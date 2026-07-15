"""Economic formula from ACS income + BLS LAUS unemployment."""

from ingest.fixtures.constants import SOURCE_ACS_BLS, SOURCE_DEFAULT
from scoring.economic import (
    EconomicInputs,
    economic_from_sources,
    income_score_from_median,
    unemployment_score_from_rate,
)


def test_income_score_interpolates_breakpoints():
    assert income_score_from_median(50_000) == 50.0
    assert income_score_from_median(75_000) == 65.0
    assert income_score_from_median(250_000) == 100.0


def test_unemployment_score_lower_is_better():
    assert unemployment_score_from_rate(2.0) == 95.0
    assert unemployment_score_from_rate(10.0) < unemployment_score_from_rate(4.0)


def test_dual_source_blend_uses_acs_bls_provenance():
    result = economic_from_sources(
        EconomicInputs(
            median_hh_income=85_000,
            unemployment_rate=3.5,
            acs_year="2022",
            laus_period="2025-M12",
        )
    )
    assert result.provenance["source_id"] == SOURCE_ACS_BLS
    assert result.provenance["reason"] == "acs_bls_blend"
    assert "census_acs" in result.provenance["contributors"]
    assert "bls_laus" in result.provenance["contributors"]
    assert 50.0 < result.score < 100.0


def test_partial_acs_when_bls_missing():
    result = economic_from_sources(
        EconomicInputs(median_hh_income=60_000, acs_year="2022"),
        has_bls_table=False,
    )
    assert result.provenance["source_id"] == SOURCE_ACS_BLS
    assert result.provenance["reason"] == "partial_bls"


def test_both_missing_defaults_to_50():
    result = economic_from_sources(EconomicInputs(), has_acs_table=False, has_bls_table=False)
    assert result.score == 50.0
    assert result.provenance["source_id"] == SOURCE_DEFAULT
