from typing import Literal

from pydantic import BaseModel


class Factor(BaseModel):
    name: str
    value: str
    impact: Literal["positive", "negative", "neutral"]


class ScoreDimension(BaseModel):
    score: float
    label: str
    summary: str
    factors: list[Factor]


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
