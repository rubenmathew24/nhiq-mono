"""Census ACS 5-year API client — tract pulls for fixture counties."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("acs.client")

ACS_BASE = "https://api.census.gov/data"
DEFAULT_ACS_YEAR = 2022
ACS_VARIABLES = (
    "NAME",
    "B01003_001E",  # total population
    "B19013_001E",
    "B23025_002E",
    "B23025_004E",
    "B23025_005E",
)


def census_api_key() -> str | None:
    key = os.getenv("CENSUS_API_KEY", "").strip().strip("'\"")
    return key or None


def fetch_county_tract_rows(
    state_fips: str,
    county_fips: str,
    *,
    acs_year: int = DEFAULT_ACS_YEAR,
    timeout: float = 120.0,
) -> list[list[str]]:
    """Return ACS rows including header row (Census tabular format)."""
    params: dict[str, str] = {
        "get": ",".join(ACS_VARIABLES),
        "for": "tract:*",
        "in": f"state:{state_fips} county:{county_fips}",
    }
    key = census_api_key()
    if key:
        params["key"] = key

    url = f"{ACS_BASE}/{acs_year}/acs/acs5"
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, params=params)
        if response.status_code == 302:
            raise RuntimeError(
                "Census ACS requires CENSUS_API_KEY — register at https://api.census.gov/data/key_signup.html"
            )
        response.raise_for_status()
        payload: list[list[str]] = response.json()

    if not payload or len(payload) < 2:
        logger.warning(
            "ACS returned no tract rows for state=%s county=%s year=%s",
            state_fips,
            county_fips,
            acs_year,
        )
        return []

    return payload


def fetch_state_tract_rows(
    state_fips: str,
    *,
    acs_year: int = DEFAULT_ACS_YEAR,
    timeout: float = 180.0,
) -> list[list[str]]:
    """Return all ACS tract rows for a state (`in=state:SS county:*`)."""
    params: dict[str, str] = {
        "get": ",".join(ACS_VARIABLES),
        "for": "tract:*",
        "in": f"state:{state_fips} county:*",
    }
    key = census_api_key()
    if key:
        params["key"] = key

    url = f"{ACS_BASE}/{acs_year}/acs/acs5"
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, params=params)
        if response.status_code == 302:
            raise RuntimeError(
                "Census ACS requires CENSUS_API_KEY — register at https://api.census.gov/data/key_signup.html"
            )
        response.raise_for_status()
        payload: list[list[str]] = response.json()

    if not payload or len(payload) < 2:
        logger.warning(
            "ACS returned no tract rows for state=%s year=%s",
            state_fips,
            acs_year,
        )
        return []

    return payload


def fetch_state_rows(
    state_fips: str,
    *,
    acs_year: int = DEFAULT_ACS_YEAR,
    timeout: float = 120.0,
) -> list[list[str]]:
    """Return ACS state-level rows including header (for population totals)."""
    params: dict[str, str] = {
        "get": ",".join(ACS_VARIABLES),
        "for": f"state:{state_fips}",
    }
    key = census_api_key()
    if key:
        params["key"] = key

    url = f"{ACS_BASE}/{acs_year}/acs/acs5"
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, params=params)
        if response.status_code == 302:
            raise RuntimeError(
                "Census ACS requires CENSUS_API_KEY — register at https://api.census.gov/data/key_signup.html"
            )
        response.raise_for_status()
        payload: list[list[str]] = response.json()

    if not payload or len(payload) < 2:
        logger.warning(
            "ACS returned no state rows for state=%s year=%s",
            state_fips,
            acs_year,
        )
        return []

    return payload


def tabular_to_dicts(rows: list[list[str]]) -> list[dict[str, Any]]:
    """Convert Census [[header], [row], ...] to list of dicts."""
    if len(rows) < 2:
        return []
    header = rows[0]
    out: list[dict[str, Any]] = []
    for row in rows[1:]:
        out.append(dict(zip(header, row)))
    return out
