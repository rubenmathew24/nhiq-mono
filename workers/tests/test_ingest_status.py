"""Unit tests for ingest status scope resolution (no DB)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from ingest.status import (
    JobStatus,
    persist_and_log,
    resolve_scope_counties,
    resolve_scope_name,
    _pct,
)
from ingest.fixtures.canonical_addresses import default_fixture_county_fips


def test_pct():
    assert _pct(7, 10) == 70.0
    assert _pct(0, 10) == 0.0
    assert _pct(5, 0) == 0.0


def test_resolve_scope_name_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("INGEST_SCOPE", raising=False)
    assert resolve_scope_name() == "metro_10"


def test_resolve_scope_smoke(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_SCOPE", "smoke")
    monkeypatch.delenv("INGEST_COUNTY_ALLOWLIST", raising=False)
    assert resolve_scope_counties("smoke") == frozenset({"05007"})


def test_resolve_scope_metro(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_SCOPE", "metro_10")
    monkeypatch.delenv("INGEST_COUNTY_ALLOWLIST", raising=False)
    assert resolve_scope_counties("metro_10") == default_fixture_county_fips()


def test_resolve_scope_national_requires_db(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        resolve_scope_counties("national")


def test_persist_and_log_console_payload_is_slim(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """National-sized universe must not blow Log Analytics line limits."""
    huge = frozenset(f"{i:05d}" for i in range(3144))
    jobs = [
        JobStatus(
            name,
            1.0,
            1,
            3144,
            {"missing": sorted(huge)},
        )
        for name in (
            "census",
            "epa",
            "cms",
            "fbi",
            "nces",
            "urban",
            "acs",
            "bls",
            "scoring",
        )
    ]

    mock_conn = MagicMock()
    monkeypatch.setattr("ingest.status.psycopg2.connect", lambda *_a, **_k: mock_conn)
    monkeypatch.setattr("ingest.status.execute_batch", lambda *_a, **_k: None)
    monkeypatch.setattr("ingest.status.compute_job_statuses", lambda *_a, **_k: jobs)

    payload = persist_and_log("postgresql://x", "national", huge)
    out = capsys.readouterr().out
    assert "INGEST_STATUS_SNAPSHOT " in out
    line = out.strip().split("INGEST_STATUS_SNAPSHOT ", 1)[1]
    assert len(line) < 8_000
    parsed = json.loads(line)
    assert parsed["scope"] == "national"
    assert parsed["county_count"] == 3144
    assert parsed["counties"] == []
    assert "detail" not in parsed["jobs"][0]
    assert len(parsed["jobs"]) == 9
    assert payload["counties"] == []
