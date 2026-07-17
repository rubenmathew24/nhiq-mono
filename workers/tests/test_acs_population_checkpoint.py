"""Unit tests documenting ACS population checkpoint SQL contract (mocked)."""

from __future__ import annotations

from ingest.checkpoints import counties_with_acs


def test_counties_with_acs_empty_input():
    assert counties_with_acs("postgresql://x", []) == set()


def test_counties_with_acs_uses_population_join(monkeypatch):
    """Done-check must require total_population (not mere ACS row existence)."""
    seen: dict = {}

    def fake_fetch(url, sql, params):
        seen["sql"] = sql
        seen["params"] = params
        return {"05007"}

    monkeypatch.setattr("ingest.checkpoints._fetch_set", fake_fetch)
    out = counties_with_acs("postgresql://x", ["05007", "06001"])
    assert out == {"05007"}
    assert "total_population" in seen["sql"]
    assert "acs_indicators" in seen["sql"]
    assert seen["params"] == (["05007", "06001"],)
