"""Open-Meteo client unit tests (httpx mocked)."""

from datetime import date
from unittest.mock import MagicMock, patch

from scoring.open_meteo import fetch_mean_us_aqi


def test_fetch_mean_us_aqi_returns_none_on_http_error():
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("boom")

    with patch("scoring.open_meteo.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        assert fetch_mean_us_aqi(36.37, -94.20, end=date(2026, 5, 30)) is None


def test_fetch_mean_us_aqi_returns_none_on_empty_series():
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"hourly": {"time": [], "us_aqi": []}}

    with patch("scoring.open_meteo.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        assert fetch_mean_us_aqi(36.37, -94.20, end=date(2026, 5, 30)) is None


def test_fetch_mean_us_aqi_averages_daily_maxes():
    # Two hours on day1 (10, 40) → daily max 40; day2 max 20 → mean 30
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "hourly": {
            "time": [
                "2026-05-29T00:00",
                "2026-05-29T12:00",
                "2026-05-30T00:00",
            ],
            "us_aqi": [10, 40, 20],
        }
    }

    with patch("scoring.open_meteo.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.get.return_value = mock_response
        assert fetch_mean_us_aqi(36.37, -94.20, end=date(2026, 5, 30)) == 30.0
