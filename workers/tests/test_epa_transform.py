"""Tests for EPA AQI transform and fixture-county filter."""

from ingest.epa.transform import transform_aqi_records


def test_transform_keeps_fixture_county_and_skips_bad():
    raw = [
        {
            "state_code": "05",
            "county_code": "007",
            "parameter_code": "44201",
            "parameter": "Ozone",
            "aqi": "42",
            "category": "Good",
            "date_local": "2026-07-13",
            "state": "Arkansas",
            "county": "Benton",
        },
        {
            "state_code": "05",
            "county_code": "001",
            "parameter_code": "44201",
            "parameter": "Ozone",
            "aqi": "10",
            "category": "Good",
            "date_local": "2026-07-13",
            "state": "Arkansas",
            "county": "Arkansas",
        },
        {
            # missing state_code → skip
            "county_code": "007",
            "parameter_code": "44201",
            "aqi": "1",
            "date_local": "2026-07-13",
        },
    ]
    out = transform_aqi_records(raw)
    assert len(out) == 1
    assert out[0]["county_fips"] == "05007"
    assert out[0]["aqi"] == 42
    assert out[0]["parameter_name"] == "Ozone"


def test_transform_null_aqi_allowed():
    raw = [
        {
            "state_code": "48",
            "county_code": "453",
            "parameter_code": "88101",
            "parameter": "PM2.5",
            "aqi": None,
            "category": None,
            "date_local": "2026-07-13",
            "state": "Texas",
            "county": "Travis",
        }
    ]
    out = transform_aqi_records(raw)
    assert len(out) == 1
    assert out[0]["county_fips"] == "48453"
    assert out[0]["aqi"] is None


def test_transform_respects_custom_allowlist():
    raw = [
        {
            "state_code": "05",
            "county_code": "007",
            "parameter_code": "44201",
            "parameter": "Ozone",
            "aqi": 5,
            "date_local": "2026-07-13",
            "state": "Arkansas",
            "county": "Benton",
        }
    ]
    out = transform_aqi_records(raw, county_allowlist=frozenset({"99999"}))
    assert out == []


def test_transform_dedupes_same_county_param_day_keeps_max_aqi():
    raw = [
        {
            "state_code": "04",
            "county_code": "013",
            "parameter_code": "44201",
            "parameter": "Ozone",
            "aqi": 40,
            "date_local": "2025-06-08",
            "state": "Arizona",
            "county": "Maricopa",
        },
        {
            "state_code": "04",
            "county_code": "013",
            "parameter_code": "44201",
            "parameter": "Ozone",
            "aqi": 55,
            "date_local": "2025-06-08",
            "state": "Arizona",
            "county": "Maricopa",
        },
    ]
    out = transform_aqi_records(raw)
    assert len(out) == 1
    assert out[0]["aqi"] == 55
