"""Normalize CMS hospital records and filter to fixture states."""

from __future__ import annotations

import re
from typing import Any

from ingest.fixtures.canonical_addresses import fixture_state_abbrs

_POINT_RE = re.compile(
    r"POINT\s*\(\s*(?P<lng>-?\d+(?:\.\d+)?)\s+(?P<lat>-?\d+(?:\.\d+)?)\s*\)",
    re.IGNORECASE,
)


def parse_star_rating(raw: Any) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() == "not available":
        return None
    try:
        value = int(float(text))
    except (TypeError, ValueError):
        return None
    if 1 <= value <= 5:
        return value
    return None


def parse_coords(raw_lat: Any, raw_lng: Any, location: Any = None) -> tuple[float | None, float | None]:
    try:
        lat = float(raw_lat) if raw_lat not in (None, "") else None
        lng = float(raw_lng) if raw_lng not in (None, "") else None
    except (TypeError, ValueError):
        lat, lng = None, None
    if lat is not None and lng is not None:
        if lat == 0.0 and lng == 0.0:
            return None, None
        if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
            return lat, lng
    if location:
        match = _POINT_RE.search(str(location))
        if match:
            lng = float(match.group("lng"))
            lat = float(match.group("lat"))
            if not (lat == 0.0 and lng == 0.0):
                return lat, lng
    return None, None


def _first(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def transform_hospital_records(
    raw_records: list[dict[str, Any]],
    *,
    state_allowlist: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Keep hospitals in fixture states; null invalid ratings/coords.

    CMS Provider Data Catalog no longer ships lat/lng on this dataset —
    coords may be filled later by the geocode step when missing.
    """
    allow = state_allowlist if state_allowlist is not None else fixture_state_abbrs()
    out: list[dict[str, Any]] = []
    for r in raw_records:
        provider_id = _first(r.get("facility_id"), r.get("provider_id"))
        if not provider_id:
            continue
        state = (_first(r.get("state")) or "").upper()
        if allow and state not in allow:
            continue
        lat, lng = parse_coords(r.get("lat"), r.get("lng"), r.get("location"))
        out.append(
            {
                "cms_provider_id": str(provider_id)[:10],
                "name": _first(r.get("facility_name"), r.get("name")),
                "address": _first(r.get("address")),
                "city": _first(r.get("citytown"), r.get("city_town"), r.get("city")),
                "state": state,
                "zip": _first(r.get("zip_code"), r.get("zip")),
                "county_name": _first(
                    r.get("countyparish"),
                    r.get("county_name"),
                    r.get("county_parish"),
                ),
                "phone": _first(r.get("telephone_number"), r.get("phone_number")),
                "hospital_type": _first(r.get("hospital_type")),
                "star_rating": parse_star_rating(r.get("hospital_overall_rating")),
                "emergency_services": str(
                    _first(r.get("emergency_services")) or ""
                ).strip()
                == "Yes",
                "latitude": lat,
                "longitude": lng,
            }
        )
    return out
