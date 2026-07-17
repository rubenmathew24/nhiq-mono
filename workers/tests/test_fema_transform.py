"""Tests for FEMA NRI transform helpers."""

from ingest.fema.transform import (
    build_geoid,
    build_hazards,
    transform_tract_feature,
)


def test_build_geoid_from_stcofips_and_tract():
    assert build_geoid("05007", "10100") == "05007010100"
    assert build_geoid("05007", "010100") == "05007010100"
    assert build_geoid("bad", "10100") is None


def test_build_hazards_filters_by_riskr_rating():
    attrs = {
        "IFLD_RISKR": "Relatively High",
        "IFLD_RISKV": 42.0,
        "IFLD_EALR": "Relatively Moderate",
        "WFIR_RISKR": "Very Low",
        "WFIR_RISKV": 1.0,
        "HAIL_RISKR": "Relatively Moderate",
        "HAIL_RISKV": 55.0,
    }
    hazards = build_hazards(attrs)
    assert "inland_flooding" in hazards
    assert "hail" in hazards
    assert "wildfire" not in hazards
    assert hazards["inland_flooding"]["IFLD_RISKR"] == "Relatively High"


def test_transform_tract_feature_extracts_risk_fields_and_geoid():
    attrs = {
        "STCOFIPS": "05007",
        "TRACT": "10100",
        "RISK_SCORE": 88.5,
        "RISK_RATNG": "Relatively High",
        "EAL_SCORE": 70.1,
        "SOVI_SCORE": 45.2,
        "RESL_SCORE": 33.3,
        "IFLD_RISKR": "Very High",
        "IFLD_RISKV": 90.0,
    }
    row = transform_tract_feature(attrs)
    assert row is not None
    assert row["geoid"] == "05007010100"
    assert row["state_fips"] == "05"
    assert row["county_fips"] == "007"
    assert row["risk_score"] == 88.5
    assert row["risk_rating"] == "Relatively High"
    assert row["eal_score"] == 70.1
    assert row["sovi_score"] == 45.2
    assert row["resl_score"] == 33.3
    assert "inland_flooding" in row["hazards"]


def test_transform_tract_feature_respects_known_geoids():
    attrs = {
        "STCOFIPS": "05007",
        "TRACT": "10100",
        "RISK_SCORE": 1.0,
        "RISK_RATNG": "Very Low",
    }
    assert transform_tract_feature(attrs, known_geoids=frozenset({"99999999999"})) is None
