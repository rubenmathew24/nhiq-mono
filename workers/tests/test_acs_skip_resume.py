"""Resume/skip-done regression: ACS pending-state filter keeps skip-done."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ingest.acs.run import AcsTractWorker


def test_acs_fetch_filters_to_pending_counties_only(monkeypatch):
    monkeypatch.setenv("INGEST_FORCE", "0")
    worker = AcsTractWorker()
    worker.database_url = "postgresql://test"
    worker.logger = MagicMock()

    tabular = [
        ["NAME", "state", "county", "tract", "B01003_001E"],
        ["A", "44", "007", "000100", "100"],
        ["B", "44", "001", "000200", "200"],
    ]

    with patch(
        "ingest.acs.run.active_county_fips",
        return_value=frozenset({"44007", "44001"}),
    ):
        with patch(
            "ingest.acs.run.counties_with_acs", return_value={"44001"}
        ):
            with patch(
                "ingest.acs.run.fetch_state_tract_rows", return_value=tabular
            ) as fetch_state:
                with patch(
                    "ingest.acs.run.fetch_state_rows", return_value=[]
                ):
                    with patch("ingest.acs.run.StatusPulse") as pulse_cls:
                        pulse_cls.return_value = MagicMock()
                        worker.fetch()

    fetch_state.assert_called_once()
    counties = {f"{r['state']}{r['county']}" for r in worker._raw_rows}
    assert counties == {"44007"}
