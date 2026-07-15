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
    """Personal-crime weighted totals for local vs state (HOM>ROB>ASS)."""
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
    if not saw and local == 0.0 and not crime.by_offense:
        return None
    # If we have local but no state, treat state as local (neutral ratio 1.0)
    if not saw:
        state = local if local > 0 else 1.0
    return local, max(state, 1e-6)


def safety_from_cde(crime: CountyCrime | None) -> SafetyResult:
    """
    Map local/state personal-crime intensity ratio to 0–100.
    ratio ≈ 1 → ~75; below state → higher; above state → lower.
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
        return SafetyResult(
            score=DEFAULT_SAFETY_SCORE,
            provenance={
                "source_id": SOURCE_DEFAULT,
                "reason": "cde_empty",
                "ori_count": crime.ori_count,
            },
        )

    local, state = pair
    ratio = local / state
    # ratio 0 → 100; ratio 1 → 75; ratio 2 → 50; ratio ≥4 → 0
    score = max(0.0, min(100.0, 100.0 - 25.0 * ratio))
    return SafetyResult(
        score=round(score, 1),
        provenance={
            "source_id": SOURCE_FBI_CDE,
            "reason": "agency_aggregate",
            "ori_count": crime.ori_count,
            "local_weighted": round(local, 2),
            "state_weighted": round(state, 2),
            "ratio": round(ratio, 3),
        },
    )
