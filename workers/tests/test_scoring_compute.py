"""Unit tests for scoring formula helpers (no DB)."""

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    DEFAULT_HEALTHCARE_SCORE,
)
from scoring.formulas import (
    distance_score_miles,
    environment_from_aqi,
    healthcare_from_nearest,
    weighted_overall,
)


def test_distance_score_bounds():
    assert distance_score_miles(1.0) == 100.0
    assert distance_score_miles(2.0) == 100.0
    assert distance_score_miles(20.0) == 0.0
    assert distance_score_miles(11.0) == 50.0


def test_healthcare_defaults_without_hospital():
    assert healthcare_from_nearest(None, None) == DEFAULT_HEALTHCARE_SCORE


def test_healthcare_uses_stars_and_distance():
    # 5 stars → 100 star component; 2 mi → 100 distance → overall 100
    assert healthcare_from_nearest(5.0, 2.0) == 100.0


def test_environment_formula_and_default():
    assert environment_from_aqi(None) == DEFAULT_ENVIRONMENT_SCORE
    assert environment_from_aqi(0) == 100.0
    assert environment_from_aqi(150) == 50.0


def test_weighted_overall_matches_contract_weights():
    # Known mix: 100, 0, 0, 0, 0 → 25.0 (healthcare weight)
    assert weighted_overall(100, 0, 0, 0, 0) == 25.0
