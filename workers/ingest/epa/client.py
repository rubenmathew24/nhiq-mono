"""EPA Air Quality System HTTP client + optional AirData bulk files."""

from __future__ import annotations

import csv
import io
import logging
import os
import zipfile
from datetime import date
from typing import Any

import httpx

from ingest.fixtures.constants import EPA_PARAM_CODES

EPA_BASE = "https://aqs.epa.gov/data/api"
EPA_AIRDATA_BASE = "https://aqs.epa.gov/aqsweb/airdata"
logger = logging.getLogger("epa.client")

# Never log full request URLs — they include email + key query params.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def use_bulk_files() -> bool:
    raw = (os.getenv("EPA_USE_BULK_FILES") or "1").strip().lower()
    return raw in ("1", "true", "yes")


def require_epa_credentials() -> tuple[str, str]:
    email = os.getenv("EPA_AQS_EMAIL", "").strip().strip("'\"")
    key = os.getenv("EPA_AQS_KEY", "").strip().strip("'\"")
    if not email or not key:
        raise RuntimeError(
            "EPA_AQS_EMAIL and EPA_AQS_KEY are required for EPA ingestion. "
            "Register at https://aqs.epa.gov/data/api/signup and set them in .env."
        )
    return email, key


def _aqs_errors(payload: dict) -> list[str]:
    header = payload.get("Header") or []
    if isinstance(header, list) and header:
        errs = header[0].get("error") or []
        if isinstance(errs, list):
            return [str(e) for e in errs]
        if errs:
            return [str(errs)]
    return []


def _param_codes() -> list[str]:
    return [p.strip() for p in EPA_PARAM_CODES.split(",") if p.strip()]


def _airdata_row_to_api(row: dict[str, str]) -> dict[str, Any] | None:
    """Map AirData daily CSV columns to AQS API-ish keys for transform_aqi_records."""
    get = {k.strip().lower(): v for k, v in row.items()}

    def pick(*names: str) -> str | None:
        for n in names:
            v = get.get(n.lower())
            if v is not None and str(v).strip() != "":
                return str(v).strip()
        return None

    state = pick("state code", "state_code")
    county = pick("county code", "county_code")
    param = pick("parameter code", "parameter_code")
    date_local = pick("date local", "date_local")
    if not state or not county or not param or not date_local:
        return None
    return {
        "state_code": state.zfill(2)[-2:],
        "county_code": county.zfill(3)[-3:],
        "parameter_code": param,
        "parameter": pick("parameter name", "parameter") or param,
        "aqi": pick("aqi"),
        "category": pick("category"),
        "date_local": date_local,
        "state": pick("state name", "state"),
        "county": pick("county name", "county"),
    }


def fetch_daily_aqi_bulk(
    start_date: date,
    end_date: date,
    *,
    timeout: float = 300.0,
) -> tuple[list[dict], set[str]]:
    """Download EPA AirData daily zips for param codes overlapping the window.

    Returns (rows_in_window, monitor_county_fips). Monitor counties are every
    distinct county that appears in the date window — the coverage denominator
    for EPA (counties with AQS data in this ingest window).
    """
    years = sorted({start_date.year, end_date.year})
    out: list[dict] = []
    monitors: set[str] = set()
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for year in years:
            for param in _param_codes():
                url = f"{EPA_AIRDATA_BASE}/daily_{param}_{year}.zip"
                logger.info("EPA AirData download %s", url)
                response = client.get(url)
                if response.status_code == 404:
                    logger.warning("EPA AirData missing %s", url)
                    continue
                response.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                    csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                    if not csv_names:
                        continue
                    text = zf.read(csv_names[0]).decode("utf-8-sig", errors="replace")
                reader = csv.DictReader(io.StringIO(text))
                for row in reader:
                    mapped = _airdata_row_to_api(
                        {str(k): ("" if v is None else str(v)) for k, v in row.items()}
                    )
                    if not mapped:
                        continue
                    d = mapped["date_local"]
                    try:
                        y, m, day = (int(x) for x in d.split("-")[:3])
                        row_date = date(y, m, day)
                    except ValueError:
                        continue
                    if start_date <= row_date <= end_date:
                        cf = f"{mapped['state_code']}{mapped['county_code']}"
                        monitors.add(cf)
                        out.append(mapped)
    logger.info(
        "EPA AirData bulk rows in window=%s monitor_counties=%s",
        len(out),
        len(monitors),
    )
    return out, monitors


async def fetch_daily_aqi(
    state_code: str,
    start_date: date,
    end_date: date,
    *,
    timeout: float = 90.0,
) -> list[dict]:
    """Fetch daily AQI summary for a state (EPA state FIPS, zero-padded)."""
    email, key = require_epa_credentials()
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            f"{EPA_BASE}/dailyData/byState",
            params={
                "email": email,
                "key": key,
                "param": EPA_PARAM_CODES,
                "bdate": start_date.strftime("%Y%m%d"),
                "edate": end_date.strftime("%Y%m%d"),
                "state": state_code,
            },
        )
        try:
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"EPA AQS returned non-JSON for state {state_code} "
                f"(HTTP {response.status_code})"
            ) from exc

        errors = _aqs_errors(data if isinstance(data, dict) else {})
        if response.status_code >= 400 or errors:
            detail = "; ".join(errors) if errors else f"HTTP {response.status_code}"
            raise RuntimeError(
                f"EPA AQS request failed for state {state_code}: {detail}"
            )

        return data.get("Data") or []
