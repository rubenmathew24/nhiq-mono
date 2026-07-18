"""Fail-closed national registry + exclude-complete honesty (007 Phase 8)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ingest.geo.jurisdictions import INCLUDED_STATE_FIPS
from ingest.geo.scope import (
    IncompleteNationalRegistryError,
    validate_national_registry,
)
import ingest.orchestrate.run as orch
from ingest.status import resolve_scope_counties


def test_validate_empty_registry_raises():
    with pytest.raises(IncompleteNationalRegistryError, match="empty"):
        validate_national_registry(frozenset())


def test_validate_incomplete_registry_raises():
    # Only one included state present.
    counties = frozenset({"44007", "44001"})
    with pytest.raises(IncompleteNationalRegistryError, match="incomplete"):
        validate_national_registry(counties, present_states=frozenset({"44"}))


def test_validate_complete_registry_ok():
    # One synthetic county per included jurisdiction is enough for the check.
    counties = frozenset(f"{sf}001" for sf in sorted(INCLUDED_STATE_FIPS))
    validate_national_registry(
        counties, present_states=frozenset(INCLUDED_STATE_FIPS)
    )


def test_status_national_fail_closed_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.delenv("INGEST_COUNTY_ALLOWLIST", raising=False)

    def _empty(_url: str):
        raise IncompleteNationalRegistryError("geo_counties is empty for included 50+DC.")

    monkeypatch.setattr(
        "ingest.status.require_complete_national_registry", _empty
    )
    with pytest.raises(IncompleteNationalRegistryError, match="empty"):
        resolve_scope_counties("national", database_url="postgresql://x")


def test_orch_blocked_excluded_not_complete(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("ORCH_CONTINUOUS", "1")
    monkeypatch.setenv("ORCH_STATE_EXCLUDE", "06")
    monkeypatch.delenv("ORCH_STATE_FILTER", raising=False)
    monkeypatch.delenv("ORCH_FORCE_STATES", raising=False)

    inv = {
        "summary": {"census": 1},
        "by_state": {"census": {"06": ["06037"]}},
    }

    def _states_needing_work(
        _inv,
        *,
        max_states=None,
        force_states=frozenset(),
        exclude_states=frozenset(),
        exclusive=False,
    ):
        # With exclude: nothing to schedule. Without exclude: CA still has gaps.
        if exclude_states and "06" in exclude_states:
            return []
        return ["06"]

    with patch.object(orch, "client_from_env", return_value=MagicMock()):
        with patch.object(orch, "build_inventory", return_value=inv):
            with patch.object(
                orch, "states_needing_work", side_effect=_states_needing_work
            ):
                with patch.object(orch, "run_status_emit"):
                    code = orch.run()
    assert code == 1


def test_orch_true_complete_still_zero(monkeypatch: pytest.MonkeyPatch):
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


def test_orch_registry_incomplete_exits_one(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("ORCH_CONTINUOUS", "1")
    monkeypatch.delenv("ORCH_STATE_FILTER", raising=False)
    monkeypatch.delenv("ORCH_FORCE_STATES", raising=False)
    monkeypatch.delenv("ORCH_STATE_EXCLUDE", raising=False)

    with patch.object(orch, "client_from_env", return_value=MagicMock()):
        with patch.object(
            orch,
            "build_inventory",
            side_effect=IncompleteNationalRegistryError("incomplete"),
        ):
            code = orch.run()
    assert code == 1
