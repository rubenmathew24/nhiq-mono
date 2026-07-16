"""Resolve active counties/states for smoke, metro_10, and national scopes."""

from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2

from ingest.fixtures.canonical_addresses import (
    default_fixture_county_fips,
    parse_county_allowlist,
)
from ingest.geo.jurisdictions import INCLUDED_STATE_FIPS, STATE_FIPS_TO_ABBR

SMOKE_COUNTY = "05007"
VALID_SCOPES = frozenset({"smoke", "metro_10", "national"})


@dataclass(frozen=True)
class CountyPoint:
    county_fips: str
    state_fips: str
    county_name: str
    state_abbr: str
    latitude: float
    longitude: float


def resolve_ingest_scope() -> str:
    raw = (os.getenv("INGEST_SCOPE") or "metro_10").strip().lower()
    if raw not in VALID_SCOPES:
        raise RuntimeError(
            f"INGEST_SCOPE must be one of {sorted(VALID_SCOPES)}; got {raw!r}"
        )
    return raw


def parse_state_batch(raw: str | None) -> frozenset[str] | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    codes: set[str] = set()
    for part in text.split(","):
        token = part.strip()
        if len(token) == 2 and token.isdigit():
            codes.add(token)
    return frozenset(codes) if codes else None


def require_national_state_batch() -> frozenset[str]:
    batch = parse_state_batch(os.getenv("INGEST_STATE_BATCH"))
    if batch is None:
        raise RuntimeError(
            "INGEST_SCOPE=national requires INGEST_STATE_BATCH=SS,SS,... "
            "(2-digit state FIPS). Refusing all-states run."
        )
    unknown = sorted(batch - INCLUDED_STATE_FIPS)
    if unknown:
        raise RuntimeError(
            f"INGEST_STATE_BATCH has codes not in 50+DC included set: {unknown}. "
            "Territory FIPS are reserved for a later config enablement."
        )
    return batch


def _narrow_allowlist(counties: frozenset[str]) -> frozenset[str]:
    override = parse_county_allowlist(os.getenv("INGEST_COUNTY_ALLOWLIST"))
    if override is None:
        return counties
    narrowed = frozenset(override & counties)
    return narrowed if narrowed else counties


def load_geo_counties_for_states(
    database_url: str, state_fips: frozenset[str]
) -> frozenset[str]:
    if not state_fips:
        return frozenset()
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT county_fips
                FROM geo_counties
                WHERE state_fips = ANY(%s)
                """,
                (sorted(state_fips),),
            )
            return frozenset(str(r[0]) for r in cur.fetchall() if r and r[0])
    finally:
        conn.close()


def load_national_universe_counties(database_url: str) -> frozenset[str]:
    """All registry counties in included jurisdictions (status denominator)."""
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT county_fips
                FROM geo_counties
                WHERE state_fips = ANY(%s)
                """,
                (sorted(INCLUDED_STATE_FIPS),),
            )
            return frozenset(str(r[0]) for r in cur.fetchall() if r and r[0])
    finally:
        conn.close()


def active_county_fips(*, database_url: str | None = None) -> frozenset[str]:
    """
    Counties the current worker should process.

    smoke / metro_10: fixtures (no DB).
    national: geo_counties rows for INGEST_STATE_BATCH (requires DATABASE_URL).
    """
    scope = resolve_ingest_scope()
    if scope == "smoke":
        return _narrow_allowlist(frozenset({SMOKE_COUNTY}))
    if scope == "metro_10":
        return _narrow_allowlist(default_fixture_county_fips())

    batch = require_national_state_batch()
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for INGEST_SCOPE=national")
    counties = load_geo_counties_for_states(database_url, batch)
    if not counties:
        raise RuntimeError(
            f"No geo_counties rows for INGEST_STATE_BATCH={sorted(batch)}. "
            "Run python -m ingest.geo.run for that batch first."
        )
    return _narrow_allowlist(counties)


def active_state_fips(*, database_url: str | None = None) -> frozenset[str]:
    return frozenset(cf[:2] for cf in active_county_fips(database_url=database_url))


def active_state_abbrs(*, database_url: str | None = None) -> frozenset[str]:
    return frozenset(
        STATE_FIPS_TO_ABBR[sf]
        for sf in active_state_fips(database_url=database_url)
        if sf in STATE_FIPS_TO_ABBR
    )


def county_in_active(
    state_fips: str, county_fips: str, *, allow: frozenset[str]
) -> bool:
    return f"{state_fips}{county_fips}" in allow


def load_county_points(
    database_url: str, counties: frozenset[str]
) -> dict[str, CountyPoint]:
    if not counties:
        return {}
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT county_fips, state_fips, county_name, state_abbr,
                       centroid_lat, centroid_lon
                FROM geo_counties
                WHERE county_fips = ANY(%s)
                """,
                (sorted(counties),),
            )
            out: dict[str, CountyPoint] = {}
            for row in cur.fetchall():
                cf, sf, name, abbr, lat, lon = row
                if lat is None or lon is None:
                    continue
                out[str(cf)] = CountyPoint(
                    county_fips=str(cf),
                    state_fips=str(sf),
                    county_name=str(name or ""),
                    state_abbr=str(abbr or STATE_FIPS_TO_ABBR.get(str(sf), "")),
                    latitude=float(lat),
                    longitude=float(lon),
                )
            return out
    finally:
        conn.close()
