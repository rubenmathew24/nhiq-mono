"""Education formula from NCES access + Urban staffing."""

from ingest.fixtures.constants import SOURCE_DEFAULT, SOURCE_NCES_URBAN
from scoring.education import (
    EducationInputs,
    access_score_from_distance,
    education_from_sources,
    staffing_score_from_ratio,
)


def test_access_score_near_school_scores_high():
    assert access_score_from_distance(0.2) == 100.0
    assert access_score_from_distance(10.0) == 20.0


def test_staffing_score_prefers_moderate_ratio():
    assert staffing_score_from_ratio(550, 35) == 100.0
    assert staffing_score_from_ratio(800, 20) < 50.0


def test_dual_source_blend_uses_nces_urban_provenance():
    result = education_from_sources(
        EducationInputs(
            nearest_miles=1.0,
            locale="21",
            enrollment=550,
            teachers_fte=35,
            ncessch="050005500513",
        )
    )
    assert result.provenance["source_id"] == SOURCE_NCES_URBAN
    assert result.provenance["reason"] == "nces_urban_blend"
    assert "nces_school_data" in result.provenance["contributors"]
    assert "urban_school_data" in result.provenance["contributors"]
    assert 50.0 < result.score < 100.0


def test_partial_nces_when_urban_missing():
    result = education_from_sources(
        EducationInputs(nearest_miles=0.5, locale="13"),
        has_urban_table=False,
    )
    assert result.provenance["source_id"] == SOURCE_NCES_URBAN
    assert result.provenance["reason"] == "partial_urban"
    assert result.provenance["contributors"] == ["nces_school_data"]


def test_both_missing_defaults_to_50_not_placeholder_70():
    result = education_from_sources(EducationInputs(), has_nces_table=False, has_urban_table=False)
    assert result.score == 50.0
    assert result.provenance["source_id"] == SOURCE_DEFAULT
