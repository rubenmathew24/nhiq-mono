"""Unit tests for national coverage denominators (no live DB required)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.schemas.coverage import CoverageResponse
from app.services import coverage_service as cs


def test_empty_universe_returns_flag():
    session = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    session.execute = AsyncMock(return_value=empty_result)

    resp = asyncio.run(cs.compute_national_coverage(session))
    assert isinstance(resp, CoverageResponse)
    assert resp.empty_universe is True
    assert resp.county_universe_count == 0
    assert resp.overall_pct == 0.0
    assert len(resp.sources) == len(cs.JOB_ORDER)
    assert resp.states == []


def test_scoring_uses_county_universe_not_tract_proxy(monkeypatch):
    """Scoring total must be |geo_counties|, done from scoring_ok set size."""
    session = AsyncMock()

    universe = MagicMock()
    universe.fetchall.return_value = [
        ("44001", "44"),
        ("44003", "44"),
        ("44005", "44"),
        ("44007", "44"),
        ("44009", "44"),
        ("09001", "09"),
        ("09003", "09"),
        ("09005", "09"),
        ("09007", "09"),
        ("09009", "09"),
    ]

    async def fake_fetch_cf_set(_session, sql, params):
        sql_l = " ".join(sql.split()).lower()
        if "neighborhood_scores" in sql_l:
            return {"44001", "44003"}
        if "hospitals" in sql_l:
            return {"RI"}
        return set()

    async def fake_timely_counts(_session, *, states, vintage):
        # RI: 5/10 hospitals; CT: 0 hospitals in mock → omitted
        return {"RI": (5, 10)}

    session.execute = AsyncMock(return_value=universe)
    monkeypatch.setattr(cs, "_fetch_cf_set", fake_fetch_cf_set)
    monkeypatch.setattr(cs, "_fetch_timely_hospital_counts", fake_timely_counts)

    resp = asyncio.run(cs.compute_national_coverage(session))
    scoring = next(s for s in resp.sources if s.job_name == "scoring")
    assert scoring.grain == "county"
    assert scoring.total_count == 10
    assert scoring.done_count == 2
    assert scoring.pct_complete == 20.0

    cms = next(s for s in resp.sources if s.job_name == "cms")
    assert cms.grain == "state"
    assert cms.total_count == 2

    timely = next(s for s in resp.sources if s.job_name == "cms_timely")
    assert timely.grain == "hospital"
    assert timely.done_count == 5
    assert timely.total_count == 10
    assert timely.pct_complete == 50.0

    ri = next(s for s in resp.states if s.state_abbr == "RI")
    ri_scoring = next(x for x in ri.sources if x.job_name == "scoring")
    assert ri_scoring.total_count == 5
    assert ri_scoring.done_count == 2
    ri_timely = next(x for x in ri.sources if x.job_name == "cms_timely")
    assert ri_timely.grain == "hospital"
    assert ri_timely.done_count == 5
    assert ri_timely.total_count == 10

    ct = next(s for s in resp.states if s.state_abbr == "CT")
    ct_timely = next(x for x in ct.sources if x.job_name == "cms_timely")
    assert ct_timely.done_count == 0
    assert ct_timely.total_count == 0


def test_empty_universe_cms_timely_uses_hospital_grain():
    session = AsyncMock()
    empty_result = MagicMock()
    empty_result.fetchall.return_value = []
    session.execute = AsyncMock(return_value=empty_result)

    resp = asyncio.run(cs.compute_national_coverage(session))
    timely = next(s for s in resp.sources if s.job_name == "cms_timely")
    assert timely.grain == "hospital"


def test_by_state_sums_match_national_and_epa_no_fallback(monkeypatch):
    """Every source: sum(by-state done/total) == national; EPA never falls back to all counties."""
    session = AsyncMock()
    universe = MagicMock()
    # RI: 5 counties, no monitors. CT: 5 counties, 2 monitors.
    universe.fetchall.return_value = [
        ("44001", "44"),
        ("44003", "44"),
        ("44005", "44"),
        ("44007", "44"),
        ("44009", "44"),
        ("09001", "09"),
        ("09003", "09"),
        ("09005", "09"),
        ("09007", "09"),
        ("09009", "09"),
    ]

    async def fake_fetch_cf_set(_session, sql, params):
        sql_l = " ".join(sql.split()).lower()
        if "epa_aqs_monitor_counties" in sql_l:
            return {"09001", "09003"}
        if "epa_aqi_readings" in sql_l:
            return {"09001", "09003"}
        if "census_tracts" in sql_l and "neighborhood_scores" not in sql_l and "acs_indicators" not in sql_l and "fema" not in sql_l:
            # census / nces-style tract presence — treat all counties present
            if "schools_nces" in sql_l or "schools_urban" in sql_l:
                return {
                    "44001",
                    "44003",
                    "44005",
                    "44007",
                    "44009",
                    "09001",
                    "09003",
                    "09005",
                    "09007",
                    "09009",
                }
            return {
                "44001",
                "44003",
                "44005",
                "44007",
                "44009",
                "09001",
                "09003",
                "09005",
                "09007",
                "09009",
            }
        if "neighborhood_scores" in sql_l:
            return {"44001", "09001"}
        if "crime_agency_selection" in sql_l:
            return {
                "44001",
                "44003",
                "44005",
                "44007",
                "44009",
                "09001",
                "09003",
                "09005",
                "09007",
                "09009",
            }
        if "bls_laus" in sql_l:
            return {
                "44001",
                "44003",
                "44005",
                "44007",
                "44009",
                "09001",
                "09003",
                "09005",
                "09007",
                "09009",
            }
        if "acs_indicators" in sql_l or "fema_nri" in sql_l:
            return {
                "44001",
                "44003",
                "44005",
                "44007",
                "44009",
                "09001",
                "09003",
                "09005",
                "09007",
                "09009",
            }
        if "hospitals" in sql_l:
            return {"RI", "CT"}
        return set()

    async def fake_timely_counts(_session, *, states, vintage):
        return {"RI": (5, 10), "CT": (8, 20)}

    session.execute = AsyncMock(return_value=universe)
    monkeypatch.setattr(cs, "_fetch_cf_set", fake_fetch_cf_set)
    monkeypatch.setattr(cs, "_fetch_timely_hospital_counts", fake_timely_counts)

    resp = asyncio.run(cs.compute_national_coverage(session))

    epa_nat = next(s for s in resp.sources if s.job_name == "epa")
    assert epa_nat.done_count == 2
    assert epa_nat.total_count == 2

    ri = next(s for s in resp.states if s.state_abbr == "RI")
    ri_epa = next(x for x in ri.sources if x.job_name == "epa")
    assert ri_epa.done_count == 0
    assert ri_epa.total_count == 0

    ct = next(s for s in resp.states if s.state_abbr == "CT")
    ct_epa = next(x for x in ct.sources if x.job_name == "epa")
    assert ct_epa.done_count == 2
    assert ct_epa.total_count == 2

    for job in cs.JOB_ORDER:
        nat = next(s for s in resp.sources if s.job_name == job)
        sum_done = sum(
            next(x for x in st.sources if x.job_name == job).done_count
            for st in resp.states
        )
        sum_total = sum(
            next(x for x in st.sources if x.job_name == job).total_count
            for st in resp.states
        )
        assert sum_done == nat.done_count, f"{job} done mismatch"
        assert sum_total == nat.total_count, f"{job} total mismatch"


def test_pct_helper():
    assert cs._pct(1, 4) == 25.0
    assert cs._pct(0, 0) == 0.0
