"""Open-Meteo air-quality client for environment score fallback."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from statistics import mean
from typing import Any

import httpx

from ingest.fixtures.constants import OPEN_METEO_LOOKBACK_DAYS

logger = logging.getLogger("scoring.open_meteo")

OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def fetch_mean_us_aqi(
    lat: float,
    lng: float,
    *,
    end: date | None = None,
    lookback_days: int = OPEN_METEO_LOOKBACK_DAYS,
    timeout: float = 60.0,
) -> float | None:
    """
    Mean of daily-max composite US AQI over lookback_days ending at `end`
    (default: yesterday). Returns None on failure or empty series.
    """
    end_day = end or (date.today() - timedelta(days=1))
    start_day = end_day - timedelta(days=lookback_days - 1)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                OPEN_METEO_AQ_URL,
                params={
                    "latitude": lat,
                    "longitude": lng,
                    "hourly": "us_aqi",
                    "start_date": start_day.isoformat(),
                    "end_date": end_day.isoformat(),
                    "timezone": "auto",
                    "domains": "cams_global",
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Open-Meteo request failed for (%s,%s): %s", lat, lng, exc)
        return None

    hourly = payload.get("hourly") or {}
    times: list[str] = hourly.get("time") or []
    values: list[Any] = hourly.get("us_aqi") or []
    if not times or not values or len(times) != len(values):
        return None

    by_day: dict[str, list[float]] = {}
    for ts, raw in zip(times, values, strict=False):
        if raw is None:
            continue
        try:
            aqi = float(raw)
        except (TypeError, ValueError):
            continue
        day = ts[:10]
        by_day.setdefault(day, []).append(aqi)

    if not by_day:
        return None

    daily_maxes = [max(v) for v in by_day.values()]
    return float(mean(daily_maxes))
