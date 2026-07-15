"""Normalize CDE selections and offense aggregates for upsert."""

from __future__ import annotations

from datetime import date
from typing import Any


def agencies_to_rows(
    *,
    county_fips: str,
    state_abbr: str,
    agencies: list[dict[str, Any]],
    data_vintage: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, agency in enumerate(agencies):
        rows.append(
            {
                "county_fips": county_fips,
                "ori": agency["ori"],
                "agency_name": agency.get("agency_name"),
                "state_abbr": state_abbr,
                "distance_miles": agency.get("distance_miles"),
                "is_primary_hint": idx == 0,
                "data_vintage": data_vintage,
            }
        )
    return rows


def offense_aggregate_row(
    *,
    county_fips: str,
    offense_slug: str,
    incidents_12mo: float,
    state_benchmark_12mo: float | None,
    data_vintage: str,
    period_end: date | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """County-merged aggregate row (ori='' sentinel for unique key)."""
    return {
        "county_fips": county_fips,
        "ori": "",
        "offense_slug": offense_slug.upper(),
        "period_start": None,
        "period_end": period_end,
        "incidents_12mo": incidents_12mo,
        "rate_12mo": None,
        "state_benchmark_12mo": state_benchmark_12mo,
        "payload": payload,
        "data_vintage": data_vintage,
    }
