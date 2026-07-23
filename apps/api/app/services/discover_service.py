"""Discover: census tracts + overall scores intersecting a WGS84 bbox."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.discover import (
    DiscoverBBox,
    DiscoverFeature,
    DiscoverFeatureProperties,
    DiscoverMeta,
    DiscoverSummary,
    DiscoverTractHighlight,
    DiscoverTractsResponse,
)

logger = logging.getLogger(__name__)

# Reject place bboxes larger than this span (degrees) on either axis.
MAX_BBOX_SPAN_DEG = 3.0
# Cap GeoJSON features for POC payload size.
FEATURE_CAP = 2500
# ~10m-ish simplification at mid-latitudes; keeps city overlays light.
GEOMETRY_SIMPLIFY_TOLERANCE = 0.00015
# Keep central fraction of place bbox for city-scope centroids (FR-015).
CITY_CORE_SHRINK = 0.7


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


def shrink_bbox(bbox: DiscoverBBox, shrink: float = CITY_CORE_SHRINK) -> DiscoverBBox:
    """Return an axis-aligned core keeping the central `shrink` fraction of each axis."""
    shrink = max(0.01, min(1.0, shrink))
    span_lng = bbox.max_lng - bbox.min_lng
    span_lat = bbox.max_lat - bbox.min_lat
    pad_lng = span_lng * (1.0 - shrink) / 2.0
    pad_lat = span_lat * (1.0 - shrink) / 2.0
    return DiscoverBBox(
        min_lng=bbox.min_lng + pad_lng,
        min_lat=bbox.min_lat + pad_lat,
        max_lng=bbox.max_lng - pad_lng,
        max_lat=bbox.max_lat - pad_lat,
    )


def friendly_tract_label(place_name: str | None, geoid: str) -> str:
    """Short place context + tract suffix (GEOID stays secondary in UI)."""
    suffix = geoid[-6:] if len(geoid) >= 6 else geoid
    place = (place_name or "").strip()
    if place:
        # Prefer city before first comma ("Bentonville, Arkansas, …").
        short = place.split(",")[0].strip() or place
        return f"{short} · Tract {suffix}"
    return f"Tract {suffix}"


def is_discover_display_tract(aland: int | None) -> bool:
    """True for land tracts Discover may color/summarize.

    Water-only = ``aland == 0`` (TIGER ALAND). NULL means migration/backfill
    pending — treat as land until census re-ingest fills the column.
    """
    return aland is None or aland > 0


def build_city_summary(
    features: list[DiscoverFeature],
    *,
    place_name: str | None,
    scope_mode: Literal["inner_bbox", "place_polygon"] = "inner_bbox",
) -> DiscoverSummary:
    """Aggregate snapshot stats over city-scoped tracts only."""
    scoped = [f for f in features if f.properties.in_city_scope]
    scored = [
        f
        for f in scoped
        if f.properties.overall_score is not None
    ]
    scores = [float(f.properties.overall_score or 0) for f in scored]
    total_count = len(scoped)
    scored_count = len(scored)

    if scored_count == 0:
        return DiscoverSummary(
            scope_mode=scope_mode,
            average_overall=None,
            score_min=None,
            score_max=None,
            scored_count=0,
            total_count=total_count,
            highest=None,
            lowest=None,
            insufficient_data=True,
        )

    average = sum(scores) / scored_count
    score_min = min(scores)
    score_max = max(scores)

    if scored_count < 2:
        return DiscoverSummary(
            scope_mode=scope_mode,
            average_overall=round(average, 2),
            score_min=score_min,
            score_max=score_max,
            scored_count=scored_count,
            total_count=total_count,
            highest=None,
            lowest=None,
            insufficient_data=True,
        )

    highest_f = max(scored, key=lambda f: float(f.properties.overall_score or 0))
    lowest_f = min(scored, key=lambda f: float(f.properties.overall_score or 0))
    hi = float(highest_f.properties.overall_score or 0)
    lo = float(lowest_f.properties.overall_score or 0)

    return DiscoverSummary(
        scope_mode=scope_mode,
        average_overall=round(average, 2),
        score_min=score_min,
        score_max=score_max,
        scored_count=scored_count,
        total_count=total_count,
        highest=DiscoverTractHighlight(
            geoid=highest_f.properties.geoid,
            overall_score=hi,
            label=friendly_tract_label(place_name, highest_f.properties.geoid),
        ),
        lowest=DiscoverTractHighlight(
            geoid=lowest_f.properties.geoid,
            overall_score=lo,
            label=friendly_tract_label(place_name, lowest_f.properties.geoid),
        ),
        insufficient_data=False,
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
    core = shrink_bbox(bbox)
    vintage = settings.SCORE_DATA_VINTAGE
    scope_mode = "inner_bbox"

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
                ) AS geojson,
                ST_Within(
                    ST_Centroid(t.geometry),
                    ST_MakeEnvelope(
                        :core_min_lng, :core_min_lat,
                        :core_max_lng, :core_max_lat, 4326
                    )
                ) AS in_city_scope
            FROM census_tracts t
            LEFT JOIN neighborhood_scores ns
              ON ns.geoid = t.geoid
             AND ns.data_vintage = :vintage
            WHERE t.geometry IS NOT NULL
              AND (t.aland IS NULL OR t.aland > 0)
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
            "core_min_lng": core.min_lng,
            "core_min_lat": core.min_lat,
            "core_max_lng": core.max_lng,
            "core_max_lat": core.max_lat,
            "limit": limit,
        },
    )
    rows = result.mappings().all()
    truncated = len(rows) > FEATURE_CAP
    if truncated:
        rows = rows[:FEATURE_CAP]

    features: list[DiscoverFeature] = []
    scores: list[float] = []

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
        else:
            score_f = float(score)
            scores.append(score_f)

        features.append(
            DiscoverFeature(
                geometry=geometry,
                properties=DiscoverFeatureProperties(
                    geoid=str(row["geoid"]),
                    overall_score=score_f,
                    in_city_scope=bool(row["in_city_scope"]),
                ),
            )
        )

    scored_count = len(scores)
    unscored_count = sum(
        1 for f in features if f.properties.overall_score is None
    )
    summary = build_city_summary(
        features, place_name=place_name, scope_mode=scope_mode
    )

    logger.info(
        "discover_tracts place=%r features=%d scored=%d unscored=%d "
        "truncated=%s scope_mode=%s city_scoped=%d city_scored=%d",
        place_name,
        len(features),
        scored_count,
        unscored_count,
        truncated,
        scope_mode,
        summary.total_count,
        summary.scored_count,
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
        summary=summary,
    )
