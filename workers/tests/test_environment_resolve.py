"""EPA primary / Open-Meteo fallback resolution."""

from datetime import date

from ingest.fixtures.constants import (
    DEFAULT_ENVIRONMENT_SCORE,
    SOURCE_DEFAULT,
    SOURCE_EPA_AQS,
    SOURCE_OPEN_METEO,
)
from scoring.environment import EpaCountyAqi, resolve_environment


def _epa(days: int, avg: float = 45.0) -> EpaCountyAqi:
    return EpaCountyAqi(
        county_fips="05007",
        avg_aqi=avg,
        distinct_days=days,
        min_date=date(2026, 5, 1),
        max_date=date(2026, 5, 30),
    )


def test_uses_epa_when_worthy():
    result = resolve_environment(epa=_epa(10), open_meteo_avg=99.0)
    assert result.provenance["source_id"] == SOURCE_EPA_AQS
    assert result.provenance["reason"] == "primary"
    # avg 45 → score max(0, 100 - 45/3) = 85.0
    assert result.score == 85.0


def test_falls_back_to_open_meteo_when_sparse_epa():
    result = resolve_environment(epa=_epa(2), open_meteo_avg=60.0)
    assert result.provenance["source_id"] == SOURCE_OPEN_METEO
    assert result.provenance["reason"] == "fallback_sparse_epa"
    assert result.score == 80.0  # 100 - 60/3


def test_falls_back_when_no_epa():
    result = resolve_environment(epa=None, open_meteo_avg=30.0)
    assert result.provenance["source_id"] == SOURCE_OPEN_METEO
    assert result.provenance["reason"] == "fallback_no_epa"


def test_default_when_both_missing():
    result = resolve_environment(epa=None, open_meteo_avg=None)
    assert result.score == DEFAULT_ENVIRONMENT_SCORE
    assert result.provenance["source_id"] == SOURCE_DEFAULT
