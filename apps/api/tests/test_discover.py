"""Discover tracts API — mocked service layer + city summary helpers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.schemas.discover import (
    DiscoverBBox,
    DiscoverFeature,
    DiscoverFeatureProperties,
    DiscoverMeta,
    DiscoverSummary,
    DiscoverTractHighlight,
    DiscoverTractsResponse,
)
from app.services.discover_service import (
    DiscoverBBoxError,
    build_city_summary,
    friendly_tract_label,
    is_discover_display_tract,
    shrink_bbox,
    validate_bbox,
)
from main import app


async def _fake_db():
    yield MagicMock()


@pytest.fixture()
def client():
    app.dependency_overrides[get_db] = _fake_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _empty_summary(**overrides):
    base = dict(
        scope_mode="inner_bbox",
        average_overall=None,
        score_min=None,
        score_max=None,
        scored_count=0,
        total_count=0,
        highest=None,
        lowest=None,
        insufficient_data=True,
    )
    base.update(overrides)
    return DiscoverSummary(**base)


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


def test_shrink_bbox_keeps_central_fraction():
    box = DiscoverBBox(min_lng=0.0, min_lat=0.0, max_lng=10.0, max_lat=10.0)
    core = shrink_bbox(box, shrink=0.7)
    assert core.min_lng == pytest.approx(1.5)
    assert core.max_lng == pytest.approx(8.5)
    assert core.min_lat == pytest.approx(1.5)
    assert core.max_lat == pytest.approx(8.5)


def test_friendly_tract_label_uses_city_prefix():
    assert (
        friendly_tract_label("Bentonville, Arkansas, United States", "05007020102")
        == "Bentonville · Tract 020102"
    )


def test_is_discover_display_tract_excludes_water_only():
    assert is_discover_display_tract(0) is False
    assert is_discover_display_tract(1) is True
    assert is_discover_display_tract(None) is True  # pre-backfill = land


def test_build_city_summary_ignores_non_city_fringe():
    features = [
        DiscoverFeature(
            geometry={"type": "Polygon", "coordinates": []},
            properties=DiscoverFeatureProperties(
                geoid="a", overall_score=99.0, in_city_scope=False
            ),
        ),
        DiscoverFeature(
            geometry={"type": "Polygon", "coordinates": []},
            properties=DiscoverFeatureProperties(
                geoid="b", overall_score=80.0, in_city_scope=True
            ),
        ),
        DiscoverFeature(
            geometry={"type": "Polygon", "coordinates": []},
            properties=DiscoverFeatureProperties(
                geoid="c", overall_score=40.0, in_city_scope=True
            ),
        ),
        DiscoverFeature(
            geometry={"type": "Polygon", "coordinates": []},
            properties=DiscoverFeatureProperties(
                geoid="d", overall_score=None, in_city_scope=True
            ),
        ),
    ]
    summary = build_city_summary(features, place_name="Demo City")
    assert summary.scored_count == 2
    assert summary.total_count == 3
    assert summary.average_overall == 60.0
    assert summary.insufficient_data is False
    assert summary.highest is not None and summary.highest.geoid == "b"
    assert summary.highest.overall_score == 80.0
    assert "Demo City" in summary.highest.label
    assert summary.lowest is not None and summary.lowest.geoid == "c"
    # Fringe 99 must not win highest.
    assert summary.score_max == 80.0


def test_build_city_summary_insufficient_when_one_scored():
    features = [
        DiscoverFeature(
            geometry={"type": "Polygon", "coordinates": []},
            properties=DiscoverFeatureProperties(
                geoid="only", overall_score=55.0, in_city_scope=True
            ),
        ),
    ]
    summary = build_city_summary(features, place_name="Solo")
    assert summary.insufficient_data is True
    assert summary.highest is None
    assert summary.lowest is None
    assert summary.average_overall == 55.0
    assert summary.scored_count == 1


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
                    geoid="25025000100",
                    overall_score=72.5,
                    in_city_scope=True,
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
                    geoid="25025000200",
                    overall_score=None,
                    in_city_scope=True,
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
        summary=_empty_summary(
            average_overall=72.5,
            score_min=72.5,
            score_max=72.5,
            scored_count=1,
            total_count=2,
            insufficient_data=True,
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
    assert body["features"][0]["properties"]["in_city_scope"] is True
    assert body["summary"]["insufficient_data"] is True
    mocked.assert_awaited_once()
    assert "address_lookups" not in str(mocked.await_args)


def test_discover_summary_high_low_payload(client):
    payload = DiscoverTractsResponse(
        place_name="Bentonville, Arkansas",
        bbox=DiscoverBBox(
            min_lng=-94.3, min_lat=36.3, max_lng=-94.1, max_lat=36.5
        ),
        features=[
            DiscoverFeature(
                geometry={"type": "Polygon", "coordinates": []},
                properties=DiscoverFeatureProperties(
                    geoid="05007020102",
                    overall_score=91.0,
                    in_city_scope=True,
                ),
            ),
            DiscoverFeature(
                geometry={"type": "Polygon", "coordinates": []},
                properties=DiscoverFeatureProperties(
                    geoid="05007020101",
                    overall_score=54.2,
                    in_city_scope=True,
                ),
            ),
        ],
        meta=DiscoverMeta(
            scored_count=2,
            unscored_count=0,
            truncated=False,
            score_min=54.2,
            score_max=91.0,
            data_vintage="2026-Q3",
        ),
        summary=DiscoverSummary(
            scope_mode="inner_bbox",
            average_overall=72.6,
            score_min=54.2,
            score_max=91.0,
            scored_count=2,
            total_count=2,
            highest=DiscoverTractHighlight(
                geoid="05007020102",
                overall_score=91.0,
                label="Bentonville · Tract 020102",
            ),
            lowest=DiscoverTractHighlight(
                geoid="05007020101",
                overall_score=54.2,
                label="Bentonville · Tract 020101",
            ),
            insufficient_data=False,
        ),
    )
    with patch(
        "app.api.v1.endpoints.discover.fetch_tracts_in_bbox",
        new=AsyncMock(return_value=payload),
    ):
        resp = client.get(
            "/api/v1/discover/tracts",
            params={
                "min_lng": -94.3,
                "min_lat": 36.3,
                "max_lng": -94.1,
                "max_lat": 36.5,
                "place_name": "Bentonville, Arkansas",
            },
        )
    assert resp.status_code == 200
    summary = resp.json()["summary"]
    assert summary["insufficient_data"] is False
    assert summary["highest"]["geoid"] == "05007020102"
    assert summary["lowest"]["geoid"] == "05007020101"
    assert summary["scope_mode"] == "inner_bbox"


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
        summary=_empty_summary(),
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
    assert resp.json()["summary"]["insufficient_data"] is True


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
