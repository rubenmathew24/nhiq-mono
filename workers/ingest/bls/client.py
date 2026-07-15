"""BLS Public Data API v2 — LAUS county unemployment series."""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger("bls.client")

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def bls_api_key() -> str | None:
    key = os.getenv("BLS_API_KEY", "").strip().strip("'\"")
    return key or None


def laus_series_id(county_fips: str) -> str:
    """County unemployment rate: LAUCN{ss}{ccc}0000000003."""
    ss = county_fips[:2]
    ccc = county_fips[2:5]
    return f"LAUCN{ss}{ccc}0000000003"


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
