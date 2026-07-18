"""Orchestrator continuous batching + exit-code helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import ingest.orchestrate.run as orch


def test_batch_states_default(monkeypatch):
    monkeypatch.delenv("ORCH_BATCH_STATES", raising=False)
    assert orch._batch_states() == 10
    monkeypatch.setenv("ORCH_BATCH_STATES", "7")
    assert orch._batch_states() == 7


def test_continuous_truthy(monkeypatch):
    monkeypatch.setenv("ORCH_CONTINUOUS", "true")
    assert orch._continuous_enabled() is True
    monkeypatch.setenv("ORCH_CONTINUOUS", "0")
    assert orch._continuous_enabled() is False


def test_run_exits_complete_when_no_gaps(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("ORCH_CONTINUOUS", "1")
    monkeypatch.delenv("ORCH_STATE_FILTER", raising=False)
    monkeypatch.delenv("ORCH_FORCE_STATES", raising=False)
    monkeypatch.delenv("ORCH_STATE_EXCLUDE", raising=False)

    inv = {"summary": {}, "by_state": {}}
    with patch.object(orch, "client_from_env", return_value=MagicMock()):
        with patch.object(orch, "build_inventory", return_value=inv):
            with patch.object(orch, "states_needing_work", return_value=[]):
                with patch.object(orch, "run_status_emit"):
                    code = orch.run()
    assert code == 0


def test_run_exits_more_work_on_budget(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("ORCH_CONTINUOUS", "1")
    monkeypatch.setenv("ORCH_TIME_BUDGET_SECONDS", "60")
    monkeypatch.delenv("ORCH_STATE_FILTER", raising=False)
    monkeypatch.delenv("ORCH_FORCE_STATES", raising=False)
    monkeypatch.delenv("ORCH_STATE_EXCLUDE", raising=False)

    inv = {
        "summary": {"census": 1},
        "by_state": {"census": {"44": ["44007"]}},
    }
    client = MagicMock()

    # First inventory has gaps; pass hits budget immediately.
    with patch.object(orch, "client_from_env", return_value=client):
        with patch.object(orch, "build_inventory", return_value=inv):
            with patch.object(orch, "states_needing_work", return_value=["44"]):
                with patch.object(
                    orch,
                    "_run_bounded_pass",
                    return_value=(False, True),
                ):
                    with patch.object(orch, "run_status_emit"):
                        with patch.object(
                            orch, "_inventory_has_gaps", return_value=True
                        ):
                            code = orch.run()
    assert code == 2
