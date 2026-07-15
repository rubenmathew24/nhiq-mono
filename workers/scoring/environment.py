"""Environment score resolution: EPA primary, Open-Meteo fallback, provenance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    EPA_MIN_DISTINCT_DAYS,
    SOURCE_DEFAULT,
    SOURCE_EPA_AQS,
    SOURCE_OPEN_METEO,
)
from scoring.formulas import environment_from_aqi


@dataclass(frozen=True)
class EpaCountyAqi:
    county_fips: str
    avg_aqi: float
    distinct_days: int
    min_date: date
    max_date: date

    @property
    def is_worthy(self) -> bool:
        """Enough distinct monitor-days in the scoring window."""
        return self.distinct_days >= EPA_MIN_DISTINCT_DAYS


@dataclass(frozen=True)
class EnvironmentResult:
    score: float
    provenance: dict[str, Any]


def resolve_environment(
    *,
    epa: EpaCountyAqi | None,
    open_meteo_avg: float | None,
) -> EnvironmentResult:
    """
    Primary: EPA AQS county average when worthy.
    Fallback: Open-Meteo modeled US AQI when EPA missing/sparse.
    Last resort: documented default score.
    """
    if epa is not None and epa.is_worthy:
        score = environment_from_aqi(epa.avg_aqi)
        return EnvironmentResult(
            score=score,
            provenance={
                "source_id": SOURCE_EPA_AQS,
                "reason": "primary",
                "avg_aqi": round(epa.avg_aqi, 2),
                "distinct_days": epa.distinct_days,
                "window_min": epa.min_date.isoformat(),
                "window_max": epa.max_date.isoformat(),
            },
        )

    if epa is not None and not epa.is_worthy:
        reason = "fallback_sparse_epa"
    elif epa is None:
        reason = "fallback_no_epa"
    else:
        reason = "fallback_no_epa"

    if open_meteo_avg is not None:
        score = environment_from_aqi(open_meteo_avg)
        return EnvironmentResult(
            score=score,
            provenance={
                "source_id": SOURCE_OPEN_METEO,
                "reason": reason,
                "avg_aqi": round(open_meteo_avg, 2),
                "epa_distinct_days": epa.distinct_days if epa else 0,
            },
        )

    return EnvironmentResult(
        score=DEFAULT_ENVIRONMENT_SCORE,
        provenance={
            "source_id": SOURCE_DEFAULT,
            "reason": "both_unavailable",
            "epa_distinct_days": epa.distinct_days if epa else 0,
            "score": DEFAULT_ENVIRONMENT_SCORE,
        },
    )
