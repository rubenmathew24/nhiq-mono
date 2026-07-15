"""Live score path vs SCORE_UNAVAILABLE (mocked score_service / cache)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.data.mock_report import build_mock_report
from app.db.session import get_db
from app.schemas.score import DimensionSource, NeighborhoodReport
from app.services.score_service import ScoreUnavailableError
from main import app


async def _fake_db():
    yield MagicMock()


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def test_demo_address_still_returns_mock(client):
    resp = client.get("/api/v1/score/demo-address-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_score"] == 82
    assert body["geoid"] == "48453001100"


def test_score_unavailable_returns_code(client):
    lookup = {
        "address_raw": "1 Main St",
        "address_normalized": "1 Main St, Bentonville, AR",
        "latitude": 36.37,
        "longitude": -94.20,
        "geoid": "05007020101",
    }
    with (
        patch(
            "app.api.v1.endpoints.score.get_report",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.api.v1.endpoints.score.get_lookup",
            new=AsyncMock(return_value=lookup),
        ),
        patch(
            "app.api.v1.endpoints.score.build_report_from_scores",
            new=AsyncMock(side_effect=ScoreUnavailableError("missing")),
        ),
    ):
        resp = client.get("/api/v1/score/addr-1")

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "SCORE_UNAVAILABLE"
    assert "not available" in body["detail"].lower()


def test_live_score_returns_report_from_service(client):
    lookup = {
        "address_raw": "1 Main St",
        "address_normalized": "1 Main St, Bentonville, AR",
        "latitude": 36.37,
        "longitude": -94.20,
        "geoid": "05007020101",
    }
    report = build_mock_report(
        address_raw=lookup["address_raw"],
        address_normalized=lookup["address_normalized"],
        latitude=lookup["latitude"],
        longitude=lookup["longitude"],
        geoid=lookup["geoid"],
    )
    report = NeighborhoodReport(
        **{
            **report.model_dump(),
            "overall_score": 71.5,
            "data_vintage": "2026-Q3",
            "sources": {
                "environment": DimensionSource(
                    source_id="open_meteo",
                    reason="fallback_no_epa",
                    detail={"avg_aqi": 56.5},
                ),
                "safety": DimensionSource(
                    source_id="fbi_cde",
                    reason="agency_aggregate",
                    detail={"ori_count": 3},
                ),
                "education": DimensionSource(
                    source_id="nces_urban",
                    reason="nces_urban_blend",
                    detail={
                        "contributors": ["nces_school_data", "urban_school_data"],
                        "nearest_school_miles": 1.2,
                    },
                ),
                "economic": DimensionSource(
                    source_id="acs_bls_laus",
                    reason="acs_bls_blend",
                    detail={
                        "contributors": ["census_acs", "bls_laus"],
                        "median_hh_income": 78500,
                        "unemployment_rate": 3.1,
                    },
                ),
            },
        }
    )

    with (
        patch(
            "app.api.v1.endpoints.score.get_report",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.api.v1.endpoints.score.get_lookup",
            new=AsyncMock(return_value=lookup),
        ),
        patch(
            "app.api.v1.endpoints.score.build_report_from_scores",
            new=AsyncMock(return_value=report),
        ),
        patch(
            "app.api.v1.endpoints.score.save_report",
            new=AsyncMock(),
        ),
    ):
        resp = client.get("/api/v1/score/addr-live")

    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_score"] == 71.5
    assert body["data_vintage"] == "2026-Q3"
    assert body["geoid"] == "05007020101"
    assert body["sources"]["environment"]["source_id"] == "open_meteo"
    assert body["sources"]["environment"]["reason"] == "fallback_no_epa"
    assert body["sources"]["safety"]["source_id"] == "fbi_cde"
    assert body["sources"]["safety"]["source_id"] != "placeholder"
    assert body["sources"]["education"]["source_id"] == "nces_urban"
    assert body["sources"]["education"]["source_id"] != "placeholder"
    assert body["sources"]["economic"]["source_id"] == "acs_bls_laus"
    assert body["sources"]["economic"]["source_id"] != "placeholder"
