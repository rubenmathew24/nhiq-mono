"""Unit tests for gap inventory and orchestrator queue helpers."""

from __future__ import annotations

from ingest.inventory import (
    PIPELINE_WORKERS,
    WORKER_ACA_JOB,
    build_inventory,
    states_needing_work,
    workers_needed_for_state,
)


def test_build_inventory_gaps_with_mocked_done(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")

    def fake_universe(_url: str):
        return frozenset({"44001", "44003", "06001"})

    monkeypatch.setattr(
        "ingest.inventory.load_national_universe_counties", fake_universe
    )

    def census_done(_url, counties):
        return {"44001"}  # 44003 and 06001 missing

    def epa_done(_url, counties):
        return set(counties)  # all done

    def empty_done(_url, counties):
        return set()

    def hospitals(_url, abbrs):
        return {"RI"}  # RI done; CA not

    def timely(_url, abbrs, data_vintage=None):
        return set(abbrs)

    monkeypatch.setattr("ingest.inventory.states_with_hospitals", hospitals)
    monkeypatch.setattr("ingest.inventory.states_with_timely_measures", timely)

    inv = build_inventory(
        "postgresql://x",
        state_filter=frozenset({"44", "06"}),
        done_fns={
            "census": census_done,
            "epa": epa_done,
            "fbi": empty_done,
            "nces": empty_done,
            "urban": empty_done,
            "acs": empty_done,
            "bls": empty_done,
            "fema": empty_done,
            "scoring": empty_done,
        },
    )
    assert "44001" not in inv["gaps"]["census"]
    assert "44003" in inv["gaps"]["census"]
    assert inv["gaps"]["epa"] == []
    assert "44" not in inv["by_state"]["epa"]
    assert inv["by_state"]["census"]["44"] == ["44003"]
    assert "44" not in inv["gaps"]["cms"]
    assert "06" in inv["gaps"]["cms"]
    assert "fema" in inv["summary"]
    assert "cms_timely" in inv["summary"]
    assert WORKER_ACA_JOB["fema"] == "niq-worker-fema"
    assert WORKER_ACA_JOB["cms_timely"] == "niq-worker-cms-timely"


def test_workers_needed_skips_complete_worker():
    inv = {
        "by_state": {
            "census": {"44": ["44001"]},
            "epa": {},
            "cms": {"44": ["44"]},
            "fbi": {"44": ["44001"]},
            "nces": {},
            "urban": {},
            "acs": {},
            "bls": {},
            "fema": {},
            "cms_timely": {},
            "scoring": {},
        }
    }
    needed = workers_needed_for_state(inv, "44")
    assert needed == ["census", "cms", "fbi"]
    assert "epa" not in needed


def test_states_needing_work_respects_max():
    inv = {
        "by_state": {
            "census": {"06": ["06001"], "44": ["44001"]},
            "epa": {},
            "cms": {},
            "fbi": {},
            "nces": {},
            "urban": {},
            "acs": {},
            "bls": {},
            "fema": {},
            "cms_timely": {},
            "scoring": {},
        }
    }
    assert states_needing_work(inv, max_states=1) == ["06"]
    assert states_needing_work(inv, max_states=5) == ["06", "44"]


def test_force_states_included_even_when_complete():
    inv = {
        "by_state": {
            "census": {},
            "epa": {},
            "cms": {},
            "fbi": {},
            "nces": {},
            "urban": {},
            "acs": {},
            "bls": {},
            "fema": {},
            "cms_timely": {},
            "scoring": {},
        }
    }
    assert states_needing_work(inv, max_states=5, force_states=frozenset({"25"})) == [
        "25"
    ]
    assert workers_needed_for_state(inv, "25", force=True) == list(PIPELINE_WORKERS)
