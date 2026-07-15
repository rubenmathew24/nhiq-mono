"""Normalize BLS LAUS observations to bls_laus_county rows."""

from __future__ import annotations

from typing import Any


def _parse_rate(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _period_key(obs: dict[str, Any]) -> tuple[int, int]:
    """Sort key: year desc, month desc (M01..M12)."""
    year = int(obs.get("year") or 0)
    period = str(obs.get("period") or "")
    month = int(period[1:]) if period.startswith("M") and period[1:].isdigit() else 0
    return year, month


def pick_latest_observation(
    observations: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return newest monthly LAUS observation."""
    monthly = [o for o in observations if str(o.get("period", "")).startswith("M")]
    if not monthly:
        return None
    return max(monthly, key=_period_key)


def transform_laus_series(
    county_fips: str,
    series_id: str,
    observations: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Map one county series to a bls_laus_county upsert row."""
    latest = pick_latest_observation(observations)
    if not latest:
        return None
    rate = _parse_rate(latest.get("value"))
    if rate is None:
        return None
    year = str(latest.get("year") or "")
    period = str(latest.get("period") or "")
    return {
        "county_fips": county_fips,
        "series_id": series_id,
        "period": f"{year}-{period}",
        "unemployment_rate": rate,
    }
