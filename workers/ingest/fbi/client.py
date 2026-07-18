"""Thin FBI CDE chart client (probe-aligned; not a full probe vendor)."""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from datetime import date
from typing import Any
from urllib.parse import quote

import httpx

from ingest.fixtures.constants import (
    FBI_CDE_CHART_OFFENSES_DEFAULT,
    FBI_CDE_CHART_YEARS,
    FBI_CDE_MAX_AGENCY_DISTANCE_MILES,
    FBI_CDE_TARGET_AGENCIES,
)

logger = logging.getLogger("fbi.client")

CHART_BASE_DEFAULT = "https://api.usa.gov/crime/fbi/cde"
AGENCY_TYPE_DENYLIST = (
    "school",
    "university",
    "college",
    "campus",
    "state park",
    "park police",
    "transit",
    "airport",
    "housing authority",
    "fish and wildlife",
    "forest service",
    "tribal",
)

# Shared rate limiter: ~4 req/s matches prior 0.25s sleep between chart calls.
_RATE_LOCK = threading.Lock()
_RATE_NEXT = 0.0
_RATE_INTERVAL = 0.25

# Per-process agency list cache (state abbr -> agencies).
_AGENCY_CACHE: dict[str, list[dict[str, Any]]] = {}
_AGENCY_CACHE_LOCK = threading.Lock()


def max_concurrency() -> int:
    raw = (os.getenv("FBI_MAX_CONCURRENCY") or "4").strip()
    try:
        return max(1, min(16, int(raw)))
    except ValueError:
        return 4


def pause_between_requests() -> None:
    """Thread-safe pacer (~4 requests/sec shared across workers)."""
    global _RATE_NEXT
    with _RATE_LOCK:
        now = time.monotonic()
        wait = _RATE_NEXT - now
        if wait > 0:
            time.sleep(wait)
            now = time.monotonic()
        _RATE_NEXT = now + _RATE_INTERVAL


def clear_agency_cache() -> None:
    with _AGENCY_CACHE_LOCK:
        _AGENCY_CACHE.clear()


def require_api_key() -> str:
    key = os.getenv("FBI_CDE_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "FBI_CDE_API_KEY is required for FBI CDE ingest. "
            "Sign up at https://api.data.gov/signup/ and set it in .env."
        )
    return key


def chart_base() -> str:
    # Compose often passes FBI_CDE_CHART_BASE= when unset; empty must not win over default.
    raw = (os.getenv("FBI_CDE_CHART_BASE") or "").strip()
    return (raw or CHART_BASE_DEFAULT).rstrip("/")


def max_agency_distance_miles() -> float:
    raw = os.getenv("FBI_CDE_MAX_AGENCY_DISTANCE_MILES", "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return FBI_CDE_MAX_AGENCY_DISTANCE_MILES


def chart_offenses() -> tuple[str, ...]:
    raw = os.getenv("FBI_CDE_CHART_OFFENSES", "").strip()
    if not raw:
        return FBI_CDE_CHART_OFFENSES_DEFAULT
    parts = tuple(p.strip().upper() for p in raw.split(",") if p.strip())
    if "HOM" not in parts:
        raise RuntimeError("FBI_CDE_CHART_OFFENSES override must include HOM")
    return parts


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


# Transient CDE / api.data.gov failures — retry before giving up on a county.
_RETRY_STATUS = frozenset({429, 502, 503, 504})
_RETRY_ATTEMPTS = 3
_RETRY_BASE_SLEEP_SEC = 1.0


def _chart_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = require_api_key()
    base = chart_base()
    rel = path if path.startswith("/") else f"/{path}"
    query = dict(params or {})
    # CDE chart host accepts API_KEY query param (probe verifies both styles).
    query["API_KEY"] = api_key
    url = f"{base}{rel}"
    last_exc: Exception | None = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(url, params=query)
                if response.status_code in _RETRY_STATUS:
                    raise httpx.HTTPStatusError(
                        f"Transient HTTP {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                payload = response.json()
            if isinstance(payload, dict):
                return payload
            return {"results": payload}
        except (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException) as exc:
            last_exc = exc
            status = (
                exc.response.status_code
                if isinstance(exc, httpx.HTTPStatusError)
                else None
            )
            retryable = status in _RETRY_STATUS or not isinstance(exc, httpx.HTTPStatusError)
            if not retryable or attempt >= _RETRY_ATTEMPTS:
                raise
            sleep_s = _RETRY_BASE_SLEEP_SEC * (2 ** (attempt - 1))
            logger.warning(
                "CDE GET %s attempt %s/%s failed (%s); retry in %.1fs",
                rel,
                attempt,
                _RETRY_ATTEMPTS,
                exc,
                sleep_s,
            )
            time.sleep(sleep_s)
    assert last_exc is not None
    raise last_exc


def _agency_lat_lon(agency: dict[str, Any]) -> tuple[float, float] | None:
    lat = agency.get("latitude") or agency.get("lat")
    lon = agency.get("longitude") or agency.get("lng") or agency.get("lon")
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        return None
    return lat_f, lon_f


def _denied_agency(agency: dict[str, Any]) -> bool:
    blob = " ".join(
        str(agency.get(k) or "")
        for k in ("agency_name", "agencyName", "name", "agency_type_name", "type")
    ).lower()
    return any(tok in blob for tok in AGENCY_TYPE_DENYLIST)


def _extract_agencies(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [a for a in payload if isinstance(a, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("agencies", "results", "data", "items"):
        val = payload.get(key)
        if isinstance(val, list):
            return [a for a in val if isinstance(a, dict)]
    if payload and all(isinstance(v, list) for v in payload.values()):
        flat: list[dict[str, Any]] = []
        for bucket, val in payload.items():
            for a in val:
                if isinstance(a, dict):
                    merged = dict(a)
                    merged["_cde_county_bucket"] = str(bucket).strip().upper()
                    flat.append(merged)
        return flat
    return []


def fetch_agencies_by_state(state_abbr: str) -> list[dict[str, Any]]:
    """Fetch agencies for a state; cached per-process by state abbr."""
    key = state_abbr.strip().upper()
    with _AGENCY_CACHE_LOCK:
        cached = _AGENCY_CACHE.get(key)
    if cached is not None:
        return cached

    st = quote(key, safe="")
    pause_between_requests()
    data = _chart_get(f"/agency/byStateAbbr/{st}")
    agencies: list[dict[str, Any]] = []
    for raw in _extract_agencies(data):
        ori = raw.get("ori") or raw.get("ORI")
        name = raw.get("agency_name") or raw.get("agencyName") or raw.get("name")
        coords = _agency_lat_lon(raw)
        if not ori or not coords:
            continue
        agencies.append(
            {
                "ori": str(ori).strip(),
                "agency_name": str(name or ori),
                "latitude": coords[0],
                "longitude": coords[1],
                "_cde_county_bucket": raw.get("_cde_county_bucket"),
            }
        )
    with _AGENCY_CACHE_LOCK:
        _AGENCY_CACHE[key] = agencies
    return agencies


def select_nearest_agencies(
    agencies: list[dict[str, Any]],
    *,
    lat: float,
    lon: float,
    county_name: str,
    max_miles: float | None = None,
    limit: int = FBI_CDE_TARGET_AGENCIES,
) -> list[dict[str, Any]]:
    """Distance + denylist filter; prefer agencies whose CDE bucket matches county."""
    cap = max_miles if max_miles is not None else max_agency_distance_miles()
    county_tok = "".join(ch for ch in county_name.upper() if ch.isalnum())
    scored: list[tuple[float, dict[str, Any]]] = []
    for agency in agencies:
        if _denied_agency(agency):
            continue
        dist = haversine_miles(lat, lon, float(agency["latitude"]), float(agency["longitude"]))
        if dist > cap:
            continue
        bucket = str(agency.get("_cde_county_bucket") or "")
        bnorm = "".join(ch for ch in bucket.upper() if ch.isalnum())
        bias = -1.0 if county_tok and bnorm and (county_tok in bnorm or bnorm in county_tok) else 0.0
        scored.append((dist + bias, {**agency, "distance_miles": round(dist, 2)}))

    if len(scored) < limit and cap == max_agency_distance_miles():
        # One widen pass (probe: ×1.5)
        return select_nearest_agencies(
            agencies,
            lat=lat,
            lon=lon,
            county_name=county_name,
            max_miles=cap * 1.5,
            limit=limit,
        )

    scored.sort(key=lambda t: t[0])
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, agency in scored:
        ori = agency["ori"]
        if ori in seen:
            continue
        seen.add(ori)
        picked.append(agency)
        if len(picked) >= limit:
            break
    return picked


def _mm_yyyy(d: date) -> str:
    return f"{d.month:02d}-{d.year}"


def chart_window(anchor: date | None = None) -> tuple[str, str]:
    end = anchor or date.today().replace(day=1)
    start = date(end.year - FBI_CDE_CHART_YEARS, end.month, 1)
    return _mm_yyyy(start), _mm_yyyy(end)


def fetch_agency_offense_chart(
    ori: str, offense_slug: str, from_mm: str, to_mm: str
) -> dict[str, Any]:
    ori_enc = quote(ori.strip(), safe="")
    slug = offense_slug.strip().upper()
    return _chart_get(
        f"/summarized/agency/{ori_enc}/{slug}",
        {"from": from_mm, "to": to_mm},
    )


def fetch_state_offense_chart(
    state_abbr: str, offense_slug: str, from_mm: str, to_mm: str
) -> dict[str, Any]:
    st = quote(state_abbr.strip().upper(), safe="")
    slug = offense_slug.strip().upper()
    return _chart_get(
        f"/summarized/state/{st}/{slug}",
        {"from": from_mm, "to": to_mm},
    )


def sum_last_n_month_counts(chart: dict[str, Any], *, n: int = 12) -> float:
    """Best-effort sum of recent monthly actuals from a CDE chart payload."""
    offenses = chart.get("offenses") if isinstance(chart, dict) else None
    if not isinstance(offenses, dict):
        return 0.0
    actuals = offenses.get("actuals")
    if not isinstance(actuals, dict):
        return 0.0

    # Actuals is often { series_name: { "MM-YYYY": count, ... }, ... }
    month_totals: dict[str, float] = {}
    for series in actuals.values():
        if not isinstance(series, dict):
            continue
        for month_key, raw in series.items():
            if not isinstance(month_key, str) or "-" not in month_key:
                continue
            try:
                val = float(raw)
            except (TypeError, ValueError):
                continue
            month_totals[month_key] = month_totals.get(month_key, 0.0) + val

    if not month_totals:
        return 0.0

    def sort_key(k: str) -> tuple[int, int]:
        try:
            mm, yyyy = k.split("-", 1)
            return int(yyyy), int(mm)
        except ValueError:
            return (0, 0)

    ordered = sorted(month_totals.keys(), key=sort_key)
    tail = ordered[-n:]
    return float(sum(month_totals[m] for m in tail))
