"""Pydantic models for GET /api/v1/coverage."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceCoverage(BaseModel):
    job_name: str
    grain: Literal["county", "state", "hospital"]
    done_count: int
    total_count: int
    pct_complete: float


class StateCoverage(BaseModel):
    state_fips: str
    state_abbr: str
    county_total: int
    sources: list[SourceCoverage]


class CoverageResponse(BaseModel):
    captured_at: datetime
    overall_pct: float
    county_universe_count: int
    state_universe_count: int
    empty_universe: bool = False
    sources: list[SourceCoverage] = Field(default_factory=list)
    states: list[StateCoverage] = Field(default_factory=list)
