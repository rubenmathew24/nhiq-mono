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


class DiscoverTractsResponse(BaseModel):
    place_name: str | None = None
    bbox: DiscoverBBox
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[DiscoverFeature] = Field(default_factory=list)
    meta: DiscoverMeta
