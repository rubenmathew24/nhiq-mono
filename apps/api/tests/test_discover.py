"""Discover tracts API — mocked service layer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.schemas.discover import (
    DiscoverBBox,
    DiscoverFeature,
    DiscoverFeatureProperties,
    DiscoverMeta,
    DiscoverTractsResponse,
)
from app.services.discover_service import DiscoverBBoxError, validate_bbox
from main import app


async def _fake_db():
    yield MagicMock()


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def test_validate_bbox_rejects_inverted():
    with pytest.raises(DiscoverBBoxError) as ei:
        validate_bbox(-70, 42, -71, 43)
    assert ei.value.code == "INVALID_BBOX"


def test_validate_bbox_rejects_too_large():
    with pytest.raises(DiscoverBBoxError) as ei:
        validate_bbox(-80, 30, -70, 40)
    assert ei.value.code == "BBOX_TOO_LARGE"


def test_validate_bbox_ok():
    box = validate_bbox(-71.2, 42.2, -70.9, 42.4)
    assert box.min_lng == -71.2


def test_discover_tracts_ok(client):
    payload = DiscoverTractsResponse(
        place_name="Boston",
        bbox=DiscoverBBox(
            min_lng=-71.2, min_lat=42.2, max_lng=-70.9, max_lat=42.4
        ),
        features=[
            DiscoverFeature(
                geometry={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-71.1, 42.3],
                            [-71.09, 42.3],
                            [-71.09, 42.31],
                            [-71.1, 42.31],
                            [-71.1, 42.3],
                        ]
                    ],
                },
                properties=DiscoverFeatureProperties(
                    geoid="25025000100", overall_score=72.5
                ),
            ),
            DiscoverFeature(
                geometry={
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-71.11, 42.3],
                            [-71.1, 42.3],
                            [-71.1, 42.31],
                            [-71.11, 42.31],
                            [-71.11, 42.3],
                        ]
                    ],
                },
                properties=DiscoverFeatureProperties(
                    geoid="25025000200", overall_score=None
                ),
            ),
        ],
        meta=DiscoverMeta(
            scored_count=1,
            unscored_count=1,
            truncated=False,
            score_min=72.5,
            score_max=72.5,
            data_vintage="2026-Q3",
        ),
    )
    with patch(
        "app.api.v1.endpoints.discover.fetch_tracts_in_bbox",
        new=AsyncMock(return_value=payload),
    ) as mocked:
        resp = client.get(
            "/api/v1/discover/tracts",
            params={
                "min_lng": -71.2,
                "min_lat": 42.2,
                "max_lng": -70.9,
                "max_lat": 42.4,
                "place_name": "Boston",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "FeatureCollection"
    assert body["meta"]["scored_count"] == 1
    assert body["meta"]["unscored_count"] == 1
    assert body["features"][1]["properties"]["overall_score"] is None
    mocked.assert_awaited_once()
    # Public POC: endpoint must not touch lookup stores (no side-effect calls).
    assert "address_lookups" not in str(mocked.await_args)


def test_discover_empty_features_ok(client):
    payload = DiscoverTractsResponse(
        place_name="Nowhere",
        bbox=DiscoverBBox(
            min_lng=-71.2, min_lat=42.2, max_lng=-70.9, max_lat=42.4
        ),
        features=[],
        meta=DiscoverMeta(
            scored_count=0,
            unscored_count=0,
            truncated=False,
            data_vintage="2026-Q3",
        ),
    )
    with patch(
        "app.api.v1.endpoints.discover.fetch_tracts_in_bbox",
        new=AsyncMock(return_value=payload),
    ):
        resp = client.get(
            "/api/v1/discover/tracts",
            params={
                "min_lng": -71.2,
                "min_lat": 42.2,
                "max_lng": -70.9,
                "max_lat": 42.4,
            },
        )
    assert resp.status_code == 200
    assert resp.json()["features"] == []


def test_discover_invalid_bbox(client):
    with patch(
        "app.api.v1.endpoints.discover.fetch_tracts_in_bbox",
        new=AsyncMock(
            side_effect=DiscoverBBoxError(
                "Choose a smaller area — this place bounding box is too large to map.",
                "BBOX_TOO_LARGE",
            )
        ),
    ):
        resp = client.get(
            "/api/v1/discover/tracts",
            params={
                "min_lng": -80,
                "min_lat": 30,
                "max_lng": -70,
                "max_lat": 40,
            },
        )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "BBOX_TOO_LARGE"
    assert "smaller" in body["detail"].lower()
