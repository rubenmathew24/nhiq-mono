"""Tests for ACS tract/state transform helpers."""

from ingest.acs.transform import transform_acs_rows, transform_acs_state_rows


def test_transform_maps_tract_geoid_and_income():
    rows = [
        {
            "state": "05",
            "county": "007",
            "tract": "020101",
            "B01003_001E": "4200",
            "B19013_001E": "78500",
            "B23025_002E": "1200",
            "B23025_004E": "1150",
            "B23025_005E": "50",
        }
    ]
    out = transform_acs_rows(rows, acs_year="2022")
    assert len(out) == 1
    assert out[0]["geoid"] == "05007020101"
    assert out[0]["geo_level"] == "tract"
    assert out[0]["median_hh_income"] == 78500.0
    assert out[0]["labor_force"] == 1200.0
    assert out[0]["total_population"] == 4200.0
    assert out[0]["acs_year"] == "2022"


def test_transform_state_population():
    rows = [{"state": "05", "B01003_001E": "3011524", "B19013_001E": "52000"}]
    out = transform_acs_state_rows(rows, acs_year="2022")
    assert len(out) == 1
    assert out[0]["geoid"] == "05"
    assert out[0]["geo_level"] == "state"
    assert out[0]["total_population"] == 3011524.0


def test_transform_treats_census_null_sentinels_as_none():
    rows = [
        {
            "state": "05",
            "county": "007",
            "tract": "020102",
            "B01003_001E": "-666666666",
            "B19013_001E": "-666666666",
            "B23025_002E": "",
        }
    ]
    out = transform_acs_rows(rows, acs_year="2022")
    assert out[0]["median_hh_income"] is None
    assert out[0]["labor_force"] is None
    assert out[0]["total_population"] is None
