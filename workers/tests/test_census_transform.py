"""Tests for census fixture-county filter and geoid shaping."""

from ingest.census.transform import (
    filter_tract_records,
    normalize_geoid,
    row_in_fixture_county,
)


def test_normalize_geoid_accepts_11_digit():
    assert normalize_geoid("05007020100") == "05007020100"


def test_normalize_geoid_rejects_bad():
    assert normalize_geoid("short") is None
    assert normalize_geoid(None) is None


def test_row_in_fixture_county_benton_ar():
    assert row_in_fixture_county("05", "007") is True
    assert row_in_fixture_county("05", "001") is False


def test_filter_tract_records_keeps_fixture_only():
    records = [
        {
            "GEOID": "05007020100",
            "STATEFP": "05",
            "COUNTYFP": "007",
            "TRACTCE": "020100",
            "ALAND": 1_234_567,
            "AWATER": 100,
            "geometry": "geom-a",
        },
        {
            "GEOID": "05001010100",
            "STATEFP": "05",
            "COUNTYFP": "001",
            "TRACTCE": "010100",
            "geometry": "geom-b",
        },
        {
            "GEOID": "bad",
            "STATEFP": "05",
            "COUNTYFP": "007",
            "TRACTCE": "020100",
            "geometry": "geom-c",
        },
    ]
    out = filter_tract_records(records)
    assert len(out) == 1
    assert out[0]["geoid"] == "05007020100"
    assert out[0]["state_fips"] == "05"
    assert out[0]["county_fips"] == "007"
    assert out[0]["aland"] == 1_234_567
    assert out[0]["awater"] == 100


def test_filter_tract_records_persists_water_only_aland_zero():
    """Water-only tracts stay in the warehouse (aland=0); Discover filters later."""
    records = [
        {
            "GEOID": "17031990000",
            "STATEFP": "17",
            "COUNTYFP": "031",
            "TRACTCE": "990000",
            "ALAND": 0,
            "AWATER": 50_000_000,
            "geometry": "lake",
        },
    ]
    # Cook County is in metro_10 fixtures
    out = filter_tract_records(records)
    assert len(out) == 1
    assert out[0]["aland"] == 0
    assert out[0]["awater"] == 50_000_000


def test_coerce_area_m2():
    from ingest.census.transform import coerce_area_m2

    assert coerce_area_m2(0) == 0
    assert coerce_area_m2("42") == 42
    assert coerce_area_m2(None) is None
    assert coerce_area_m2(-1) is None
    assert coerce_area_m2("x") is None
