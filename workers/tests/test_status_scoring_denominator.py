"""Scoring status must use national county denominator, not loaded tracts."""

from __future__ import annotations

from unittest.mock import MagicMock

from ingest.fixtures.constants import DATA_VINTAGE
from ingest.status import JobStatus, compute_job_statuses


def test_scoring_denominator_is_county_universe_not_tract_count():
    """Partial census must not inflate scoring % (FR-001 / FR-002)."""
    # Use real included FIPS so CMS state_abbr mapping stays valid.
    counties = frozenset(
        {
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
    )
    cur = MagicMock()

    def execute(sql, params=None):
        execute.last_sql = " ".join(sql.split())
        execute.last_params = params

    execute.last_sql = ""
    execute.last_params = None
    cur.execute = execute

    fetch_results = []

    def fetchone():
        if fetch_results:
            return fetch_results.pop(0)
        return (0,)

    def fetchall():
        return []

    cur.fetchone = fetchone
    cur.fetchall = fetchall

    # compute_job_statuses runs many queries; we only assert the scoring JobStatus
    # at the end by stubbing everything to empty then injecting scoring result.
    # Simpler approach: call scoring logic by patching intermediate queries via
    # side_effect sequence that ends with scoring done count.

    # Build a minimal path: empty results for all county/state queries, then
    # scoring subquery returns done=2.
    call_n = {"i": 0}

    def fetchone_seq():
        # Most COUNT queries return 0; the last scoring COUNT returns 2.
        call_n["i"] += 1
        # Scoring is the last COUNT(*)::int before return — return 2 always for
        # COUNT queries when SQL mentions done_counties / score_detail.
        sql = execute.last_sql
        if "done_counties" in sql or (
            "score_detail" in sql and "COUNT(*)::int" in sql and "WITH scoped" in sql
        ):
            return (2,)
        return (0,)

    cur.fetchone = fetchone_seq
    cur.fetchall = lambda: []

    statuses = compute_job_statuses(cur, counties, "national")
    scoring = next(s for s in statuses if s.job_name == "scoring")
    assert isinstance(scoring, JobStatus)
    assert scoring.total_count == 10
    assert scoring.done_count == 2
    assert scoring.pct_complete == 20.0
    assert scoring.detail.get("metric") == "counties_with_fbi_cde_and_score_detail"
    # Vintage must be applied so inventory + status agree.
    assert execute.last_params[1] == DATA_VINTAGE
