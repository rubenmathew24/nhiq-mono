"""DB-backed checkpoint helpers — skip work already successfully stored."""

from __future__ import annotations

import logging

import psycopg2


def _fetch_set(database_url: str, sql: str, params: tuple) -> set[str]:
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return {str(r[0]) for r in cur.fetchall() if r and r[0]}
    finally:
        conn.close()


def counties_with_geo(database_url: str, counties: list[str]) -> set[str]:
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        "SELECT county_fips FROM geo_counties WHERE county_fips = ANY(%s)",
        (counties,),
    )


def counties_with_census_tracts(database_url: str, counties: list[str]) -> set[str]:
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        """
        SELECT DISTINCT (state_fips || county_fips)
        FROM census_tracts
        WHERE (state_fips || county_fips) = ANY(%s)
        """,
        (counties,),
    )


def counties_with_epa(database_url: str, counties: list[str]) -> set[str]:
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        """
        SELECT DISTINCT county_fips FROM epa_aqi_readings
        WHERE county_fips = ANY(%s)
        """,
        (counties,),
    )


def states_with_hospitals(database_url: str, state_abbrs: list[str]) -> set[str]:
    if not state_abbrs:
        return set()
    return _fetch_set(
        database_url,
        """
        SELECT DISTINCT state FROM hospitals WHERE state = ANY(%s)
        """,
        (state_abbrs,),
    )


def counties_with_fbi_agencies(database_url: str, counties: list[str]) -> set[str]:
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        """
        SELECT DISTINCT county_fips FROM crime_agency_selection
        WHERE county_fips = ANY(%s)
        """,
        (counties,),
    )


def counties_with_nces(database_url: str, counties: list[str]) -> set[str]:
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        """
        SELECT DISTINCT (state_fips || county_fips)
        FROM schools_nces
        WHERE (state_fips || county_fips) = ANY(%s)
        """,
        (counties,),
    )


def counties_with_acs(database_url: str, counties: list[str]) -> set[str]:
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        """
        SELECT DISTINCT LEFT(geoid, 5)
        FROM acs_indicators
        WHERE geo_level = 'tract' AND LEFT(geoid, 5) = ANY(%s)
        """,
        (counties,),
    )


def counties_with_bls(database_url: str, counties: list[str]) -> set[str]:
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        """
        SELECT DISTINCT county_fips FROM bls_laus_county
        WHERE county_fips = ANY(%s)
        """,
        (counties,),
    )


def counties_with_fbi_cde_scores(database_url: str, counties: list[str]) -> set[str]:
    """Counties where every tract has safety source fbi_cde (strict skip-done)."""
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        """
        WITH scoped AS (
            SELECT geoid, (state_fips || county_fips) AS cf
            FROM census_tracts
            WHERE (state_fips || county_fips) = ANY(%s)
        )
        SELECT s.cf
        FROM scoped s
        LEFT JOIN neighborhood_scores ns ON ns.geoid = s.geoid
        GROUP BY s.cf
        HAVING COUNT(*) > 0
           AND COUNT(*) FILTER (
               WHERE ns.score_sources->'safety'->>'source_id' = 'fbi_cde'
           ) = COUNT(*)
        """,
        (counties,),
    )


def log_skip(logger: logging.Logger, worker: str, skipped: int, remaining: int) -> None:
    logger.info(
        "skip_checkpoint worker=%s skipped=%s remaining=%s",
        worker,
        skipped,
        remaining,
    )
