"""FBI CDE client retry behavior (no live network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from ingest.fbi import client as cde


def _response(status: int) -> httpx.Response:
    req = httpx.Request("GET", "https://example.test/agency")
    return httpx.Response(status, request=req, json={"agencies": []})


def test_chart_get_retries_on_503_then_succeeds(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FBI_CDE_API_KEY", "test-key")
    monkeypatch.setattr(cde, "_RETRY_BASE_SLEEP_SEC", 0.01)

    calls = {"n": 0}

    def fake_get(url, params=None):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] < 3:
            return _response(503)
        req = httpx.Request("GET", url)
        return httpx.Response(200, request=req, json={"agencies": [{"ori": "X"}]})

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get.side_effect = fake_get

    with patch("ingest.fbi.client.httpx.Client", return_value=mock_client):
        payload = cde._chart_get("/agency/byStateAbbr/IL")

    assert calls["n"] == 3
    assert payload["agencies"][0]["ori"] == "X"


def test_chart_get_gives_up_after_retries(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FBI_CDE_API_KEY", "test-key")
    monkeypatch.setattr(cde, "_RETRY_BASE_SLEEP_SEC", 0.01)
    monkeypatch.setattr(cde, "_RETRY_ATTEMPTS", 2)

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.get.return_value = _response(503)

    with patch("ingest.fbi.client.httpx.Client", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            cde._chart_get("/agency/byStateAbbr/IL")
