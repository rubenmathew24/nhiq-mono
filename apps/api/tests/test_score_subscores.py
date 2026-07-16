"""API report includes sub_scores from score_detail."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data.mock_report import build_mock_report
from app.db.session import get_db
from app.schemas.score import SubScore
from app.services.score_service import build_report_from_scores
from main import app


async def _fake_db():
    yield MagicMock()


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def test_demo_report_has_sub_scores(client):
    resp = client.get("/api/v1/score/demo-address-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["healthcare"]["sub_scores"]
    assert body["healthcare"]["sub_scores"][0]["id"] == "access"
    assert body["healthcare"]["factors"]


@pytest.mark.asyncio
async def test_build_report_maps_score_detail():
    lookup = {
        "address_raw": "1 Main",
        "address_normalized": "1 Main, Bentonville, AR",
        "latitude": 36.3,
        "longitude": -94.2,
        "geoid": "05007020101",
    }
    session = MagicMock()

    async def fake_fetch(_session, geoid, vintage=None):
        return {
            "geoid": geoid,
            "healthcare_score": 80,
            "safety_score": 70,
            "environment_score": 75,
            "education_score": 85,
            "economic_score": 65,
            "overall_score": 75,
            "data_vintage": "2026-Q3",
            "computed_at": datetime.now(timezone.utc),
            "score_sources": {"environment": {"source_id": "epa_aqs", "reason": "primary"}},
            "score_detail": {
                "healthcare": {
                    "sub_scores": [
                        {"id": "access", "label": "Access", "score": 90, "available": True}
                    ],
                    "stats": [
                        {"name": "Nearest ER", "value": "Mercy · 2.0 mi · ★4", "impact": "positive"}
                    ],
                },
                "safety": {"sub_scores": [], "stats": []},
                "education": {"sub_scores": [], "stats": []},
                "environment": {"sub_scores": [], "stats": []},
                "economic": {"sub_scores": [], "stats": []},
            },
        }

    with patch(
        "app.services.score_service.fetch_score_row",
        new=AsyncMock(side_effect=fake_fetch),
    ):
        report = await build_report_from_scores(session, lookup)

    assert report.healthcare.sub_scores[0].id == "access"
    assert report.healthcare.factors[0].name == "Nearest ER"
    assert isinstance(report.healthcare.sub_scores[0], SubScore)


def test_mock_report_shape():
    r = build_mock_report(
        address_raw="a",
        address_normalized="a",
        latitude=1.0,
        longitude=2.0,
        geoid="05007020101",
    )
    assert len(r.healthcare.sub_scores) >= 2
