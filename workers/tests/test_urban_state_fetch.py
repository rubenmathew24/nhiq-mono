"""Urban per-state fips fetch unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ingest.urban.client import fetch_directory_for_states


def test_fetch_directory_for_states_passes_fips_param():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "count": 1,
        "results": [{"ncessch": "440000000001", "leaid": "440001"}],
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("ingest.urban.client.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None
        client.get.return_value = mock_resp
        client_cls.return_value = client

        rows = fetch_directory_for_states(["44", "09"], year=2022)

    assert len(rows) == 1
    _, kwargs = client.get.call_args
    assert kwargs["params"]["fips"] == "44,09"
    assert kwargs["params"]["page"] == 1
