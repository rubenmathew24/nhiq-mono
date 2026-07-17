"""API assertions for hazard/wait tone in score_detail factors."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.score_service import build_report_from_scores


@pytest.mark.asyncio
async def test_wait_tone_score_and_hazard_unavailable():
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
            "healthcare_score": 70,
            "safety_score": 70,
            "environment_score": 75,
            "education_score": 80,
            "economic_score": 65,
            "overall_score": 72,
            "data_vintage": "2026-Q3",
            "computed_at": datetime.now(timezone.utc),
            "score_sources": {},
            "score_detail": {
                "healthcare": {
                    "sub_scores": [
                        {
                            "id": "timeliness",
                            "label": "Timeliness",
                            "score": 49.0,
                            "available": True,
                        }
                    ],
                    "stats": [
                        {
                            "name": "ER wait",
                            "value": "162 min (state 120 · national 161)",
                            "impact": "negative",
                            "tone_score": 49.0,
                        }
                    ],
                },
                "environment": {
                    "sub_scores": [
                        {
                            "id": "hazard",
                            "label": "Hazard risk",
                            "score": 0.0,
                            "available": False,
                        }
                    ],
                    "stats": [
                        {"name": "Hazard risk", "value": "Unavailable", "impact": "neutral"}
                    ],
                },
                "safety": {"sub_scores": [], "stats": []},
                "education": {"sub_scores": [], "stats": []},
                "economic": {"sub_scores": [], "stats": []},
            },
        }

    with patch(
        "app.services.score_service.fetch_score_row",
        new=AsyncMock(side_effect=fake_fetch),
    ):
        report = await build_report_from_scores(session, lookup)

    wait = report.healthcare.factors[0]
    assert wait.tone_score is not None and wait.tone_score < 75
    assert report.environment.factors[0].value == "Unavailable"
