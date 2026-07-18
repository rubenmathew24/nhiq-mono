"""ACS per-state wildcard fetch unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ingest.acs.client import fetch_state_tract_rows


def test_fetch_state_tract_rows_uses_county_star():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        ["NAME", "state", "county", "tract"],
        ["Tract 1", "44", "007", "000100"],
    ]
    mock_resp.raise_for_status = MagicMock()

    with patch("ingest.acs.client.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None
        client.get.return_value = mock_resp
        client_cls.return_value = client

        rows = fetch_state_tract_rows("44", acs_year=2022)

    assert len(rows) == 2
    _, kwargs = client.get.call_args
    assert kwargs["params"]["in"] == "state:44 county:*"
    assert kwargs["params"]["for"] == "tract:*"
