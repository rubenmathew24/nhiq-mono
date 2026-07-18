"""BLS Public Data API v2 — LAUS county unemployment series + bulk flat files."""

from __future__ import annotations

import csv
import io
import logging
import os
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger("bls.client")

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_LAUS_BASE = "https://download.bls.gov/pub/time.series/la"


def use_bulk_files() -> bool:
    raw = (os.getenv("BLS_USE_BULK_FILES") or "1").strip().lower()
    return raw in ("1", "true", "yes")


def bls_api_key() -> str | None:
    key = os.getenv("BLS_API_KEY", "").strip().strip("'\"")
    return key or None


def laus_series_id(county_fips: str) -> str:
    """County unemployment rate: LAUCN{ss}{ccc}0000000003."""
    ss = county_fips[:2]
    ccc = county_fips[2:5]
    return f"LAUCN{ss}{ccc}0000000003"


def _download_text(url: str, *, timeout: float = 180.0) -> str:
    headers = {"User-Agent": "NeighborhoodInsight-ingest/1.0"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def fetch_laus_bulk(
    series_ids: list[str],
    *,
    timeout: float = 300.0,
) -> dict[str, list[dict[str, Any]]]:
    """Load BLS LAUS flat files and return series_id -> observations (API-shaped)."""
    wanted = set(series_ids)
    if not wanted:
        return {}

    data_url = f"{BLS_LAUS_BASE}/la.data.0.CurrentAllData00-Present"
    logger.info("BLS LAUS bulk download %s", data_url)
    try:
        text = _download_text(data_url, timeout=timeout)
    except Exception:
        data_url = f"{BLS_LAUS_BASE}/la.data.1.AllData"
        logger.info("BLS LAUS bulk fallback download %s", data_url)
        text = _download_text(data_url, timeout=timeout)

    out: dict[str, list[dict[str, Any]]] = {sid: [] for sid in wanted}
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    for row in reader:
        sid = (row.get("series_id") or row.get("series_id ") or "").strip()
        if sid not in wanted:
            continue
        year = (row.get("year") or "").strip()
        period = (row.get("period") or "").strip()
        value = (row.get("value") or "").strip()
        if not year or not period:
            continue
        out[sid].append({"year": year, "period": period, "value": value})
    logger.info(
        "BLS LAUS bulk matched series=%s/%s",
        sum(1 for v in out.values() if v),
        len(wanted),
    )
    return out


def fetch_laus_series(
    series_ids: list[str],
    *,
    start_year: int | None = None,
    end_year: int | None = None,
    timeout: float = 60.0,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch LAUS time series; returns series_id -> observations (newest first)."""
    if not series_ids:
        return {}

    today = date.today()
    end_year = end_year or today.year
    start_year = start_year or (end_year - 2)

    body: dict[str, Any] = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    key = bls_api_key()
    if key:
        body["registrationkey"] = key

    with httpx.Client(timeout=timeout) as client:
        response = client.post(BLS_API_URL, json=body)
        response.raise_for_status()
        payload = response.json()

    status = payload.get("status")
    if status != "REQUEST_SUCCEEDED":
        messages = payload.get("message") or payload.get("Messages")
        raise RuntimeError(f"BLS API failed: {status} {messages}")

    out: dict[str, list[dict[str, Any]]] = {}
    for series in payload.get("Results", {}).get("series", []):
        sid = series.get("seriesID")
        if sid:
            out[sid] = series.get("data") or []
    return out
