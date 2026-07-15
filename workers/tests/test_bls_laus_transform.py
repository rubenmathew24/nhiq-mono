"""Tests for BLS LAUS transform helpers."""

from ingest.bls.client import laus_series_id
from ingest.bls.transform import pick_latest_observation, transform_laus_series


def test_laus_series_id_format():
    assert laus_series_id("05007") == "LAUCN050070000000003"
    assert laus_series_id("17031") == "LAUCN170310000000003"


def test_pick_latest_observation_prefers_newest_month():
    obs = [
        {"year": "2024", "period": "M10", "value": "4.0"},
        {"year": "2025", "period": "M02", "value": "3.5"},
        {"year": "2025", "period": "M12", "value": "3.1"},
    ]
    latest = pick_latest_observation(obs)
    assert latest["period"] == "M12"
    assert latest["year"] == "2025"


def test_transform_laus_series_maps_latest_rate():
    row = transform_laus_series(
        "05007",
        "LAUCN050070000000003",
        [{"year": "2025", "period": "M12", "value": "3.1"}],
    )
    assert row is not None
    assert row["county_fips"] == "05007"
    assert row["unemployment_rate"] == 3.1
    assert row["period"] == "2025-M12"
