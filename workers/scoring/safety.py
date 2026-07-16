"""Safety score from FBI CDE county offense aggregates vs state benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    FBI_CDE_PERSONAL_OFFENSES,
    SOURCE_DEFAULT,
    SOURCE_FBI_CDE,
)

# Reuse same numeric default pattern as other missing-inputs paths.
DEFAULT_SAFETY_SCORE = DEFAULT_ENVIRONMENT_SCORE


@dataclass(frozen=True)
class CountyCrime:
    county_fips: str
    # offense_slug -> (incidents_12mo, state_benchmark_12mo)
    by_offense: dict[str, tuple[float, float | None]]
    ori_count: int = 0


@dataclass(frozen=True)
class SafetyResult:
    score: float
    provenance: dict[str, Any]


def _weighted_local_state(crime: CountyCrime) -> tuple[float, float] | None:
    """Personal-crime weighted totals for local vs state (HOM>ROB>ASS).

    Requires at least one real state benchmark. Never synthesize
    ``state = local`` — under population normalization that invents a
    false intensity ratio (same failure mode as property FR-021).
    """
    weights = {"HOM": 3.0, "ROB": 2.0, "ASS": 2.0}
    local = 0.0
    state = 0.0
    saw = False
    for slug in FBI_CDE_PERSONAL_OFFENSES:
        pair = crime.by_offense.get(slug)
        if not pair:
            continue
        incidents, bench = pair
        w = weights.get(slug, 1.0)
        local += w * float(incidents or 0.0)
        if bench is not None:
            state += w * float(bench)
            saw = True
    if not saw:
        return None
    return local, max(state, 1e-6)


def safety_from_cde(
    crime: CountyCrime | None,
    *,
    county_pop: float | None = None,
    state_pop: float | None = None,
) -> SafetyResult:
    """
    Map local/state personal-crime intensity (per resident) to 0–100.

    intensity_ratio = (local/county_pop) / (state/state_pop)
    ratio ≈ 1 → ~75; below state → higher; above state → lower.

    Missing population → default/unavailable (no absolute-share fallback).
    """
    if crime is None or not crime.by_offense:
        return SafetyResult(
            score=DEFAULT_SAFETY_SCORE,
            provenance={
                "source_id": SOURCE_DEFAULT,
                "reason": "cde_unavailable",
            },
        )

    pair = _weighted_local_state(crime)
    if pair is None:
        has_personal = any(
            slug in crime.by_offense for slug in FBI_CDE_PERSONAL_OFFENSES
        )
        reason = (
            "state_benches_unavailable" if has_personal else "cde_empty"
        )
        return SafetyResult(
            score=DEFAULT_SAFETY_SCORE,
            provenance={
                "source_id": SOURCE_DEFAULT,
                "reason": reason,
                "ori_count": crime.ori_count,
            },
        )

    if (
        county_pop is None
        or state_pop is None
        or float(county_pop) <= 0
        or float(state_pop) <= 0
    ):
        return SafetyResult(
            score=DEFAULT_SAFETY_SCORE,
            provenance={
                "source_id": SOURCE_DEFAULT,
                "reason": "population_unavailable",
                "ori_count": crime.ori_count,
            },
        )

    local, state = pair
    c_pop = float(county_pop)
    s_pop = float(state_pop)
    local_rate = local / c_pop
    state_rate = state / s_pop
    if state_rate <= 0:
        return SafetyResult(
            score=DEFAULT_SAFETY_SCORE,
            provenance={
                "source_id": SOURCE_DEFAULT,
                "reason": "state_rate_zero",
                "ori_count": crime.ori_count,
            },
        )

    ratio = local_rate / state_rate
    # ratio 0 → 100; ratio 1 → 75; ratio 2 → 50; ratio ≥4 → 0
    score = max(0.0, min(100.0, 100.0 - 25.0 * ratio))
    return SafetyResult(
        score=round(score, 1),
        provenance={
            "source_id": SOURCE_FBI_CDE,
            "reason": "agency_aggregate_per_resident",
            "ori_count": crime.ori_count,
            "local_weighted": round(local, 2),
            "state_weighted": round(state, 2),
            "county_pop": round(c_pop, 1),
            "state_pop": round(s_pop, 1),
            "local_rate_per_100k": round(local_rate * 100_000.0, 3),
            "state_rate_per_100k": round(state_rate * 100_000.0, 3),
            "ratio": round(ratio, 3),
        },
    )
