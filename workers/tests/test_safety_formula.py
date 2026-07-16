"""Safety formula from CDE aggregates."""

from ingest.fixtures.constants import SOURCE_DEFAULT, SOURCE_FBI_CDE
from scoring.safety import CountyCrime, safety_from_cde


def test_missing_crime_uses_default():
    result = safety_from_cde(None)
    assert result.score == 50.0
    assert result.provenance["source_id"] == SOURCE_DEFAULT


def test_at_state_benchmark_scores_near_75():
    crime = CountyCrime(
        county_fips="05007",
        by_offense={
            "HOM": (1.0, 1.0),
            "ROB": (2.0, 2.0),
            "ASS": (3.0, 3.0),
        },
        ori_count=2,
    )
    result = safety_from_cde(crime)
    assert result.provenance["source_id"] == SOURCE_FBI_CDE
    assert result.score == 75.0


def test_above_state_benchmark_lowers_score():
    crime = CountyCrime(
        county_fips="17031",
        by_offense={"HOM": (8.0, 1.0), "ROB": (8.0, 1.0), "ASS": (8.0, 1.0)},
        ori_count=3,
    )
    result = safety_from_cde(crime)
    assert result.score < 50.0
    assert result.provenance["source_id"] == SOURCE_FBI_CDE


def test_below_state_benchmark_raises_score():
    crime = CountyCrime(
        county_fips="05007",
        by_offense={"HOM": (0.0, 4.0), "ROB": (0.0, 4.0), "ASS": (0.0, 4.0)},
        ori_count=1,
    )
    result = safety_from_cde(crime)
    assert result.score > 90.0
