"""Tests for INGEST_COUNTY_ALLOWLIST env resolution."""

from __future__ import annotations

import os

import pytest

from ingest.fixtures.canonical_addresses import (
    active_canonical_addresses,
    default_fixture_county_fips,
    fixture_county_fips,
    fixture_state_abbrs,
    fixture_state_fips,
    parse_county_allowlist,
)


def test_parse_county_allowlist_none_and_blank():
    assert parse_county_allowlist(None) is None
    assert parse_county_allowlist("") is None
    assert parse_county_allowlist("   ") is None


def test_parse_county_allowlist_valid_and_invalid_tokens():
    assert parse_county_allowlist("05007") == frozenset({"05007"})
    assert parse_county_allowlist("05007,17031") == frozenset({"05007", "17031"})
    assert parse_county_allowlist("05007, bad, 12") == frozenset({"05007"})
    assert parse_county_allowlist("not-a-fips") is None


def test_fixture_county_fips_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("INGEST_COUNTY_ALLOWLIST", raising=False)
    assert fixture_county_fips() == default_fixture_county_fips()
    assert len(fixture_county_fips()) == 10


def test_fixture_county_fips_single_smoke(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_COUNTY_ALLOWLIST", "05007")
    assert fixture_county_fips() == frozenset({"05007"})
    assert fixture_state_fips() == frozenset({"05"})
    assert fixture_state_abbrs() == frozenset({"AR"})
    addrs = active_canonical_addresses()
    assert len(addrs) == 1
    assert addrs[0].county_fips == "05007"


def test_fixture_county_fips_ignores_unknown(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_COUNTY_ALLOWLIST", "05007,99999")
    assert fixture_county_fips() == frozenset({"05007"})


def test_fixture_county_fips_unknown_only_falls_back(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_COUNTY_ALLOWLIST", "99999")
    assert fixture_county_fips() == default_fixture_county_fips()


def test_env_cleared_between_tests(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("INGEST_COUNTY_ALLOWLIST", "05007")
    assert "05007" in fixture_county_fips()
    monkeypatch.delenv("INGEST_COUNTY_ALLOWLIST", raising=False)
    # Ensure tests do not leak a stuck env var into later modules.
    os.environ.pop("INGEST_COUNTY_ALLOWLIST", None)
    assert len(fixture_county_fips()) == 10
