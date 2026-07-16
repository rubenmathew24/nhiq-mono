"""Tests for national scope resolution and batch guards."""

from __future__ import annotations

import pytest

from ingest.fixtures.canonical_addresses import default_fixture_county_fips
from ingest.geo.jurisdictions import INCLUDED_STATE_FIPS, TERRITORY_STATE_FIPS
from ingest.geo.scope import (
    require_national_state_batch,
    resolve_ingest_scope,
    active_county_fips,
)


def test_included_excludes_territories():
    assert "11" in INCLUDED_STATE_FIPS  # DC
    assert "06" in INCLUDED_STATE_FIPS
    assert not (INCLUDED_STATE_FIPS & TERRITORY_STATE_FIPS)
    assert "72" in TERRITORY_STATE_FIPS  # PR reserved


def test_national_requires_batch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_SCOPE", "national")
    monkeypatch.delenv("INGEST_STATE_BATCH", raising=False)
    with pytest.raises(RuntimeError, match="INGEST_STATE_BATCH"):
        require_national_state_batch()


def test_national_rejects_territory_batch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_SCOPE", "national")
    monkeypatch.setenv("INGEST_STATE_BATCH", "72")
    with pytest.raises(RuntimeError, match="not in 50\\+DC"):
        require_national_state_batch()


def test_metro_default_unchanged(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("INGEST_SCOPE", raising=False)
    monkeypatch.delenv("INGEST_COUNTY_ALLOWLIST", raising=False)
    assert resolve_ingest_scope() == "metro_10"
    assert active_county_fips() == default_fixture_county_fips()


def test_smoke_scope(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_SCOPE", "smoke")
    monkeypatch.delenv("INGEST_COUNTY_ALLOWLIST", raising=False)
    assert active_county_fips() == frozenset({"05007"})
