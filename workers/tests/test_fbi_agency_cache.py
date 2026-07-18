"""FBI agency-list cache unit tests."""

from __future__ import annotations

from unittest.mock import patch

import ingest.fbi.client as cde


def test_fetch_agencies_by_state_caches_per_state():
    cde.clear_agency_cache()
    agencies = [
        {
            "ori": "RI00100",
            "agency_name": "Test PD",
            "latitude": 41.8,
            "longitude": -71.4,
        }
    ]

    with patch.object(cde, "_chart_get", return_value={"RI": agencies}) as chart_get:
        with patch.object(cde, "_extract_agencies", return_value=agencies):
            with patch.object(
                cde, "_agency_lat_lon", return_value=(41.8, -71.4)
            ):
                with patch.object(cde, "pause_between_requests"):
                    a1 = cde.fetch_agencies_by_state("RI")
                    a2 = cde.fetch_agencies_by_state("ri")

    assert a1 == a2
    assert chart_get.call_count == 1
