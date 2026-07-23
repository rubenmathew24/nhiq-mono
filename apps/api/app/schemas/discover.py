"""Pydantic models for Discover tracts-in-bbox API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DiscoverBBox(BaseModel):
    min_lng: float
    min_lat: float
    max_lng: float
    max_lat: float


class DiscoverFeatureProperties(BaseModel):
    geoid: str
    overall_score: float | None = None
    in_city_scope: bool = False


class DiscoverFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: DiscoverFeatureProperties


class DiscoverMeta(BaseModel):
    scored_count: int = 0
    unscored_count: int = 0
    truncated: bool = False
    score_min: float | None = None
    score_max: float | None = None
    data_vintage: str


class DiscoverTractHighlight(BaseModel):
    geoid: str
    overall_score: float
    label: str


class DiscoverSummary(BaseModel):
    scope_mode: Literal["inner_bbox", "place_polygon"] = "inner_bbox"
    average_overall: float | None = None
    score_min: float | None = None
    score_max: float | None = None
    scored_count: int = 0
    total_count: int = 0
    highest: DiscoverTractHighlight | None = None
    lowest: DiscoverTractHighlight | None = None
    insufficient_data: bool = True


class DiscoverTractsResponse(BaseModel):
    place_name: str | None = None
    bbox: DiscoverBBox
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[DiscoverFeature] = Field(default_factory=list)
    meta: DiscoverMeta
    summary: DiscoverSummary
