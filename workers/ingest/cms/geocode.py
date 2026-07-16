"""Fill missing hospital coordinates via Zippopotam.us ZIP centroids."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger("cms.geocode")

ZIPPO_URL = "https://api.zippopotam.us/us/{zip_code}"


async def _geocode_zip(
    client: httpx.AsyncClient,
    zip_code: str,
    sem: asyncio.Semaphore,
) -> tuple[str, tuple[float, float] | None]:
    async with sem:
        try:
            response = await client.get(ZIPPO_URL.format(zip_code=zip_code))
            if response.status_code == 404:
                return zip_code, None
            response.raise_for_status()
            places = response.json().get("places") or []
            if not places:
                return zip_code, None
            lat = places[0].get("latitude")
            lng = places[0].get("longitude")
            if lat is None or lng is None:
                return zip_code, None
            return zip_code, (float(lat), float(lng))
        except Exception as exc:  # noqa: BLE001
            logger.debug("ZIP geocode failed for %s: %s", zip_code, exc)
            return zip_code, None


async def _build_zip_map(zip_codes: set[str]) -> dict[str, tuple[float, float]]:
    if not zip_codes:
        return {}
    logger.info("Geocoding %s unique ZIPs via Zippopotam…", len(zip_codes))
    sem = asyncio.Semaphore(12)
    out: dict[str, tuple[float, float]] = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [_geocode_zip(client, z, sem) for z in sorted(zip_codes)]
        done = 0
        for coro in asyncio.as_completed(tasks):
            z, coords = await coro
            done += 1
            if coords:
                out[z] = coords
            if done % 200 == 0 or done == len(tasks):
                logger.info(
                    "ZIP geocode progress %s / %s (hit=%s)",
                    done,
                    len(tasks),
                    len(out),
                )
    return out


def fill_missing_coordinates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    CMS Hospital General Information no longer includes lat/lng.
    Geocode unique ZIPs once, then apply centroids to hospitals.
    """
    needed_zips: set[str] = set()
    for r in records:
        if r.get("latitude") is not None and r.get("longitude") is not None:
            continue
        z = str(r.get("zip") or "").strip()[:5]
        if len(z) == 5 and z.isdigit():
            needed_zips.add(z)

    zip_map = asyncio.run(_build_zip_map(needed_zips))

    out: list[dict[str, Any]] = []
    filled = 0
    for record in records:
        row = dict(record)
        if row.get("latitude") is not None and row.get("longitude") is not None:
            out.append(row)
            continue
        z = str(row.get("zip") or "").strip()[:5]
        coords = zip_map.get(z)
        if coords:
            row["latitude"], row["longitude"] = coords
            filled += 1
        out.append(row)

    with_coords = sum(
        1 for r in out if r.get("latitude") is not None and r.get("longitude") is not None
    )
    logger.info(
        "ZIP-geocoded %s hospitals; with coordinates: %s / %s",
        filled,
        with_coords,
        len(out),
    )
    return out
