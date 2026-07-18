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
        if "hospitals" in sql_l and "hospital_counts" not in sql_l:
            return {"RI"}
        if "hospital_counts" in sql_l or "timely_measures" in sql_l:
            return {"RI"}
        return set()

    session.execute = AsyncMock(return_value=universe)
    monkeypatch.setattr(cs, "_fetch_cf_set", fake_fetch_cf_set)

    resp = asyncio.run(cs.compute_national_coverage(session))
    scoring = next(s for s in resp.sources if s.job_name == "scoring")
    assert scoring.grain == "county"
    assert scoring.total_count == 10
    assert scoring.done_count == 2
    assert scoring.pct_complete == 20.0

    cms = next(s for s in resp.sources if s.job_name == "cms")
    assert cms.grain == "state"
    assert cms.total_count == 2

    ri = next(s for s in resp.states if s.state_abbr == "RI")
    ri_scoring = next(x for x in ri.sources if x.job_name == "scoring")
    assert ri_scoring.total_count == 5
    assert ri_scoring.done_count == 2


def test_pct_helper():
    assert cs._pct(1, 4) == 25.0
    assert cs._pct(0, 0) == 0.0
