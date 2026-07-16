"""NCES EDGE ArcGIS REST client — public school locations."""

from __future__ import annotations

import logging
from typing import Any, Iterator

import httpx

logger = logging.getLogger("nces.client")

NCES_EDGE_BASE = (
    "https://nces.ed.gov/opengis/rest/services/K12_School_Locations/"
    "EDGE_GEOCODE_PUBLICSCH_2425/MapServer/0/query"
)

OUT_FIELDS = "NCESSCH,LEAID,NAME,STFIP,CNTY,LOCALE,LAT,LON"
PAGE_SIZE = 2000


def iter_state_school_pages(
    state_fips: str,
    *,
    timeout: float = 120.0,
) -> Iterator[list[dict[str, Any]]]:
    """Yield raw ArcGIS feature dicts for one state (paginated)."""
    offset = 0
    with httpx.Client(timeout=timeout) as client:
        while True:
            response = client.get(
                NCES_EDGE_BASE,
                params={
                    "where": f"STFIP='{state_fips}'",
                    "outFields": OUT_FIELDS,
                    "returnGeometry": "true",
                    "f": "json",
                    "resultRecordCount": PAGE_SIZE,
                    "resultOffset": offset,
                },
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(
                    f"NCES EDGE query failed for state {state_fips}: {payload['error']}"
                )
            features = payload.get("features") or []
            if not features:
                break
            yield features
            if len(features) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            logger.debug(
                "NCES state %s: fetched offset %s (%s features)",
                state_fips,
                offset,
                len(features),
            )
