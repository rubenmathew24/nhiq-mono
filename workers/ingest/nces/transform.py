"""Normalize NCES EDGE school features to schools_nces rows."""

from __future__ import annotations

from typing import Any

from ingest.fixtures.canonical_addresses import fixture_county_fips


def _first(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _parse_coords(
    attrs: dict[str, Any],
    geometry: dict[str, Any] | None,
) -> tuple[float | None, float | None]:
    lat = attrs.get("LAT")
    lng = attrs.get("LON")
    try:
        lat_f = float(lat) if lat not in (None, "") else None
        lng_f = float(lng) if lng not in (None, "") else None
    except (TypeError, ValueError):
        lat_f, lng_f = None, None
    if geometry and (lat_f is None or lng_f is None):
        try:
            lng_f = float(geometry.get("x"))
            lat_f = float(geometry.get("y"))
        except (TypeError, ValueError):
            lat_f, lng_f = None, None
    if lat_f is not None and lng_f is not None:
        if lat_f == 0.0 and lng_f == 0.0:
            return None, None
        if -90.0 <= lat_f <= 90.0 and -180.0 <= lng_f <= 180.0:
            return lat_f, lng_f
    return None, None


def _county_parts(cnty: str | None, stfip: str | None) -> tuple[str | None, str | None]:
    """EDGE CNTY is SSCCC; schema stores state_fips + 3-digit county_fips."""
    if cnty:
        digits = "".join(ch for ch in str(cnty) if ch.isdigit())
        if len(digits) >= 5:
            return digits[:2], digits[2:5]
        if len(digits) == 3 and stfip:
            return str(stfip).zfill(2), digits.zfill(3)
    if stfip:
        return str(stfip).zfill(2), None
    return None, None


def transform_nces_features(
    features: list[dict[str, Any]],
    *,
    county_allowlist: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Keep fixture-county schools with valid NCESSCH + coordinates."""
    allow = county_allowlist if county_allowlist is not None else fixture_county_fips()
    out: list[dict[str, Any]] = []
    for feature in features:
        attrs = feature.get("attributes") or {}
        ncessch = _first(attrs.get("NCESSCH"))
        if not ncessch:
            continue
        state_fips, county_fips = _county_parts(attrs.get("CNTY"), attrs.get("STFIP"))
        if not state_fips or not county_fips:
            continue
        if f"{state_fips}{county_fips}" not in allow:
            continue
        lat, lng = _parse_coords(attrs, feature.get("geometry"))
        if lat is None or lng is None:
            continue
        out.append(
            {
                "ncessch": str(ncessch)[:12],
                "leaid": _first(attrs.get("LEAID")),
                "name": _first(attrs.get("NAME")),
                "state_fips": state_fips,
                "county_fips": county_fips,
                "locale": _first(attrs.get("LOCALE")),
                "latitude": lat,
                "longitude": lng,
            }
        )
    return out
