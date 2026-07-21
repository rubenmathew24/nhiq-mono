"""National data coverage — same denominators as workers/ingest/status.py (007)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.data.jurisdictions import (
    INCLUDED_STATE_FIPS,
    STATE_FIPS_TO_ABBR,
)
from app.schemas.coverage import CoverageResponse, SourceCoverage, StateCoverage

JOB_ORDER: tuple[str, ...] = (
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

COUNTY_JOBS = frozenset(
    {"census", "epa", "fbi", "nces", "urban", "acs", "bls", "fema", "scoring"}
)
STATE_JOBS = frozenset({"cms"})
HOSPITAL_JOBS = frozenset({"cms_timely"})


def _pct(done: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * done / total, 1)


def _grain_for_job(job_name: str) -> str:
    if job_name in STATE_JOBS:
        return "state"
    if job_name in HOSPITAL_JOBS:
        return "hospital"
    return "county"


def _source(
    job_name: str,
    *,
    grain: str,
    done: int,
    total: int,
) -> SourceCoverage:
    return SourceCoverage(
        job_name=job_name,
        grain=grain,  # type: ignore[arg-type]
        done_count=done,
        total_count=total,
        pct_complete=_pct(done, total),
    )


async def _fetch_cf_set(session: AsyncSession, sql: str, params: dict[str, Any]) -> set[str]:
    result = await session.execute(text(sql), params)
    return {str(r[0]) for r in result.fetchall() if r and r[0]}


async def _fetch_timely_hospital_counts(
    session: AsyncSession, *, states: list[str], vintage: str
) -> dict[str, tuple[int, int]]:
    """Per-state (hospitals_with_timely, hospital_total) for cms_timely coverage.

    Continuous hospital share — not the ingest 80% state pass/fail checkpoint.
    """
    result = await session.execute(
        text(
            """
            WITH hospitals_in AS (
                SELECT cms_provider_id, state
                FROM hospitals
                WHERE state = ANY(:states)
            ),
            hospital_counts AS (
                SELECT state, COUNT(*)::int AS n FROM hospitals_in GROUP BY state
            ),
            timely_counts AS (
                SELECT h.state, COUNT(DISTINCT h.cms_provider_id)::int AS n
                FROM hospitals_in h
                INNER JOIN hospital_timely_measures t
                  ON t.cms_provider_id = h.cms_provider_id
                 AND t.data_vintage = :vintage
                GROUP BY h.state
            )
            SELECT hc.state,
                   COALESCE(tc.n, 0)::int AS timely_n,
                   hc.n AS hospital_n
            FROM hospital_counts hc
            LEFT JOIN timely_counts tc ON tc.state = hc.state
            """
        ),
        {"states": states, "vintage": vintage},
    )
    out: dict[str, tuple[int, int]] = {}
    for row in result.fetchall():
        if not row or not row[0]:
            continue
        out[str(row[0])] = (int(row[1] or 0), int(row[2] or 0))
    return out


async def compute_national_coverage(session: AsyncSession) -> CoverageResponse:
    captured = datetime.now(timezone.utc)
    vintage = settings.SCORE_DATA_VINTAGE
    included = sorted(INCLUDED_STATE_FIPS)

    universe_rows = (
        await session.execute(
            text(
                """
                SELECT county_fips, state_fips
                FROM geo_counties
                WHERE state_fips = ANY(:states)
                """
            ),
            {"states": included},
        )
    ).fetchall()

    counties = [str(r[0]) for r in universe_rows if r and r[0]]
    county_to_state = {
        str(r[0]): str(r[1]).zfill(2)[-2:]
        for r in universe_rows
        if r and r[0] and r[1]
    }
    n = len(counties)
    state_fips_list = sorted({county_to_state[c] for c in counties})
    state_abbrs = sorted(
        {
            STATE_FIPS_TO_ABBR[sf]
            for sf in state_fips_list
            if sf in STATE_FIPS_TO_ABBR
        }
    )

    if n == 0:
        empty_sources = [
            _source(
                name,
                grain=_grain_for_job(name),
                done=0,
                total=0,
            )
            for name in JOB_ORDER
        ]
        return CoverageResponse(
            captured_at=captured,
            overall_pct=0.0,
            county_universe_count=0,
            state_universe_count=0,
            empty_universe=True,
            sources=empty_sources,
            states=[],
        )

    params_cf = {"counties": counties}

    census_ok = await _fetch_cf_set(
        session,
        """
        SELECT DISTINCT (state_fips || county_fips) AS cf
        FROM census_tracts
        WHERE (state_fips || county_fips) = ANY(:counties)
        """,
        params_cf,
    )
    epa_ok = await _fetch_cf_set(
        session,
        """
        SELECT DISTINCT county_fips
        FROM epa_aqi_readings
        WHERE county_fips = ANY(:counties)
        """,
        params_cf,
    )
    # AQS monitor catalog — EPA coverage ÷ this set (urban ÷ NCES pattern).
    epa_monitors = await _fetch_cf_set(
        session,
        """
        SELECT county_fips
        FROM epa_aqs_monitor_counties
        WHERE county_fips = ANY(:counties)
        """,
        params_cf,
    )
    cms_ok = await _fetch_cf_set(
        session,
        """
        SELECT DISTINCT state
        FROM hospitals
        WHERE state = ANY(:states)
        """,
        {"states": state_abbrs},
    )
    fbi_ok = await _fetch_cf_set(
        session,
        """
        SELECT DISTINCT county_fips
        FROM crime_agency_selection
        WHERE county_fips = ANY(:counties)
        """,
        params_cf,
    )
    nces_ok = await _fetch_cf_set(
        session,
        """
        SELECT DISTINCT (state_fips || county_fips) AS cf
        FROM schools_nces
        WHERE (state_fips || county_fips) = ANY(:counties)
        """,
        params_cf,
    )
    urban_ok = await _fetch_cf_set(
        session,
        """
        SELECT DISTINCT (n.state_fips || n.county_fips) AS cf
        FROM schools_nces n
        INNER JOIN schools_urban u ON u.ncessch = n.ncessch
        WHERE (n.state_fips || n.county_fips) = ANY(:counties)
        """,
        params_cf,
    )
    acs_ok = await _fetch_cf_set(
        session,
        """
        WITH scoped AS (
            SELECT geoid, (state_fips || county_fips) AS cf
            FROM census_tracts
            WHERE (state_fips || county_fips) = ANY(:counties)
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
        params_cf,
    )
    bls_ok = await _fetch_cf_set(
        session,
        """
        SELECT DISTINCT county_fips
        FROM bls_laus_county
        WHERE county_fips = ANY(:counties)
        """,
        params_cf,
    )
    fema_ok = await _fetch_cf_set(
        session,
        """
        WITH scoped AS (
            SELECT geoid, (state_fips || county_fips) AS cf
            FROM census_tracts
            WHERE (state_fips || county_fips) = ANY(:counties)
              AND tract_fips NOT LIKE '99%'
        )
        SELECT s.cf
        FROM scoped s
        LEFT JOIN fema_nri_tracts f ON f.geoid = s.geoid
        GROUP BY s.cf
        HAVING COUNT(*) > 0
           AND COUNT(*) FILTER (WHERE f.geoid IS NOT NULL) = COUNT(*)
        """,
        params_cf,
    )
    timely_by_state = await _fetch_timely_hospital_counts(
        session, states=state_abbrs, vintage=vintage
    )
    timely_done_n = sum(d for d, _t in timely_by_state.values())
    timely_total_n = sum(t for _d, t in timely_by_state.values())

    scoring_ok = await _fetch_cf_set(
        session,
        """
        WITH scoped AS (
            SELECT geoid, (state_fips || county_fips) AS cf
            FROM census_tracts
            WHERE (state_fips || county_fips) = ANY(:counties)
        )
        SELECT s.cf
        FROM scoped s
        LEFT JOIN neighborhood_scores ns
          ON ns.geoid = s.geoid AND ns.data_vintage = :vintage
        GROUP BY s.cf
        HAVING COUNT(*) > 0
           AND COUNT(*) FILTER (
               WHERE ns.score_sources->'safety'->>'source_id' = 'fbi_cde'
                 AND ns.score_detail IS NOT NULL
                 AND ns.score_detail <> '{}'::jsonb
           ) = COUNT(*)
        """,
        {"counties": counties, "vintage": vintage},
    )

    urban_den = len(nces_ok) if nces_ok else n
    # EPA: only counties with AQS monitors (008 exception, same idea as urban).
    epa_den = len(epa_monitors) if epa_monitors else n
    epa_done = len(epa_ok & epa_monitors) if epa_monitors else len(epa_ok)
    national_sources = [
        _source("census", grain="county", done=len(census_ok), total=n),
        _source("epa", grain="county", done=epa_done, total=epa_den),
        _source("cms", grain="state", done=len(cms_ok), total=len(state_abbrs)),
        _source("fbi", grain="county", done=len(fbi_ok), total=n),
        _source("nces", grain="county", done=len(nces_ok), total=n),
        _source("urban", grain="county", done=len(urban_ok), total=urban_den),
        _source("acs", grain="county", done=len(acs_ok), total=n),
        _source("bls", grain="county", done=len(bls_ok), total=n),
        _source("fema", grain="county", done=len(fema_ok), total=n),
        _source(
            "cms_timely",
            grain="hospital",
            done=timely_done_n,
            total=timely_total_n,
        ),
        _source("scoring", grain="county", done=len(scoring_ok), total=n),
    ]
    overall = round(
        sum(s.pct_complete for s in national_sources) / len(national_sources),
        1,
    )

    # Counties grouped by state for by-state view
    by_state_counties: dict[str, list[str]] = {}
    for cf in counties:
        sf = county_to_state.get(cf)
        if not sf:
            continue
        by_state_counties.setdefault(sf, []).append(cf)

    states_out: list[StateCoverage] = []
    for sf in sorted(by_state_counties):
        abbr = STATE_FIPS_TO_ABBR.get(sf, sf)
        scounties = by_state_counties[sf]
        sn = len(scounties)
        scounty_set = set(scounties)
        snces = nces_ok & scounty_set
        surban_den = len(snces) if snces else sn
        # EPA: same as national — only AQS monitor counties (0/0 if none in state).
        sepa_mon = epa_monitors & scounty_set
        sepa_den = len(sepa_mon)
        sepa_done = len(epa_ok & sepa_mon)
        srcs = [
            _source(
                "census",
                grain="county",
                done=len(census_ok & scounty_set),
                total=sn,
            ),
            _source(
                "epa",
                grain="county",
                done=sepa_done,
                total=sepa_den,
            ),
            _source(
                "cms",
                grain="state",
                done=1 if abbr in cms_ok else 0,
                total=1,
            ),
            _source(
                "fbi", grain="county", done=len(fbi_ok & scounty_set), total=sn
            ),
            _source(
                "nces", grain="county", done=len(snces), total=sn
            ),
            _source(
                "urban",
                grain="county",
                done=len(urban_ok & scounty_set),
                total=surban_den,
            ),
            _source(
                "acs", grain="county", done=len(acs_ok & scounty_set), total=sn
            ),
            _source(
                "bls", grain="county", done=len(bls_ok & scounty_set), total=sn
            ),
            _source(
                "fema", grain="county", done=len(fema_ok & scounty_set), total=sn
            ),
            _source(
                "cms_timely",
                grain="hospital",
                done=timely_by_state.get(abbr, (0, 0))[0],
                total=timely_by_state.get(abbr, (0, 0))[1],
            ),
            _source(
                "scoring",
                grain="county",
                done=len(scoring_ok & scounty_set),
                total=sn,
            ),
        ]
        states_out.append(
            StateCoverage(
                state_fips=sf,
                state_abbr=abbr,
                county_total=sn,
                sources=srcs,
            )
        )

    return CoverageResponse(
        captured_at=captured,
        overall_pct=overall,
        county_universe_count=n,
        state_universe_count=len(state_abbrs),
        empty_universe=False,
        sources=national_sources,
        states=states_out,
    )
