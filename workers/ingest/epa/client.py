"""EPA Air Quality System HTTP client."""

from __future__ import annotations

import logging
import os
from datetime import date

import httpx

from ingest.fixtures.constants import EPA_PARAM_CODES

EPA_BASE = "https://aqs.epa.gov/data/api"
logger = logging.getLogger("epa.client")

# Never log full request URLs — they include email + key query params.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


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
            # Do not include request URL (contains secrets).
            raise RuntimeError(
                f"EPA AQS request failed for state {state_code}: {detail}"
            )

        return data.get("Data") or []
