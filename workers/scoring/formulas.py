"""Pure scoring formulas (no DB imports — safe for unit tests)."""

from __future__ import annotations

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    DEFAULT_HEALTHCARE_SCORE,
    HOSPITAL_FAR_MILES,
    HOSPITAL_NEAR_MILES,
    SCORE_WEIGHTS,
)


def distance_score_miles(nearest_miles: float) -> float:
    """≤ near → 100, ≥ far → 0, linear between."""
    if nearest_miles <= HOSPITAL_NEAR_MILES:
        return 100.0
    if nearest_miles >= HOSPITAL_FAR_MILES:
        return 0.0
    span = HOSPITAL_FAR_MILES - HOSPITAL_NEAR_MILES
    return max(0.0, 100.0 - (nearest_miles - HOSPITAL_NEAR_MILES) * (100.0 / span))


def healthcare_from_nearest(
    avg_stars: float | None,
    nearest_miles: float | None,
) -> float:
    """Blend star rating (60%) and distance decay (40%); default if no ER."""
    if nearest_miles is None:
        return DEFAULT_HEALTHCARE_SCORE
    stars = avg_stars if avg_stars is not None else 3.0
    star_score = (stars - 1.0) / 4.0 * 100.0
    dist_score = distance_score_miles(float(nearest_miles))
    return round(star_score * 0.6 + dist_score * 0.4, 1)


def environment_from_aqi(avg_aqi: float | None) -> float:
    """Higher score = better air. Missing AQI → documented default."""
    if avg_aqi is None:
        return DEFAULT_ENVIRONMENT_SCORE
    return round(max(0.0, 100.0 - (float(avg_aqi) / 3.0)), 1)


def weighted_overall(
    healthcare: float,
    safety: float,
    education: float,
    environment: float,
    economic: float,
) -> float:
    return round(
        healthcare * SCORE_WEIGHTS["healthcare"]
        + safety * SCORE_WEIGHTS["safety"]
        + education * SCORE_WEIGHTS["education"]
        + environment * SCORE_WEIGHTS["environment"]
        + economic * SCORE_WEIGHTS["economic"],
        1,
    )
