"""Urban Institute Education Data Portal — CCD school directory."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("urban.client")

URBAN_CCD_BASE = "https://educationdata.urban.org/api/v1/schools/ccd/directory"
DEFAULT_YEAR = 2022
PER_PAGE = 100


def fetch_directory_for_leaid(
    leaid: str,
    *,
    year: int = DEFAULT_YEAR,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    """Fetch all CCD directory rows for one LEA (paginated)."""
    out: list[dict[str, Any]] = []
    page = 1
    with httpx.Client(timeout=timeout) as client:
        while True:
            response = client.get(
                f"{URBAN_CCD_BASE}/{year}/",
                params={"leaid": leaid, "per_page": PER_PAGE, "page": page},
            )
            if response.status_code == 404:
                break
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results") or []
            if not isinstance(results, list) or not results:
                break
            out.extend(results)
            count = payload.get("count")
            if isinstance(count, int) and len(out) >= count:
                break
            if len(results) < PER_PAGE:
                break
            page += 1
            if page > 50:
                break
    return out


def fetch_directory_for_ncessch(
    ncessch: str,
    *,
    year: int = DEFAULT_YEAR,
    timeout: float = 30.0,
) -> dict[str, Any] | None:
    """Fetch a single school directory row by NCESSCH."""
    with httpx.Client(timeout=timeout) as client:
        response = client.get(
            f"{URBAN_CCD_BASE}/{year}/",
            params={"ncessch": ncessch, "per_page": 5, "page": 1},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        if isinstance(results, list) and results:
            return results[0] if isinstance(results[0], dict) else None
    return None
