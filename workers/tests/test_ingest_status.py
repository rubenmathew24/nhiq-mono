"""Unit tests for ingest status scope resolution (no DB)."""

from __future__ import annotations

import pytest

from ingest.status import resolve_scope_counties, resolve_scope_name, _pct
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
