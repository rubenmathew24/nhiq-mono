"""EPA AirData bulk returns window rows + monitor-county catalog."""

from __future__ import annotations

import io
import zipfile
from datetime import date
from unittest.mock import MagicMock, patch

from ingest.epa.client import fetch_daily_aqi_bulk


def _zip_bytes(csv_name: str, csv_text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(csv_name, csv_text)
    return buf.getvalue()


def test_bulk_returns_monitor_counties_in_window():
    csv_text = (
        "State Code,County Code,Parameter Code,Date Local,AQI,Parameter Name,"
        "Category,State Name,County Name\n"
        "05,007,44201,2026-06-01,42,Ozone,Good,Arkansas,Benton\n"
        "05,007,44201,2026-01-01,10,Ozone,Good,Arkansas,Benton\n"
        "06,001,44201,2026-06-02,55,Ozone,Moderate,California,Alameda\n"
    )
    payload = _zip_bytes("daily.csv", csv_text)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = payload
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get.return_value = mock_resp

    with patch("ingest.epa.client.httpx.Client", return_value=mock_client):
        with patch("ingest.epa.client._param_codes", return_value=["44201"]):
            rows, monitors = fetch_daily_aqi_bulk(
                date(2026, 6, 1), date(2026, 6, 30)
            )

    assert monitors == {"05007", "06001"}
    assert len(rows) == 2  # Jan row outside window
    assert {f"{r['state_code']}{r['county_code']}" for r in rows} == {
        "05007",
        "06001",
    }
