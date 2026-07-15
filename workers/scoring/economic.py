"""Economic score from ACS income + BLS LAUS unemployment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    SOURCE_ACS_BLS,
    SOURCE_DEFAULT,
)

DEFAULT_ECONOMIC_SCORE = DEFAULT_ENVIRONMENT_SCORE

INCOME_WEIGHT = 0.60
LABOR_WEIGHT = 0.40

# Median household income breakpoints (USD).
INCOME_BREAKPOINTS: tuple[tuple[float, float], ...] = (
    (25_000, 25.0),
    (50_000, 50.0),
    (75_000, 65.0),
    (100_000, 75.0),
    (150_000, 90.0),
    (200_000, 100.0),
)


@dataclass(frozen=True)
class EconomicInputs:
    median_hh_income: float | None = None
    unemployment_rate: float | None = None
    acs_year: str | None = None
    laus_period: str | None = None


@dataclass(frozen=True)
class EconomicResult:
    score: float
    provenance: dict[str, Any]


def income_score_from_median(median_income: float | None) -> float | None:
    """Map ACS median HH income to 0–100 using documented breakpoints."""
    if median_income is None or median_income <= 0:
        return None
    income = float(median_income)
    if income <= INCOME_BREAKPOINTS[0][0]:
        return INCOME_BREAKPOINTS[0][1]
    for (low, low_score), (high, high_score) in zip(
        INCOME_BREAKPOINTS,
        INCOME_BREAKPOINTS[1:],
    ):
        if income <= high:
            span = high - low
            if span <= 0:
                return high_score
            frac = (income - low) / span
            return low_score + frac * (high_score - low_score)
    return 100.0


def unemployment_score_from_rate(rate: float | None) -> float | None:
    """Lower county unemployment → higher score."""
    if rate is None:
        return None
    # 2% ≈ 95, each +1% unemployment ≈ −8 points.
    return max(0.0, min(100.0, 95.0 - (float(rate) - 2.0) * 8.0))


def economic_from_sources(
    inputs: EconomicInputs | None,
    *,
    has_acs_table: bool = True,
    has_bls_table: bool = True,
) -> EconomicResult:
    """
    Blend ACS income (~60%) + LAUS unemployment (~40%).
    County LAUS applies to all tracts in the county.
    """
    if inputs is None:
        inputs = EconomicInputs()

    income = income_score_from_median(inputs.median_hh_income)
    labor = unemployment_score_from_rate(inputs.unemployment_rate)

    has_acs = has_acs_table and income is not None
    has_bls = has_bls_table and labor is not None

    contributors: list[str] = []
    if has_acs:
        contributors.append("census_acs")
    if has_bls:
        contributors.append("bls_laus")

    if not has_acs and not has_bls:
        reason = "both_unavailable"
        if not has_acs_table and not has_bls_table:
            reason = "tables_empty"
        elif income is None and labor is None:
            reason = "no_matching_rows"
        return EconomicResult(
            score=DEFAULT_ECONOMIC_SCORE,
            provenance={
                "source_id": SOURCE_DEFAULT,
                "reason": reason,
                "contributors": contributors,
            },
        )

    if has_acs and has_bls:
        score = income * INCOME_WEIGHT + labor * LABOR_WEIGHT
        reason = "acs_bls_blend"
    elif has_acs:
        score = income
        reason = "partial_bls"
    else:
        score = labor
        reason = "partial_acs"

    prov: dict[str, Any] = {
        "source_id": SOURCE_ACS_BLS,
        "reason": reason,
        "contributors": contributors,
    }
    if inputs.median_hh_income is not None:
        prov["median_hh_income"] = round(float(inputs.median_hh_income), 0)
    if inputs.unemployment_rate is not None:
        prov["unemployment_rate"] = round(float(inputs.unemployment_rate), 2)
    if inputs.acs_year:
        prov["acs_year"] = inputs.acs_year
    if inputs.laus_period:
        prov["laus_period"] = inputs.laus_period

    return EconomicResult(score=round(score, 1), provenance=prov)
