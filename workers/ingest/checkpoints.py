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
    """Counties where every census tract has ACS tract row with total_population."""
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
        LEFT JOIN acs_indicators a
          ON a.geoid = s.geoid
         AND a.geo_level = 'tract'
         AND a.total_population IS NOT NULL
        GROUP BY s.cf
        HAVING COUNT(*) > 0
           AND COUNT(*) FILTER (WHERE a.geoid IS NOT NULL) = COUNT(*)
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


def counties_with_urban(database_url: str, counties: list[str]) -> set[str]:
    """Counties with ≥1 NCES school that has a matching schools_urban row."""
    if not counties:
        return set()
    return _fetch_set(
        database_url,
        """
        SELECT DISTINCT (n.state_fips || n.county_fips)
        FROM schools_nces n
        INNER JOIN schools_urban u ON u.ncessch = n.ncessch
        WHERE (n.state_fips || n.county_fips) = ANY(%s)
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


def counties_with_score_detail(
    database_url: str,
    counties: list[str],
    *,
    data_vintage: str,
) -> set[str]:
    """Counties where every tract has fbi_cde safety and non-empty score_detail."""
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
        LEFT JOIN neighborhood_scores ns
          ON ns.geoid = s.geoid AND ns.data_vintage = %s
        GROUP BY s.cf
        HAVING COUNT(*) > 0
           AND COUNT(*) FILTER (
               WHERE ns.score_sources->'safety'->>'source_id' = 'fbi_cde'
                 AND ns.score_detail IS NOT NULL
                 AND ns.score_detail <> '{}'::jsonb
           ) = COUNT(*)
        """,
        (counties, data_vintage),
    )


def counties_with_fema_nri(database_url: str, counties: list[str]) -> set[str]:
    """Counties where every census tract has a fema_nri_tracts row."""
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
        LEFT JOIN fema_nri_tracts f ON f.geoid = s.geoid
        GROUP BY s.cf
        HAVING COUNT(*) > 0
           AND COUNT(*) FILTER (WHERE f.geoid IS NOT NULL) = COUNT(*)
        """,
        (counties,),
    )


def states_with_timely_measures(
    database_url: str,
    state_abbrs: list[str],
    *,
    data_vintage: str,
) -> set[str]:
    """USPS state abbrs where every hospital has ≥1 timely measure (or no hospitals)."""
    if not state_abbrs:
        return set()
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH hospitals_in AS (
                    SELECT cms_provider_id, state
                    FROM hospitals
                    WHERE state = ANY(%s)
                ),
                hospital_counts AS (
                    SELECT state, COUNT(*)::int AS n
                    FROM hospitals_in
                    GROUP BY state
                ),
                timely_counts AS (
                    SELECT h.state, COUNT(DISTINCT h.cms_provider_id)::int AS n
                    FROM hospitals_in h
                    INNER JOIN hospital_timely_measures t
                      ON t.cms_provider_id = h.cms_provider_id
                     AND t.data_vintage = %s
                    GROUP BY h.state
                )
                SELECT hc.state
                FROM hospital_counts hc
                LEFT JOIN timely_counts tc ON tc.state = hc.state
                WHERE hc.n = 0 OR COALESCE(tc.n, 0) = hc.n
                """,
                (state_abbrs, data_vintage),
            )
            have = {str(r[0]) for r in cur.fetchall() if r and r[0]}
            # States with zero hospitals are done (nothing to fetch)
            cur.execute(
                """
                SELECT DISTINCT state FROM hospitals WHERE state = ANY(%s)
                """,
                (state_abbrs,),
            )
            with_hospitals = {str(r[0]) for r in cur.fetchall() if r and r[0]}
            no_hospitals = set(state_abbrs) - with_hospitals
            return have | no_hospitals
    finally:
        conn.close()


def geoids_with_fema_nri(database_url: str, geoids: list[str]) -> set[str]:
    if not geoids:
        return set()
    return _fetch_set(
        database_url,
        "SELECT geoid FROM fema_nri_tracts WHERE geoid = ANY(%s)",
        (geoids,),
    )


def log_skip(logger: logging.Logger, worker: str, skipped: int, remaining: int) -> None:
    logger.info(
        "skip_checkpoint worker=%s skipped=%s remaining=%s",
        worker,
        skipped,
        remaining,
    )
