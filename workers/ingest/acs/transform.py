"""Normalize ACS tract tabular rows to acs_indicators."""

from __future__ import annotations

from typing import Any

CENSUS_NULL_SENTINELS = frozenset(
    {
        "",
        "-",
        "null",
        "-666666666",
        "-888888888",
        "-999999999",
    }
)


def _parse_numeric(raw: Any) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if text in CENSUS_NULL_SENTINELS:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def transform_acs_rows(
    rows: list[dict[str, Any]],
    *,
    acs_year: str,
) -> list[dict[str, Any]]:
    """Map Census tract rows to acs_indicators upsert dicts."""
    out: list[dict[str, Any]] = []
    for row in rows:
        state = str(row.get("state") or "").zfill(2)
        county = str(row.get("county") or "").zfill(3)
        tract = str(row.get("tract") or "").zfill(6)
        if not state or not county or not tract:
            continue
        geoid = f"{state}{county}{tract}"
        out.append(
            {
                "geoid": geoid,
                "geo_level": "tract",
                "median_hh_income": _parse_numeric(row.get("B19013_001E")),
                "labor_force": _parse_numeric(row.get("B23025_002E")),
                "employed": _parse_numeric(row.get("B23025_004E")),
                "unemployed": _parse_numeric(row.get("B23025_005E")),
                "acs_year": acs_year,
                "payload": None,
            }
        )
    return out
