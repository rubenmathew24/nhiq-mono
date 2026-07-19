"""Checkpoint helpers for FEMA / CMS Timely / score_detail."""

from __future__ import annotations

from ingest.checkpoints import (
    counties_with_fema_nri,
    counties_with_score_detail,
    states_with_timely_measures,
)


def test_counties_with_fema_nri_empty():
    assert counties_with_fema_nri("postgresql://x", []) == set()


def test_counties_with_fema_nri_sql(monkeypatch):
    seen: dict = {}

    def fake_fetch(url, sql, params):
        seen["sql"] = sql
        seen["params"] = params
        return {"05007"}

    monkeypatch.setattr("ingest.checkpoints._fetch_set", fake_fetch)
    assert counties_with_fema_nri("postgresql://x", ["05007"]) == {"05007"}
    assert "fema_nri_tracts" in seen["sql"]
    assert "99%" in seen["sql"] or "99%%" in seen["sql"]


def test_counties_with_score_detail_sql(monkeypatch):
    seen: dict = {}

    def fake_fetch(url, sql, params):
        seen["sql"] = sql
        seen["params"] = params
        return set()

    monkeypatch.setattr("ingest.checkpoints._fetch_set", fake_fetch)
    counties_with_score_detail(
        "postgresql://x", ["05007"], data_vintage="2026-Q3"
    )
    assert "score_detail" in seen["sql"]
    assert seen["params"] == (["05007"], "2026-Q3")


def test_states_with_timely_measures_empty():
    assert (
        states_with_timely_measures("postgresql://x", [], data_vintage="2026-Q3")
        == set()
    )
