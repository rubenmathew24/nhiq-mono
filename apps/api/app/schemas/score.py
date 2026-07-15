from typing import Any, Literal

from pydantic import BaseModel, Field


class Factor(BaseModel):
    name: str
    value: str
    impact: Literal["positive", "negative", "neutral"]


class ScoreDimension(BaseModel):
    score: float
    label: str
    summary: str
    factors: list[Factor]


class DimensionSource(BaseModel):
    """Provenance for one score dimension (future “show sources” UI)."""

    source_id: str
    reason: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class NeighborhoodReport(BaseModel):
    address: str
    address_normalized: str
    geoid: str
    latitude: float
    longitude: float
    overall_score: float
    healthcare: ScoreDimension
    safety: ScoreDimension
    environment: ScoreDimension
    education: ScoreDimension
    economic: ScoreDimension
    narrative: str
    data_vintage: str
    computed_at: str
    # Machine-readable sources; web may ignore until a showcase feature ships.
    sources: dict[str, DimensionSource] = Field(default_factory=dict)
