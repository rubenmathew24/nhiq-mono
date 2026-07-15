"""Tests for Urban CCD directory transform helpers."""

from ingest.urban.transform import transform_urban_records


def test_transform_filters_by_ncessch_allowlist():
    raw = [
        {
            "ncessch": "050005500513",
            "county_code": "5007",
            "enrollment": 550,
            "teachers_fte": 35,
            "school_level": "1",
            "charter": 1,
        },
        {
            "ncessch": "010000500870",
            "county_code": "1095",
            "enrollment": 400,
            "teachers_fte": 20,
        },
    ]
    out = transform_urban_records(
        raw, year=2022, ncessch_allowlist=frozenset({"050005500513"})
    )
    assert len(out) == 1
    assert out[0]["ncessch"] == "050005500513"
    assert out[0]["year"] == 2022
    assert out[0]["enrollment"] == 550
    assert out[0]["teachers_fte"] == 35.0


def test_transform_keeps_all_when_no_allowlist():
    raw = [
        {
            "ncessch": "170000000001",
            "county_code": "17031",
            "enrollment": 100,
            "teachers_fte": 8,
        }
    ]
    out = transform_urban_records(raw, year=2022)
    assert len(out) == 1
    assert out[0]["ncessch"] == "170000000001"
