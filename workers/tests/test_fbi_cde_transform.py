"""FBI CDE transform + agency select unit tests (no live API)."""

from ingest.fbi.client import haversine_miles, select_nearest_agencies, sum_last_n_month_counts
from ingest.fbi.transform import agencies_to_rows, offense_aggregate_row


def test_haversine_zero_for_same_point():
    assert haversine_miles(36.37, -94.20, 36.37, -94.20) == 0.0


def test_select_nearest_agencies_respects_distance_and_denylist():
    agencies = [
        {
            "ori": "AR0040100",
            "agency_name": "Bentonville Police Department",
            "latitude": 36.37,
            "longitude": -94.21,
            "_cde_county_bucket": "BENTON",
        },
        {
            "ori": "AR9999999",
            "agency_name": "University Campus Police",
            "latitude": 36.37,
            "longitude": -94.21,
        },
        {
            "ori": "AR0000001",
            "agency_name": "Far Away PD",
            "latitude": 35.0,
            "longitude": -92.0,
        },
    ]
    picked = select_nearest_agencies(
        agencies,
        lat=36.3729,
        lon=-94.2088,
        county_name="Benton",
        max_miles=15.0,
        limit=5,
    )
    oris = {a["ori"] for a in picked}
    assert "AR0040100" in oris
    assert "AR9999999" not in oris  # denylist
    assert "AR0000001" not in oris  # too far


def test_agencies_to_rows_marks_primary():
    rows = agencies_to_rows(
        county_fips="05007",
        state_abbr="AR",
        agencies=[
            {"ori": "A", "agency_name": "One", "distance_miles": 1.0},
            {"ori": "B", "agency_name": "Two", "distance_miles": 2.0},
        ],
        data_vintage="2026-Q3",
    )
    assert rows[0]["is_primary_hint"] is True
    assert rows[1]["is_primary_hint"] is False


def test_offense_aggregate_row_uses_empty_ori_sentinel():
    row = offense_aggregate_row(
        county_fips="05007",
        offense_slug="hom",
        incidents_12mo=3.0,
        state_benchmark_12mo=10.0,
        data_vintage="2026-Q3",
    )
    assert row["ori"] == ""
    assert row["offense_slug"] == "HOM"


def test_sum_last_n_month_counts_from_chart_shape():
    chart = {
        "offenses": {
            "actuals": {
                "Agency Actual": {
                    "01-2024": 1,
                    "02-2024": 2,
                    "03-2024": 3,
                }
            }
        }
    }
    assert sum_last_n_month_counts(chart, n=2) == 5.0
