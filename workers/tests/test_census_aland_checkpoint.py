"""Census checkpoint requires TIGER aland populated (mocked SQL contract)."""

from __future__ import annotations

from ingest.checkpoints import counties_with_census_tracts


def test_counties_with_census_tracts_empty_input():
    assert counties_with_census_tracts("postgresql://x", []) == set()


def test_counties_with_census_requires_aland(monkeypatch):
    """Done-check must require non-NULL aland on every tract (not mere row existence)."""
    seen: dict = {}

    def fake_fetch(url, sql, params):
        seen["sql"] = sql
        seen["params"] = params
        return {"05007"}

    monkeypatch.setattr("ingest.checkpoints._fetch_set", fake_fetch)
    out = counties_with_census_tracts("postgresql://x", ["05007", "17031"])
    assert out == {"05007"}
    sql_l = " ".join(seen["sql"].split()).lower()
    assert "census_tracts" in sql_l
    assert "aland is null" in sql_l
    assert "having" in sql_l
    assert seen["params"] == (["05007", "17031"],)
