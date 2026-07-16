"""Unit tests for force helper, status pulse, and ARM retries."""

from __future__ import annotations

from unittest.mock import patch

import httpx

from ingest.force import force_enabled
from ingest.inventory import PIPELINE_WORKERS, states_needing_work, workers_needed_for_state
from ingest.orchestrate.azure_jobs import _request_with_retries
from ingest.status_pulse import StatusPulse


def test_force_enabled_truthy(monkeypatch):
    monkeypatch.setenv("INGEST_FORCE", "1")
    assert force_enabled() is True
    monkeypatch.setenv("INGEST_FORCE", "YES")
    assert force_enabled() is True
    monkeypatch.setenv("INGEST_FORCE", "0")
    assert force_enabled() is False
    monkeypatch.delenv("INGEST_FORCE", raising=False)
    assert force_enabled() is False


def test_force_enabled_from_dict():
    assert force_enabled({"INGEST_FORCE": "true"}) is True
    assert force_enabled({"INGEST_FORCE": ""}) is False


def test_states_needing_work_force_exclusive_no_pad():
    inv = {
        "by_state": {
            "census": {"06": ["06001"]},
            "epa": {},
            "cms": {},
            "fbi": {},
            "nces": {},
            "urban": {},
            "acs": {},
            "bls": {},
            "scoring": {},
        }
    }
    # Forced 25 only — must not pad with gap state 06 even when max_states=5
    ordered = states_needing_work(
        inv, max_states=5, force_states=frozenset({"25"}), exclusive=True
    )
    assert ordered == ["25"]


def test_states_needing_work_unscoped_still_pads():
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
            "scoring": {},
        }
    }
    ordered = states_needing_work(inv, max_states=5, exclusive=False)
    assert ordered == ["06", "44"]


def test_workers_needed_force_returns_full_pipeline():
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
            "scoring": {},
        }
    }
    assert workers_needed_for_state(inv, "25", force=True) == list(PIPELINE_WORKERS)
    assert workers_needed_for_state(inv, "25", force=False) == []


def test_status_pulse_emits_every_n(monkeypatch):
    calls: list[int] = []

    def fake_emit(url, *, scope=None):
        calls.append(1)
        return {}

    monkeypatch.setattr("ingest.status_pulse.emit_status_snapshot", fake_emit)
    pulse = StatusPulse("postgresql://x", every_n=3)
    for _ in range(7):
        pulse.tick()
    assert len(calls) == 2  # at 3 and 6
    pulse.flush()
    assert len(calls) == 3  # remainder at 7


def test_arm_retries_then_succeeds():
    responses = [
        httpx.Response(500, text='{"error":"boom"}'),
        httpx.Response(500, text='{"error":"boom"}'),
        httpx.Response(200, json={"ok": True}),
    ]
    call_count = {"n": 0}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def request(self, method, url, headers=None, json=None):
            i = call_count["n"]
            call_count["n"] += 1
            return responses[i]

    with (
        patch("ingest.orchestrate.azure_jobs.httpx.Client", FakeClient),
        patch("ingest.orchestrate.azure_jobs.time.sleep"),
    ):
        resp = _request_with_retries(
            "PATCH",
            "https://example/jobs/x",
            headers={},
            json_body={},
            retries=3,
        )
    assert resp.status_code == 200
    assert call_count["n"] == 3
