"""Safety formula from CDE aggregates (per-resident intensity)."""

from ingest.fixtures.constants import SOURCE_DEFAULT, SOURCE_FBI_CDE
from scoring.safety import CountyCrime, safety_from_cde

# Equal per-resident rates: local=10, county=100k, state=100, state_pop=1M → ratio 1
POP_COUNTY = 100_000.0
POP_STATE = 1_000_000.0


def test_missing_crime_uses_default():
    result = safety_from_cde(None, county_pop=POP_COUNTY, state_pop=POP_STATE)
    assert result.score == 50.0
    assert result.provenance["source_id"] == SOURCE_DEFAULT


def test_missing_population_uses_default_not_absolute_share():
    crime = CountyCrime(
        county_fips="05007",
        by_offense={"HOM": (1.0, 100.0), "ROB": (2.0, 200.0), "ASS": (3.0, 300.0)},
        ori_count=2,
    )
    result = safety_from_cde(crime, county_pop=None, state_pop=POP_STATE)
    assert result.score == 50.0
    assert result.provenance["source_id"] == SOURCE_DEFAULT
    assert result.provenance["reason"] == "population_unavailable"
    assert "ratio" not in result.provenance


def test_at_state_per_resident_benchmark_scores_near_75():
    # Weighted local = 3*1+2*2+2*3 = 13; state = 130 → rates equal when pops 100k / 1M
    crime = CountyCrime(
        county_fips="05007",
        by_offense={
            "HOM": (1.0, 10.0),
            "ROB": (2.0, 20.0),
            "ASS": (3.0, 30.0),
        },
        ori_count=2,
    )
    result = safety_from_cde(crime, county_pop=POP_COUNTY, state_pop=POP_STATE)
    assert result.provenance["source_id"] == SOURCE_FBI_CDE
    assert result.score == 75.0
    assert abs(result.provenance["ratio"] - 1.0) < 0.01


def test_higher_local_rate_lowers_score():
    crime = CountyCrime(
        county_fips="17031",
        by_offense={"HOM": (8.0, 1.0), "ROB": (8.0, 1.0), "ASS": (8.0, 1.0)},
        ori_count=3,
    )
    result = safety_from_cde(crime, county_pop=POP_COUNTY, state_pop=POP_STATE)
    assert result.score < 50.0
    assert result.provenance["source_id"] == SOURCE_FBI_CDE
    assert result.provenance["ratio"] > 1.0


def test_lower_local_rate_raises_score():
    crime = CountyCrime(
        county_fips="05007",
        by_offense={"HOM": (0.0, 40.0), "ROB": (0.0, 40.0), "ASS": (0.0, 40.0)},
        ori_count=1,
    )
    result = safety_from_cde(crime, county_pop=POP_COUNTY, state_pop=POP_STATE)
    assert result.score > 90.0


def test_personal_without_benches_is_unavailable_not_synthesized():
    """Null personal benches + pop must not invent a scored FBI result."""
    crime = CountyCrime(
        county_fips="05007",
        by_offense={
            "HOM": (4.0, None),
            "ROB": (37.0, None),
            "ASS": (599.0, None),
        },
        ori_count=4,
    )
    result = safety_from_cde(crime, county_pop=286528.0, state_pop=3018669.0)
    assert result.provenance["source_id"] == SOURCE_DEFAULT
    assert result.provenance["reason"] == "state_benches_unavailable"
    assert "ratio" not in result.provenance
