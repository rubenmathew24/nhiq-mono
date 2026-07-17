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
                        {
                            "name": "Nearest ER",
                            "value": "Mercy · 2.0 mi · ★4",
                            "impact": "positive",
                            "tone_score": 85,
                        },
                        {
                            "name": "2nd nearest ER",
                            "value": "Other · 4.0 mi · ★3",
                            "impact": "neutral",
                            "tone_score": 55,
                        },
                        {
                            "name": "ER wait",
                            "value": "162 min (national 161)",
                            "impact": "negative",
                            "tone_score": 49,
                        },
                    ],
                },
                "safety": {
                    "sub_scores": [
                        {
                            "id": "personal",
                            "label": "Crimes against people",
                            "score": 91.0,
                            "available": True,
                        },
                        {
                            "id": "property",
                            "label": "Crimes against property",
                            "score": 0.0,
                            "available": False,
                        },
                    ],
                    "stats": [
                        {
                            "name": "Violent crime vs state",
                            "value": "Violent crime about 12% lower than the state average (per resident)",
                            "impact": "positive",
                            "tone_score": 78,
                        },
                        {"name": "Assault", "value": "20 incidents (12 mo)", "impact": "neutral"},
                    ],
                },
                "education": {
                    "sub_scores": [],
                    "stats": [
                        {
                            "name": "Nearest Pre-K",
                            "value": "No schools found within 30 mi",
                            "impact": "neutral",
                        }
                    ],
                },
                "environment": {
                    "sub_scores": [],
                    "stats": [
                        {"name": "Average AQI", "value": "57 · Moderate", "impact": "neutral"}
                    ],
                },
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
    assert report.healthcare.factors[1].name == "2nd nearest ER"
    assert report.healthcare.factors[2].tone_score == 49
    assert isinstance(report.healthcare.sub_scores[0], SubScore)
    joined = " ".join(f"{f.name} {f.value}" for f in report.healthcare.factors)
    assert "Also nearby" not in joined
    assert "★" in report.healthcare.factors[0].value
    assert "ASS" not in " ".join(f.name for f in report.safety.factors)
    safety_joined = " ".join(f.value for f in report.safety.factors)
    assert "per resident" in safety_joined
    assert "0.03×" not in safety_joined
    prop = next(s for s in report.safety.sub_scores if s.id == "property")
    assert prop.available is False
    edu_joined = " ".join(f.value for f in report.education.factors)
    assert "457" not in edu_joined
    assert "30 mi" in edu_joined or "No schools found" in edu_joined
    assert "open_meteo" not in report.environment.factors[0].value


def test_mock_report_shape():
    r = build_mock_report(
        address_raw="a",
        address_normalized="a",
        latitude=1.0,
        longitude=2.0,
        geoid="05007020101",
    )
    assert len(r.healthcare.sub_scores) >= 2
    assert r.healthcare.factors[0].tone_score is not None
    assert r.education.sub_scores[-1].available is False
    assert any(f.name == "Share of labor force employed" for f in r.economic.factors)
