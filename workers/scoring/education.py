"""Education score from NCES access + Urban staffing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    SOURCE_DEFAULT,
    SOURCE_NCES_URBAN,
)

DEFAULT_EDUCATION_SCORE = DEFAULT_ENVIRONMENT_SCORE

ACCESS_WEIGHT = 0.55
STAFFING_WEIGHT = 0.45

# Distance bands for nearest public school (miles).
ACCESS_NEAR_MILES = 0.5
ACCESS_FAR_MILES = 5.0

# Pupil–teacher ratio sweet spot.
PT_RATIO_LOW = 14.0
PT_RATIO_HIGH = 18.0


@dataclass(frozen=True)
class EducationInputs:
    nearest_miles: float | None = None
    locale: str | None = None
    enrollment: int | None = None
    teachers_fte: float | None = None
    ncessch: str | None = None


@dataclass(frozen=True)
class EducationResult:
    score: float
    provenance: dict[str, Any]


def access_score_from_distance(
    miles: float | None,
    locale: str | None = None,
) -> float | None:
    """Closer schools score higher; locale nudges ±3 (not a hard penalty)."""
    if miles is None:
        return None
    if miles <= ACCESS_NEAR_MILES:
        base = 100.0
    elif miles >= ACCESS_FAR_MILES:
        base = 20.0
    else:
        span = ACCESS_FAR_MILES - ACCESS_NEAR_MILES
        base = 100.0 - (miles - ACCESS_NEAR_MILES) * (80.0 / span)

    if locale:
        try:
            locale_code = int(str(locale)[:2])
            if 11 <= locale_code <= 13:
                base = min(100.0, base + 3.0)
            elif locale_code >= 40:
                base = max(0.0, base - 2.0)
        except ValueError:
            pass
    return max(0.0, min(100.0, base))


def staffing_score_from_ratio(
    enrollment: int | None,
    teachers_fte: float | None,
) -> float | None:
    """Moderate pupil–teacher ratios score highest."""
    if enrollment is None or teachers_fte is None or teachers_fte <= 0:
        return None
    ratio = float(enrollment) / float(teachers_fte)
    if PT_RATIO_LOW <= ratio <= PT_RATIO_HIGH:
        return 100.0
    if ratio < PT_RATIO_LOW:
        return max(60.0, 100.0 - (PT_RATIO_LOW - ratio) * 5.0)
    return max(20.0, 100.0 - (ratio - PT_RATIO_HIGH) * 4.0)


def education_from_sources(
    inputs: EducationInputs | None,
    *,
    has_nces_table: bool = True,
    has_urban_table: bool = True,
) -> EducationResult:
    """
    Blend NCES access (~55%) + Urban staffing (~45%).
    Reweight when one component is missing; default 50 when both unavailable.
    """
    if inputs is None:
        inputs = EducationInputs()

    access = access_score_from_distance(inputs.nearest_miles, inputs.locale)
    staffing = staffing_score_from_ratio(inputs.enrollment, inputs.teachers_fte)

    has_nces = has_nces_table and access is not None
    has_urban = has_urban_table and staffing is not None

    contributors: list[str] = []
    if has_nces:
        contributors.append("nces_school_data")
    if has_urban:
        contributors.append("urban_school_data")

    if not has_nces and not has_urban:
        reason = "both_unavailable"
        if not has_nces_table and not has_urban_table:
            reason = "tables_empty"
        elif access is None and staffing is None:
            reason = "no_matching_rows"
        return EducationResult(
            score=DEFAULT_EDUCATION_SCORE,
            provenance={
                "source_id": SOURCE_DEFAULT,
                "reason": reason,
                "contributors": contributors,
            },
        )

    if has_nces and has_urban:
        score = access * ACCESS_WEIGHT + staffing * STAFFING_WEIGHT
        reason = "nces_urban_blend"
    elif has_nces:
        score = access
        reason = "partial_urban"
    else:
        score = staffing
        reason = "partial_nces"

    prov: dict[str, Any] = {
        "source_id": SOURCE_NCES_URBAN,
        "reason": reason,
        "contributors": contributors,
    }
    if inputs.ncessch:
        prov["ncessch"] = inputs.ncessch
    if inputs.nearest_miles is not None:
        prov["nearest_school_miles"] = round(float(inputs.nearest_miles), 2)
    if inputs.enrollment is not None and inputs.teachers_fte:
        prov["pupil_teacher_ratio"] = round(
            float(inputs.enrollment) / float(inputs.teachers_fte),
            1,
        )

    return EducationResult(score=round(score, 1), provenance=prov)
