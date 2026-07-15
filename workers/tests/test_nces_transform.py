"""Tests for NCES EDGE transform helpers."""

from ingest.nces.transform import transform_nces_features


def test_transform_keeps_fixture_county_schools():
    features = [
        {
            "attributes": {
                "NCESSCH": "050005500513",
                "LEAID": "0500055",
                "NAME": "ARKANSAS ARTS ACADEMY ELEMENTARY",
                "STFIP": "05",
                "CNTY": "05007",
                "LOCALE": "21",
                "LAT": 36.35,
                "LON": -94.22,
            },
            "geometry": {"x": -94.22, "y": 36.35},
        },
        {
            "attributes": {
                "NCESSCH": "390000100001",
                "STFIP": "39",
                "CNTY": "39035",
                "LAT": 41.0,
                "LON": -81.0,
            },
            "geometry": {"x": -81.0, "y": 41.0},
        },
    ]
    out = transform_nces_features(features)
    assert len(out) == 1
    assert out[0]["ncessch"] == "050005500513"
    assert out[0]["state_fips"] == "05"
    assert out[0]["county_fips"] == "007"
    assert out[0]["latitude"] == 36.35


def test_transform_skips_missing_coords():
    features = [
        {
            "attributes": {
                "NCESSCH": "050005500513",
                "STFIP": "05",
                "CNTY": "05007",
                "LAT": 0,
                "LON": 0,
            },
            "geometry": None,
        }
    ]
    assert transform_nces_features(features) == []
