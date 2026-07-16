"""Education formula — access by level (no PTR/locale in category score)."""

from ingest.fixtures.constants import SOURCE_DEFAULT, SOURCE_NCES_URBAN
from scoring.education import (
    EducationInputs,
    access_score_from_distance,
    education_from_sources,
    staffing_score_from_ratio,
)
from scoring.formulas import distance_score_miles


def test_access_score_near_school_scores_high():
    assert access_score_from_distance(0.2) == 100.0
    assert access_score_from_distance(10.0) == 20.0


def test_staffing_score_prefers_moderate_ratio():
    assert staffing_score_from_ratio(550, 35) == 100.0
    assert staffing_score_from_ratio(800, 20) < 50.0


def test_category_score_matches_by_level_access_average():
    """Category score must match Access sub-score (avg distance_score, ≤30 mi)."""
    miles = [0.8, 2.0]
    expected = round(sum(distance_score_miles(m) for m in miles) / len(miles), 1)
    result = education_from_sources(
        EducationInputs(
            level_miles=miles,
            nearest_miles=0.5,
            locale="13",
            enrollment=550,
            teachers_fte=35,
            ncessch="050005500513",
        )
    )
    assert result.score == expected
    assert result.provenance["source_id"] == SOURCE_NCES_URBAN
    assert result.provenance["reason"] == "access_by_level"
    assert result.provenance["contributors"] == ["nces_school_data"]
    assert "pupil_teacher_ratio" not in result.provenance


def test_excludes_schools_beyond_cutoff():
    result = education_from_sources(
        EducationInputs(level_miles=[1.0, 457.0]),
    )
    assert result.score == round(distance_score_miles(1.0), 1)
    assert result.provenance["levels_in_range"] == 1


def test_ptr_and_locale_do_not_change_category_score():
    base = education_from_sources(EducationInputs(level_miles=[1.0]))
    with_ptr = education_from_sources(
        EducationInputs(level_miles=[1.0], enrollment=800, teachers_fte=20, locale="41")
    )
    assert base.score == with_ptr.score


def test_fallback_nearest_when_no_levels():
    result = education_from_sources(EducationInputs(nearest_miles=0.5))
    assert result.provenance["reason"] == "access_by_level"
    assert result.score == round(distance_score_miles(0.5), 1)


def test_both_missing_defaults_to_50_not_placeholder_70():
    result = education_from_sources(
        EducationInputs(), has_nces_table=False, has_urban_table=False
    )
    assert result.score == 50.0
    assert result.provenance["source_id"] == SOURCE_DEFAULT
