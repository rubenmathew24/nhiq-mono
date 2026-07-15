"""Census tract transform helpers (fixture-county filter + geoid shaping)."""

from __future__ import annotations

from typing import Any

from ingest.fixtures.canonical_addresses import county_in_fixture


def normalize_geoid(raw: Any) -> str | None:
    """Return an 11-digit GEOID or None if invalid."""
    if raw is None:
        return None
    geoid = str(raw).strip()
    if len(geoid) != 11 or not geoid.isdigit():
        return None
    return geoid


def row_in_fixture_county(state_fips: Any, county_fips: Any) -> bool:
    """True when STATEFP/COUNTYFP are in the canonical fixture allowlist."""
    state = str(state_fips).zfill(2)[-2:]
    county = str(county_fips).zfill(3)[-3:]
    return county_in_fixture(state, county)


def filter_tract_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Keep tracts in fixture counties and normalize identifiers.

    Each record should include: geoid (or GEOID), state_fips/STATEFP,
    county_fips/COUNTYFP, tract_fips/TRACTCE.
    """
    out: list[dict[str, Any]] = []
    for r in records:
        state = r.get("state_fips", r.get("STATEFP"))
        county = r.get("county_fips", r.get("COUNTYFP"))
        if not row_in_fixture_county(state, county):
            continue
        geoid = normalize_geoid(r.get("geoid", r.get("GEOID")))
        if not geoid:
            continue
        tract = str(r.get("tract_fips", r.get("TRACTCE", ""))).zfill(6)[-6:]
        out.append(
            {
                "geoid": geoid,
                "state_fips": str(state).zfill(2)[-2:],
                "county_fips": str(county).zfill(3)[-3:],
                "tract_fips": tract,
                "geometry": r.get("geometry"),
            }
        )
    return out
