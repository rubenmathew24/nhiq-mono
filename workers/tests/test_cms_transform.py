"""Tests for CMS hospital transform helpers."""

from ingest.cms.transform import (
    parse_coords,
    parse_star_rating,
    transform_hospital_records,
)


def test_parse_star_rating_handles_not_available():
    assert parse_star_rating("Not Available") is None
    assert parse_star_rating("5") == 5
    assert parse_star_rating("3.0") == 3
    assert parse_star_rating(None) is None


def test_parse_coords_rejects_zeros_and_parses_wkt():
    assert parse_coords(0, 0) == (None, None)
    assert parse_coords("36.1", "-94.2") == (36.1, -94.2)
    assert parse_coords(None, None, "POINT (-94.2 36.1)") == (36.1, -94.2)


def test_transform_filters_to_fixture_states_and_field_aliases():
    raw = [
        {
            "facility_id": "10001",
            "facility_name": "AR Hospital",
            "address": "1 Main",
            "citytown": "Bentonville",
            "state": "AR",
            "zip_code": "72712",
            "countyparish": "BENTON",
            "telephone_number": "555",
            "hospital_type": "Acute Care",
            "hospital_overall_rating": "4",
            "emergency_services": "Yes",
        },
        {
            "facility_id": "20002",
            "facility_name": "OH Hospital",
            "state": "OH",
            "hospital_overall_rating": "Not Available",
            "emergency_services": "No",
        },
    ]
    out = transform_hospital_records(raw)
    assert len(out) == 1
    assert out[0]["cms_provider_id"] == "10001"
    assert out[0]["city"] == "Bentonville"
    assert out[0]["county_name"] == "BENTON"
    assert out[0]["star_rating"] == 4
    assert out[0]["emergency_services"] is True
    assert out[0]["latitude"] is None
