"""Education score from public-school access (by level), not PTR/locale staffing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    SCHOOL_MAX_EXPAND_MILES,
    SOURCE_DEFAULT,
    SOURCE_NCES_URBAN,
)
from scoring.formulas import distance_score_miles

DEFAULT_EDUCATION_SCORE = DEFAULT_ENVIRONMENT_SCORE

# Legacy helpers retained for unit tests / future zoning-backed staffing.
ACCESS_NEAR_MILES = 0.5
ACCESS_FAR_MILES = 5.0
PT_RATIO_LOW = 14.0
PT_RATIO_HIGH = 18.0


@dataclass(frozen=True)
class EducationInputs:
    nearest_miles: float | None = None
    # Distances for nearest school per level (miles); filtered to SCHOOL_MAX in scorer.
    level_miles: list[float] = field(default_factory=list)
    locale: str | None = None  # unused for category score (expand must not show locale)
    enrollment: int | None = None  # unused while staffing is limited-data
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
    """Closer schools score higher; locale nudges deprecated for category scoring."""
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
    """Moderate pupil–teacher ratios score highest (not used for category until zoning)."""
    if enrollment is None or teachers_fte is None or teachers_fte <= 0:
        return None
    ratio = float(enrollment) / float(teachers_fte)
    if PT_RATIO_LOW <= ratio <= PT_RATIO_HIGH:
        return 100.0
    if ratio < PT_RATIO_LOW:
        return max(60.0, 100.0 - (PT_RATIO_LOW - ratio) * 5.0)
    return max(20.0, 100.0 - (ratio - PT_RATIO_HIGH) * 4.0)


def _in_range_miles(inputs: EducationInputs) -> list[float]:
    """Miles used for Access — same cutoff as expand / detail._access_from_schools."""
    out: list[float] = []
    for raw in inputs.level_miles:
        try:
            m = float(raw)
        except (TypeError, ValueError):
            continue
        if m <= SCHOOL_MAX_EXPAND_MILES:
            out.append(m)
    if out:
        return out
    if (
        inputs.nearest_miles is not None
        and float(inputs.nearest_miles) <= SCHOOL_MAX_EXPAND_MILES
    ):
        return [float(inputs.nearest_miles)]
    return []


def education_from_sources(
    inputs: EducationInputs | None,
    *,
    has_nces_table: bool = True,
    has_urban_table: bool = True,  # kept for call-site compat; staffing not scored
) -> EducationResult:
    """
    Schools category = access proximity only (avg distance_score over in-range levels).

    Staffing / PTR / locale are NOT blended into the published category while
    staffing remains limited-data (research.md §10.5 / FR-007).
    """
    del has_urban_table  # staffing excluded from category score
    if inputs is None:
        inputs = EducationInputs()

    miles_list = _in_range_miles(inputs) if has_nces_table else []
    if not miles_list:
        reason = "tables_empty" if not has_nces_table else "no_in_range_schools"
        return EducationResult(
            score=DEFAULT_EDUCATION_SCORE,
            provenance={
                "source_id": SOURCE_DEFAULT,
                "reason": reason,
                "contributors": [],
            },
        )

    scores = [distance_score_miles(m) for m in miles_list]
    access = sum(scores) / len(scores)
    prov: dict[str, Any] = {
        "source_id": SOURCE_NCES_URBAN,
        "reason": "access_by_level",
        "contributors": ["nces_school_data"],
        "levels_in_range": len(miles_list),
        "mean_miles": round(sum(miles_list) / len(miles_list), 2),
    }
    if inputs.ncessch:
        prov["ncessch"] = inputs.ncessch
    return EducationResult(score=round(access, 1), provenance=prov)
