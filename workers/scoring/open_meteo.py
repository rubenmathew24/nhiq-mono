"""Open-Meteo air-quality client for environment score fallback."""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from statistics import mean
from typing import Any

import httpx

from ingest.fixtures.constants import OPEN_METEO_LOOKBACK_DAYS

logger = logging.getLogger("scoring.open_meteo")

OPEN_METEO_AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Fail fast on hung TLS handshakes (previously 60s × thousands of counties).
_DEFAULT_TIMEOUT = float(os.getenv("OPEN_METEO_TIMEOUT", "15") or "15")
_DEFAULT_BATCH_SIZE = int(os.getenv("OPEN_METEO_BATCH_SIZE", "25") or "25")
# Keep low — 8 parallel 40-loc batches triggered HTTP 429 in Azure.
_DEFAULT_MAX_WORKERS = int(os.getenv("OPEN_METEO_MAX_WORKERS", "2") or "2")


def _mean_us_aqi_from_payload(payload: dict[str, Any]) -> float | None:
    """Mean of daily-max composite US AQI from one location payload."""
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


def _normalize_multi_payload(payload: Any) -> list[dict[str, Any]]:
    """Open-Meteo returns a list for multi-location, a dict for one location."""
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def fetch_mean_us_aqi(
    lat: float,
    lng: float,
    *,
    end: date | None = None,
    lookback_days: int = OPEN_METEO_LOOKBACK_DAYS,
    timeout: float | None = None,
) -> float | None:
    """
    Mean of daily-max composite US AQI over lookback_days ending at `end`
    (default: yesterday). Returns None on failure or empty series.
    """
    results = fetch_mean_us_aqi_many(
        [("loc", lat, lng)],
        end=end,
        lookback_days=lookback_days,
        timeout=timeout,
        batch_size=1,
        max_workers=1,
    )
    return results.get("loc")


def _fetch_batch(
    batch: list[tuple[str, float, float]],
    *,
    start_day: date,
    end_day: date,
    timeout: float,
) -> dict[str, float]:
    """One HTTP call for up to N locations (comma-separated lat/lng)."""
    if not batch:
        return {}
    lats = ",".join(str(lat) for _, lat, _ in batch)
    lngs = ",".join(str(lng) for _, _, lng in batch)
    ids = [loc_id for loc_id, _, _ in batch]
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(
                    OPEN_METEO_AQ_URL,
                    params={
                        "latitude": lats,
                        "longitude": lngs,
                        "hourly": "us_aqi",
                        "start_date": start_day.isoformat(),
                        "end_date": end_day.isoformat(),
                        "timezone": "auto",
                        "domains": "cams_global",
                    },
                )
                if response.status_code == 429:
                    wait = 2.0 * (attempt + 1)
                    logger.warning(
                        "Open-Meteo 429 for batch first=%s; retry in %.1ss",
                        ids[0],
                        wait,
                    )
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                payload = response.json()
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            wait = 1.5 * (attempt + 1)
            logger.warning(
                "Open-Meteo batch attempt=%s failed (%s locs, first=%s): %s",
                attempt + 1,
                len(batch),
                ids[0],
                exc,
            )
            time.sleep(wait)
    else:
        logger.warning(
            "Open-Meteo batch gave up (%s locs, first=%s): %s",
            len(batch),
            ids[0],
            last_exc,
        )
        return {}

    locations = _normalize_multi_payload(payload)
    out: dict[str, float] = {}
    if len(locations) != len(ids):
        logger.warning(
            "Open-Meteo batch size mismatch: requested=%s got=%s",
            len(ids),
            len(locations),
        )
    for loc_id, loc_payload in zip(ids, locations, strict=False):
        avg = _mean_us_aqi_from_payload(loc_payload)
        if avg is not None:
            out[loc_id] = avg
    return out


def fetch_mean_us_aqi_many(
    locations: list[tuple[str, float, float]],
    *,
    end: date | None = None,
    lookback_days: int = OPEN_METEO_LOOKBACK_DAYS,
    timeout: float | None = None,
    batch_size: int | None = None,
    max_workers: int | None = None,
) -> dict[str, float]:
    """
    Fetch mean US AQI for many (id, lat, lng) points.

    Batches coordinates into multi-location Open-Meteo requests and runs batches
    concurrently so national scoring is not stuck on serial ~0.4–60s calls.
    """
    if not locations:
        return {}

    end_day = end or (date.today() - timedelta(days=1))
    start_day = end_day - timedelta(days=lookback_days - 1)
    timeout_s = _DEFAULT_TIMEOUT if timeout is None else float(timeout)
    size = _DEFAULT_BATCH_SIZE if batch_size is None else max(1, int(batch_size))
    workers = _DEFAULT_MAX_WORKERS if max_workers is None else max(1, int(max_workers))

    batches = [locations[i : i + size] for i in range(0, len(locations), size)]
    out: dict[str, float] = {}
    logger.info(
        "Open-Meteo fetch locations=%s batches=%s batch_size=%s workers=%s timeout=%ss",
        len(locations),
        len(batches),
        size,
        workers,
        timeout_s,
    )

    with ThreadPoolExecutor(max_workers=min(workers, len(batches))) as pool:
        futures = [
            pool.submit(
                _fetch_batch,
                batch,
                start_day=start_day,
                end_day=end_day,
                timeout=timeout_s,
            )
            for batch in batches
        ]
        done = 0
        for fut in as_completed(futures):
            part = fut.result()
            out.update(part)
            done += 1
            if done == len(futures) or done % 5 == 0:
                logger.info(
                    "Open-Meteo batches complete=%s/%s hits=%s",
                    done,
                    len(futures),
                    len(out),
                )
    return out
