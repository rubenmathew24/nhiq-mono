"""Discover: census tracts + overall scores intersecting a WGS84 bbox."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.discover import (
    DiscoverBBox,
    DiscoverFeature,
    DiscoverFeatureProperties,
    DiscoverMeta,
    DiscoverTractsResponse,
)

logger = logging.getLogger(__name__)

# Reject place bboxes larger than this span (degrees) on either axis.
MAX_BBOX_SPAN_DEG = 3.0
# Cap GeoJSON features for POC payload size.
FEATURE_CAP = 2500
# ~10m-ish simplification at mid-latitudes; keeps city overlays light.
GEOMETRY_SIMPLIFY_TOLERANCE = 0.00015


class DiscoverBBoxError(Exception):
    def __init__(self, detail: str, code: str) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code


def validate_bbox(
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
) -> DiscoverBBox:
    if not all(
        isinstance(v, (int, float)) and v == v  # not NaN
        for v in (min_lng, min_lat, max_lng, max_lat)
    ):
        raise DiscoverBBoxError(
            "Provide a valid place bounding box (min/max longitude and latitude).",
            "INVALID_BBOX",
        )

    if min_lng >= max_lng or min_lat >= max_lat:
        raise DiscoverBBoxError(
            "That place bounding box is invalid (min must be less than max).",
            "INVALID_BBOX",
        )

    if not (-180.0 <= min_lng <= 180.0 and -180.0 <= max_lng <= 180.0):
        raise DiscoverBBoxError(
            "Longitude must be between -180 and 180.",
            "INVALID_BBOX",
        )
    if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise DiscoverBBoxError(
            "Latitude must be between -90 and 90.",
            "INVALID_BBOX",
        )

    span_lng = max_lng - min_lng
    span_lat = max_lat - min_lat
    if span_lng > MAX_BBOX_SPAN_DEG or span_lat > MAX_BBOX_SPAN_DEG:
        raise DiscoverBBoxError(
            "Choose a smaller area — this place bounding box is too large to map.",
            "BBOX_TOO_LARGE",
        )

    return DiscoverBBox(
        min_lng=float(min_lng),
        min_lat=float(min_lat),
        max_lng=float(max_lng),
        max_lat=float(max_lat),
    )


async def fetch_tracts_in_bbox(
    session: AsyncSession,
    *,
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
    place_name: str | None = None,
) -> DiscoverTractsResponse:
    bbox = validate_bbox(min_lng, min_lat, max_lng, max_lat)
    vintage = settings.SCORE_DATA_VINTAGE

    # Fetch one extra row to detect truncation without a separate COUNT.
    limit = FEATURE_CAP + 1
    result = await session.execute(
        text(
            """
            SELECT
                t.geoid AS geoid,
                ns.overall_score AS overall_score,
                ST_AsGeoJSON(
                    ST_SimplifyPreserveTopology(t.geometry, :tol)
                ) AS geojson
            FROM census_tracts t
            LEFT JOIN neighborhood_scores ns
              ON ns.geoid = t.geoid
             AND ns.data_vintage = :vintage
            WHERE t.geometry IS NOT NULL
              AND ST_Intersects(
                    t.geometry,
                    ST_MakeEnvelope(
                        :min_lng, :min_lat, :max_lng, :max_lat, 4326
                    )
                  )
            ORDER BY t.geoid
            LIMIT :limit
            """
        ),
        {
            "tol": GEOMETRY_SIMPLIFY_TOLERANCE,
            "vintage": vintage,
            "min_lng": bbox.min_lng,
            "min_lat": bbox.min_lat,
            "max_lng": bbox.max_lng,
            "max_lat": bbox.max_lat,
            "limit": limit,
        },
    )
    rows = result.mappings().all()
    truncated = len(rows) > FEATURE_CAP
    if truncated:
        rows = rows[:FEATURE_CAP]

    features: list[DiscoverFeature] = []
    scores: list[float] = []
    unscored = 0

    for row in rows:
        geo_raw = row["geojson"]
        if not geo_raw:
            continue
        try:
            geometry: dict[str, Any] = json.loads(geo_raw)
        except (TypeError, json.JSONDecodeError):
            logger.warning("discover_skip_bad_geojson geoid=%s", row["geoid"])
            continue

        score = row["overall_score"]
        score_f: float | None
        if score is None:
            score_f = None
            unscored += 1
        else:
            score_f = float(score)
            scores.append(score_f)

        features.append(
            DiscoverFeature(
                geometry=geometry,
                properties=DiscoverFeatureProperties(
                    geoid=str(row["geoid"]),
                    overall_score=score_f,
                ),
            )
        )

    scored_count = len(scores)
    # Recompute unscored from features in case some rows lacked geometry.
    unscored_count = sum(
        1 for f in features if f.properties.overall_score is None
    )

    logger.info(
        "discover_tracts place=%r features=%d scored=%d unscored=%d truncated=%s",
        place_name,
        len(features),
        scored_count,
        unscored_count,
        truncated,
    )

    return DiscoverTractsResponse(
        place_name=place_name,
        bbox=bbox,
        features=features,
        meta=DiscoverMeta(
            scored_count=scored_count,
            unscored_count=unscored_count,
            truncated=truncated,
            score_min=min(scores) if scores else None,
            score_max=max(scores) if scores else None,
            data_vintage=vintage,
        ),
    )
