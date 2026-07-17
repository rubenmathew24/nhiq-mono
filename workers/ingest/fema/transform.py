"""Normalize FEMA NRI tract features for PostgreSQL upsert."""

from __future__ import annotations

from typing import Any

from ingest.fixtures.constants import DATA_VINTAGE

# Prefixes must match FeatureServer field names (*_RISKR). Layer uses ISTM/IFLD
# (not older ISTD/RFLD names — those 400 the whole outFields query).
FEMA_NRI_HAZARD_PREFIXES: tuple[str, ...] = (
    "AVLN",
    "CFLD",
    "CWAV",
    "DRGT",
    "ERQK",
    "HAIL",
    "HWAV",
    "HRCN",
    "ISTM",
    "LNDS",
    "LTNG",
    "IFLD",
    "SWND",
    "TRND",
    "TSUN",
    "VLCN",
    "WFIR",
    "WNTW",
)

FEMA_NRI_HAZARD_PREFIX_TO_SLUG: dict[str, str] = {
    "AVLN": "avalanche",
    "CFLD": "coastal_flooding",
    "CWAV": "cold_wave",
    "DRGT": "drought",
    "ERQK": "earthquake",
    "HAIL": "hail",
    "HRCN": "hurricane",
    "HWAV": "heat_wave",
    "IFLD": "inland_flooding",
    "ISTM": "ice_storm",
    "LNDS": "landslide",
    "LTNG": "lightning",
    "SWND": "strong_wind",
    "TRND": "tornado",
    "TSUN": "tsunami",
    "VLCN": "volcanic_activity",
    "WFIR": "wildfire",
    "WNTW": "winter_weather",
}

HAZARD_RATING_KEEP = frozenset(
    ("Relatively Moderate", "Relatively High", "Very High")
)


def _finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def build_geoid(stcofips: str, tract: str) -> str | None:
    stco = str(stcofips or "").strip()
    tr = str(tract or "").strip()
    if len(stco) != 5 or not stco.isdigit():
        return None
    if not tr:
        return None
    tr6 = tr.zfill(6)
    if len(tr6) != 6 or not tr6.isdigit():
        return None
    return f"{stco}{tr6}"


def build_hazards(attrs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Include hazard blocks only when RISKR is Moderate+."""
    hazards: dict[str, dict[str, Any]] = {}
    for prefix in FEMA_NRI_HAZARD_PREFIXES:
        rating = attrs.get(f"{prefix}_RISKR")
        if rating not in HAZARD_RATING_KEEP:
            continue
        slug = FEMA_NRI_HAZARD_PREFIX_TO_SLUG.get(prefix, prefix.lower())
        block = {
            k: v
            for k, v in attrs.items()
            if k.startswith(f"{prefix}_") and v is not None
        }
        if block:
            hazards[slug] = block
    return hazards


def transform_tract_feature(
    attrs: dict[str, Any],
    *,
    known_geoids: frozenset[str] | None = None,
) -> dict[str, Any] | None:
    geoid = build_geoid(str(attrs.get("STCOFIPS") or ""), str(attrs.get("TRACT") or ""))
    if not geoid:
        return None
    if known_geoids is not None and geoid not in known_geoids:
        return None

    state_fips = geoid[:2]
    county_fips = geoid[2:5]
    hazards = build_hazards(attrs)

    return {
        "geoid": geoid,
        "state_fips": state_fips,
        "county_fips": county_fips,
        "risk_score": _finite_float(attrs.get("RISK_SCORE")),
        "risk_rating": str(attrs.get("RISK_RATNG") or "").strip() or None,
        "eal_score": _finite_float(attrs.get("EAL_SCORE")),
        "sovi_score": _finite_float(attrs.get("SOVI_SCORE")),
        "resl_score": _finite_float(attrs.get("RESL_SCORE")),
        "hazards": hazards,
        "data_vintage": DATA_VINTAGE,
        "payload": attrs,
    }


def transform_tract_features(
    features: list[dict[str, Any]],
    *,
    known_geoids: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for attrs in features:
        row = transform_tract_feature(attrs, known_geoids=known_geoids)
        if row is None:
            continue
        geoid = row["geoid"]
        if geoid in seen:
            continue
        seen.add(geoid)
        out.append(row)
    return out
