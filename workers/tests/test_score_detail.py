"""Unit tests for score_detail builders (UX polish)."""

from scoring.detail import (
    DetailInputs,
    FemaInputs,
    NearestFacility,
    SchoolByLevel,
    TimelyMeasure,
    _timeliness_score,
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


def test_build_detail_ordinal_ers_and_plain_english():
    detail = build_score_detail(
        DetailInputs(
            nearest_ers=[
                NearestFacility(name="Mercy NW", miles=2.1, star_rating=4, cms_provider_id="100"),
                NearestFacility(name="Hospital B", miles=4.0, star_rating=3, cms_provider_id="101"),
                NearestFacility(name="Hospital C", miles=6.0, star_rating=3, cms_provider_id="102"),
            ],
            avg_stars=4.0,
            nearest_er_miles=2.1,
            median_hh_income=80000,
            unemployment_rate=3.2,
            employed=4500,
            labor_force=4700,
            avg_aqi=42.0,
            aqi_source="open_meteo",
            schools_by_level=[
                SchoolByLevel(level="elementary", name="Central Elem", miles=0.8),
                SchoolByLevel(level="high", name="Central High", miles=2.0),
            ],
            crime=CountyCrime(
                county_fips="05007",
                by_offense={"HOM": (1.0, 2.0), "ROB": (10.0, 12.0), "ASS": (20.0, 22.0)},
                ori_count=2,
            ),
            agencies=[{"agency_name": "Bentonville PD", "ori": "AR001"}, {"agency_name": "County SO"}],
        )
    )
    hc_names = [s["name"] for s in detail["healthcare"]["stats"]]
    assert hc_names[0] == "Nearest ER"
    assert hc_names[1] == "2nd nearest ER"
    assert hc_names[2] == "3rd nearest ER"
    assert "Also nearby" not in hc_names

    safety_names = [s["name"] for s in detail["safety"]["stats"]]
    assert "Assault" in safety_names
    assert "Homicide" in safety_names
    assert not any(n.startswith("Offense ") for n in safety_names)
    assert any(s["name"] == "About these numbers" for s in detail["safety"]["stats"])
    assert detail["safety"]["sub_scores"][0]["label"] == "Crimes against people"

    aqi = next(s for s in detail["environment"]["stats"] if s["name"] == "Average AQI")
    assert "open_meteo" not in aqi["value"]
    assert "epa_aqs" not in aqi["value"]
    assert "42" in aqi["value"]

    edu_names = [s["name"] for s in detail["education"]["stats"]]
    assert "Nearest elementary" in edu_names
    assert "Nearest high" in edu_names
    assert "Pupil–teacher ratio" not in edu_names
    assert "Locale code" not in edu_names
    staffing = next(s for s in detail["education"]["sub_scores"] if s["id"] == "staffing")
    assert staffing["available"] is False

    assert any(
        s["name"] == "Share of labor force employed" for s in detail["economic"]["stats"]
    )


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


def test_timely_stat_tone_below_good_when_at_national():
    """Bentonville-style: wait ≈ national must not be ScoreBar good (≥75)."""
    timely = TimelyMeasure(
        measure_id="OP_18b",
        measure_name="ED wait",
        score_value=162.0,
        state_score=120.0,
        national_score=161.0,
    )
    tone = _timeliness_score(timely)
    assert tone is not None
    assert tone < 75

    detail = build_score_detail(
        DetailInputs(
            nearest_ers=[NearestFacility(name="H", miles=3.0, star_rating=3)],
            avg_stars=3.0,
            nearest_er_miles=3.0,
            timely=timely,
        )
    )
    wait = next(s for s in detail["healthcare"]["stats"] if s["name"] == "ER wait")
    assert wait["tone_score"] < 75
    assert "162" in wait["value"]
    assert detail["healthcare"]["sub_scores"][2]["id"] == "timeliness"
    assert detail["healthcare"]["sub_scores"][2]["available"] is True


def test_safety_category_personal_property():
    assert safety_category_score(80.0, 60.0) == 74.0
