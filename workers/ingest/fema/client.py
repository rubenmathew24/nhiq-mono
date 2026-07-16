"""FEMA NRI ArcGIS FeatureServer client — county-scoped tract queries."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("fema.client")

FEMA_NRI_LAYER = (
    "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
    "National_Risk_Index_Census_Tracts/FeatureServer/0/query"
)

ROOT_FIELDS = (
    "STCOFIPS",
    "TRACT",
    "RISK_SCORE",
    "RISK_RATNG",
    "EAL_SCORE",
    "SOVI_SCORE",
    "RESL_SCORE",
)

PAGE_SIZE = 2000


def hazard_riskr_fields(prefixes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"{p}_RISKR" for p in prefixes)


def build_out_fields(prefixes: tuple[str, ...]) -> str:
    return ",".join(ROOT_FIELDS + hazard_riskr_fields(prefixes))


def query_county_features(
    stcofips: str,
    *,
    out_fields: str,
    timeout: float = 120.0,
) -> list[dict[str, Any]]:
    """Return raw ArcGIS feature attribute dicts for one county (STCOFIPS)."""
    where = f"STCOFIPS='{stcofips}'"
    offset = 0
    features: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout) as client:
        while True:
            response = client.get(
                FEMA_NRI_LAYER,
                params={
                    "where": where,
                    "outFields": out_fields,
                    "returnGeometry": "false",
                    "f": "json",
                    "resultRecordCount": PAGE_SIZE,
                    "resultOffset": offset,
                },
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(
                    f"FEMA NRI query failed for {stcofips}: {payload['error']}"
                )
            batch = payload.get("features") or []
            if not batch:
                break
            for feat in batch:
                attrs = feat.get("attributes") if isinstance(feat, dict) else None
                if isinstance(attrs, dict):
                    features.append(attrs)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            logger.debug(
                "FEMA county %s: fetched offset %s (%s features)",
                stcofips,
                offset,
                len(batch),
            )
    return features
