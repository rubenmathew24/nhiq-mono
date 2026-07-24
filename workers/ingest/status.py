"""Ingest completion snapshot for ops Workbook (scope + per-job %).

Usage:
  python -m ingest.status

Env:
  DATABASE_URL (required)
  INGEST_SCOPE — smoke | metro_10 | national (default metro_10)
  INGEST_COUNTY_ALLOWLIST — optional SSCCC override (intersects fixtures)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_batch
from dotenv import load_dotenv

from ingest.fixtures.canonical_addresses import (
    default_fixture_county_fips,
    parse_county_allowlist,
)
from ingest.fixtures.constants import DATA_VINTAGE
from ingest.geo.jurisdictions import STATE_FIPS_TO_ABBR
from ingest.geo.scope import (
    IncompleteNationalRegistryError,
    require_complete_national_registry,
)

FIPS_TO_STATE_ABBR = STATE_FIPS_TO_ABBR

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger("ingest.status")

SMOKE_COUNTY = "05007"
VALID_SCOPES = frozenset({"smoke", "metro_10", "national"})

JOB_NAMES = (
    "census",
    "epa",
    "cms",
    "fbi",
    "nces",
    "urban",
    "acs",
    "bls",
    "fema",
    "cms_timely",
    "scoring",
)

UPSERT_SQL = """
INSERT INTO ingest_status_snapshot
    (scope, job_name, pct_complete, done_count, total_count, detail, captured_at)
VALUES
    (%(scope)s, %(job_name)s, %(pct_complete)s, %(done_count)s, %(total_count)s,
     %(detail)s, %(captured_at)s)
ON CONFLICT (scope, job_name) DO UPDATE SET
    pct_complete = EXCLUDED.pct_complete,
    done_count = EXCLUDED.done_count,
    total_count = EXCLUDED.total_count,
    detail = EXCLUDED.detail,
    captured_at = EXCLUDED.captured_at
"""


@dataclass(frozen=True)
class JobStatus:
    job_name: str
    pct_complete: float
    done_count: int
    total_count: int
    detail: dict[str, Any]


def resolve_scope_name() -> str:
    raw = (os.getenv("INGEST_SCOPE") or "metro_10").strip().lower()
    if raw not in VALID_SCOPES:
        raise RuntimeError(
            f"INGEST_SCOPE must be one of {sorted(VALID_SCOPES)}; got {raw!r}"
        )
    return raw


def resolve_scope_counties(
    scope: str, *, database_url: str | None = None
) -> frozenset[str]:
    """Counties that define completion denominators for this status run."""
    if scope == "national":
        if not database_url:
            database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL required for INGEST_SCOPE=national status")
        # Fail closed: empty or incomplete registry is an error, not 0% success.
        base = require_complete_national_registry(database_url)
    elif scope == "smoke":
        base = frozenset({SMOKE_COUNTY})
    else:
        base = default_fixture_county_fips()

    override = parse_county_allowlist(os.getenv("INGEST_COUNTY_ALLOWLIST"))
    if override is None:
        return base
    narrowed = frozenset(override & base)
    return narrowed if narrowed else base


def _pct(done: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * done / total, 1)


def _county_set_from_rows(rows: list[tuple]) -> set[str]:
    return {str(r[0]) for r in rows if r and r[0]}


def compute_job_statuses(cur, counties: frozenset[str], scope: str) -> list[JobStatus]:
    county_list = sorted(counties)
    n = len(county_list)
    if n == 0:
        detail = {"reason": "empty_universe"}
        if scope == "national":
            detail = {
                "reason": "geo_counties_empty",
                "hint": "Run python -m ingest.geo.run with INGEST_GEO_LOAD_ALL=1",
            }
        return [
            JobStatus(name, 0.0, 0, 0, detail)
            for name in JOB_NAMES
        ]

    # census — SSCCC = state_fips || county_fips; require aland backfill
    cur.execute(
        """
        SELECT (state_fips || county_fips) AS cf
        FROM census_tracts
        WHERE (state_fips || county_fips) = ANY(%s)
        GROUP BY (state_fips || county_fips)
        HAVING COUNT(*) > 0
           AND COUNT(*) FILTER (WHERE aland IS NULL) = 0
        """,
        (county_list,),
    )
    census_ok = _county_set_from_rows(cur.fetchall())
    statuses: list[JobStatus] = [
        JobStatus(
            "census",
            _pct(len(census_ok), n),
            len(census_ok),
            n,
            {"missing": sorted(set(county_list) - census_ok)},
        )
    ]

    # epa — county_fips is SSCCC; denominator = AQS monitor counties (not all geo)
    cur.execute(
        """
        SELECT DISTINCT county_fips
        FROM epa_aqi_readings
        WHERE county_fips = ANY(%s)
        """,
        (county_list,),
    )
    epa_ok = _county_set_from_rows(cur.fetchall())
    cur.execute(
        """
        SELECT county_fips
        FROM epa_aqs_monitor_counties
        WHERE county_fips = ANY(%s)
        """,
        (county_list,),
    )
    epa_monitors = _county_set_from_rows(cur.fetchall())
    # Same pattern as urban ÷ NCES: fall back to full N until catalog exists.
    epa_den = len(epa_monitors) if epa_monitors else n
    epa_done_set = epa_ok & epa_monitors if epa_monitors else epa_ok
    epa_missing = (
        sorted(epa_monitors - epa_ok) if epa_monitors else sorted(set(county_list) - epa_ok)
    )
    statuses.append(
        JobStatus(
            "epa",
            _pct(len(epa_done_set), epa_den),
            len(epa_done_set),
            epa_den,
            {"missing": epa_missing},
        )
    )

    # cms — by USPS state for counties in scope
    state_abbrs = sorted(
        {
            FIPS_TO_STATE_ABBR[cf[:2]]
            for cf in county_list
            if cf[:2] in FIPS_TO_STATE_ABBR
        }
    )
    cur.execute(
        """
        SELECT DISTINCT state
        FROM hospitals
        WHERE state = ANY(%s)
        """,
        (state_abbrs,),
    )
    cms_ok = {str(r[0]) for r in cur.fetchall() if r and r[0]}
    statuses.append(
        JobStatus(
            "cms",
            _pct(len(cms_ok), len(state_abbrs)),
            len(cms_ok),
            len(state_abbrs),
            {"missing_states": sorted(set(state_abbrs) - cms_ok)},
        )
    )

    # fbi
    cur.execute(
        """
        SELECT DISTINCT county_fips
        FROM crime_agency_selection
        WHERE county_fips = ANY(%s)
        """,
        (county_list,),
    )
    fbi_ok = _county_set_from_rows(cur.fetchall())
    statuses.append(
        JobStatus(
            "fbi",
            _pct(len(fbi_ok), n),
            len(fbi_ok),
            n,
            {"missing": sorted(set(county_list) - fbi_ok)},
        )
    )

    # nces — state_fips + 3-digit county_fips
    cur.execute(
        """
        SELECT DISTINCT (state_fips || county_fips) AS cf
        FROM schools_nces
        WHERE (state_fips || county_fips) = ANY(%s)
        """,
        (county_list,),
    )
    nces_ok = _county_set_from_rows(cur.fetchall())
    statuses.append(
        JobStatus(
            "nces",
            _pct(len(nces_ok), n),
            len(nces_ok),
            n,
            {"missing": sorted(set(county_list) - nces_ok)},
        )
    )

    # urban — counties that have ≥1 NCES school with a matching urban row
    cur.execute(
        """
        SELECT DISTINCT (n.state_fips || n.county_fips) AS cf
        FROM schools_nces n
        INNER JOIN schools_urban u ON u.ncessch = n.ncessch
        WHERE (n.state_fips || n.county_fips) = ANY(%s)
        """,
        (county_list,),
    )
    urban_ok = _county_set_from_rows(cur.fetchall())
    # Denominator: counties that have NCES (plan); if none, use N
    urban_den = len(nces_ok) if nces_ok else n
    urban_done = len(urban_ok)
    statuses.append(
        JobStatus(
            "urban",
            _pct(urban_done, urban_den),
            urban_done,
            urban_den,
            {"missing": sorted(nces_ok - urban_ok) if nces_ok else sorted(county_list)},
        )
    )

    # acs — every tract has ACS row with total_population
    cur.execute(
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
        (county_list,),
    )
    acs_ok = _county_set_from_rows(cur.fetchall())
    statuses.append(
        JobStatus(
            "acs",
            _pct(len(acs_ok), n),
            len(acs_ok),
            n,
            {"missing": sorted(set(county_list) - acs_ok), "metric": "tracts_with_population"},
        )
    )

    # bls
    cur.execute(
        """
        SELECT DISTINCT county_fips
        FROM bls_laus_county
        WHERE county_fips = ANY(%s)
        """,
        (county_list,),
    )
    bls_ok = _county_set_from_rows(cur.fetchall())
    statuses.append(
        JobStatus(
            "bls",
            _pct(len(bls_ok), n),
            len(bls_ok),
            n,
            {"missing": sorted(set(county_list) - bls_ok)},
        )
    )

    # fema — counties where every land tract has fema_nri_tracts
    # (exclude Census water tracts 99xxxx — absent from FEMA NRI)
    cur.execute(
        """
        WITH scoped AS (
            SELECT geoid, (state_fips || county_fips) AS cf
            FROM census_tracts
            WHERE (state_fips || county_fips) = ANY(%s)
              AND tract_fips NOT LIKE '99%%'
        )
        SELECT s.cf
        FROM scoped s
        LEFT JOIN fema_nri_tracts f ON f.geoid = s.geoid
        GROUP BY s.cf
        HAVING COUNT(*) > 0
           AND COUNT(*) FILTER (WHERE f.geoid IS NOT NULL) = COUNT(*)
        """,
        (county_list,),
    )
    fema_ok = _county_set_from_rows(cur.fetchall())
    statuses.append(
        JobStatus(
            "fema",
            _pct(len(fema_ok), n),
            len(fema_ok),
            n,
            {"missing": sorted(set(county_list) - fema_ok)},
        )
    )

    # cms_timely — hospital share (hospitals with ≥1 timely measure / all hospitals).
    # Ingest checkpoint still uses ≥80% per state; coverage UI uses continuous share.
    cur.execute(
        """
        WITH hospitals_in AS (
            SELECT cms_provider_id, state
            FROM hospitals
            WHERE state = ANY(%s)
        ),
        hospital_counts AS (
            SELECT state, COUNT(*)::int AS n FROM hospitals_in GROUP BY state
        ),
        timely_counts AS (
            SELECT h.state, COUNT(DISTINCT h.cms_provider_id)::int AS n
            FROM hospitals_in h
            INNER JOIN hospital_timely_measures t
              ON t.cms_provider_id = h.cms_provider_id
             AND t.data_vintage = %s
            GROUP BY h.state
        )
        SELECT COALESCE(SUM(COALESCE(tc.n, 0)), 0)::int AS timely_n,
               COALESCE(SUM(hc.n), 0)::int AS hospital_n
        FROM hospital_counts hc
        LEFT JOIN timely_counts tc ON tc.state = hc.state
        """,
        (state_abbrs, DATA_VINTAGE),
    )
    timely_row = cur.fetchone()
    timely_done_n = int(timely_row[0] or 0) if timely_row else 0
    timely_total_n = int(timely_row[1] or 0) if timely_row else 0
    statuses.append(
        JobStatus(
            "cms_timely",
            _pct(timely_done_n, timely_total_n),
            timely_done_n,
            timely_total_n,
            {"grain": "hospital"},
        )
    )

    # scoring — county grain vs full national universe (same as inventory
    # counties_with_score_detail). Do NOT use loaded-tract count as denominator.
    cur.execute(
        """
        WITH scoped AS (
            SELECT geoid, (state_fips || county_fips) AS cf
            FROM census_tracts
            WHERE (state_fips || county_fips) = ANY(%s)
        )
        SELECT COUNT(*)::int
        FROM (
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
        ) done_counties
        """,
        (county_list, DATA_VINTAGE),
    )
    score_done = int(cur.fetchone()[0] or 0)
    statuses.append(
        JobStatus(
            "scoring",
            _pct(score_done, n),
            score_done,
            n,
            {"metric": "counties_with_fbi_cde_and_score_detail"},
        )
    )

    return statuses


def persist_and_log(database_url: str, scope: str, counties: frozenset[str]) -> dict[str, Any]:
    captured = datetime.now(timezone.utc)
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            jobs = compute_job_statuses(cur, counties, scope)
            rows = [
                {
                    "scope": scope,
                    "job_name": j.job_name,
                    "pct_complete": j.pct_complete,
                    "done_count": j.done_count,
                    "total_count": j.total_count,
                    "detail": Json(j.detail),
                    "captured_at": captured,
                }
                for j in jobs
            ]
            execute_batch(cur, UPSERT_SQL, rows, page_size=50)
        conn.commit()
    finally:
        conn.close()

    payload = {
        "scope": scope,
        "counties": [],  # omitted from LA (too large for national); use county_count
        "county_count": len(counties),
        "captured_at": captured.isoformat(),
        "jobs": [
            {
                "job_name": j.job_name,
                "pct_complete": j.pct_complete,
                "done_count": j.done_count,
                "total_count": j.total_count,
            }
            for j in jobs
        ],
    }
    # Single parseable metrics-only line for Log Analytics / Workbook.
    # Full missing-county detail remains in Postgres only (avoids ~16KB LA truncation).
    print("INGEST_STATUS_SNAPSHOT " + json.dumps(payload, separators=(",", ":")))
    logger.info(
        "Status snapshot scope=%s jobs=%s",
        scope,
        {j.job_name: j.pct_complete for j in jobs},
    )
    return payload


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL is required")
        return 1
    try:
        scope = resolve_scope_name()
        counties = resolve_scope_counties(scope, database_url=database_url)
        persist_and_log(database_url, scope, counties)
        return 0
    except IncompleteNationalRegistryError as exc:
        logger.error("%s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
