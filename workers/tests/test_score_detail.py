"""Unit tests for score_detail builders."""

from scoring.detail import (
    DetailInputs,
    FemaInputs,
    NearestFacility,
    TimelyMeasure,
    build_score_detail,
    healthcare_category_score,
    safety_category_score,
)
from scoring.safety import CountyCrime


def test_healthcare_blend_access_quality():
    score = healthcare_category_score(100.0, 75.0, None)
    assert 80 <= score <= 90


def test_healthcare_with_timely():
    score = healthcare_category_score(80.0, 80.0, 80.0)
    assert score == 80.0


def test_build_detail_nearest_er_stats():
    detail = build_score_detail(
        DetailInputs(
            nearest_ers=[
                NearestFacility(name="Mercy NW", miles=2.1, star_rating=4, cms_provider_id="100"),
            ],
            avg_stars=4.0,
            nearest_er_miles=2.1,
            median_hh_income=80000,
            unemployment_rate=3.2,
            avg_aqi=42.0,
            aqi_source="epa_aqs",
            school_name="Central Elem",
            nearest_school_miles=0.8,
            enrollment=400,
            teachers_fte=25.0,
            crime=CountyCrime(
                county_fips="05007",
                by_offense={"HOM": (1.0, 2.0), "ROB": (10.0, 12.0), "ASS": (20.0, 22.0)},
                ori_count=2,
            ),
        )
    )
    assert detail["healthcare"]["sub_scores"][0]["available"] is True
    assert "Mercy" in detail["healthcare"]["stats"][0]["value"]
    assert detail["education"]["stats"][0]["name"] == "Nearest school"
    assert detail["economic"]["sub_scores"][0]["id"] == "income"
    assert detail["environment"]["sub_scores"][0]["available"] is True
    assert detail["safety"]["sub_scores"][0]["available"] is True


def test_hazard_and_timely_unavailable_copy():
    detail = build_score_detail(DetailInputs())
    assert any(s["value"] == "Unavailable" for s in detail["healthcare"]["stats"])
    assert any(s["name"] == "Hazard risk" for s in detail["environment"]["stats"])


def test_fema_hazard_subscore():
    detail = build_score_detail(
        DetailInputs(
            fema=FemaInputs(risk_rating="Relatively Moderate", risk_score=55.0, hazards={}),
            avg_aqi=40.0,
        )
    )
    hazard = next(s for s in detail["environment"]["sub_scores"] if s["id"] == "hazard")
    assert hazard["available"] is True
    assert hazard["score"] == 55.0


def test_timely_stat():
    detail = build_score_detail(
        DetailInputs(
            nearest_ers=[NearestFacility(name="H", miles=3.0, star_rating=3)],
            avg_stars=3.0,
            nearest_er_miles=3.0,
            timely=TimelyMeasure(
                measure_id="OP_18b",
                measure_name="ED wait",
                score_value=28.0,
                state_score=35.0,
            ),
        )
    )
    assert any("28" in s["value"] for s in detail["healthcare"]["stats"])
    assert detail["healthcare"]["sub_scores"][2]["id"] == "timeliness"
    assert detail["healthcare"]["sub_scores"][2]["available"] is True


def test_safety_category_personal_property():
    assert safety_category_score(80.0, 60.0) == 74.0
