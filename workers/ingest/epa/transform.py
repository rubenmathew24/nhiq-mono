"""Normalize EPA AQS records and filter to fixture counties."""

from __future__ import annotations

from typing import Any

from ingest.fixtures.canonical_addresses import fixture_county_fips


def transform_aqi_records(
    raw_records: list[dict[str, Any]],
    *,
    county_allowlist: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Normalize raw EPA API records to epa_aqi_readings columns.

    Skips malformed rows. When county_allowlist is set (default: fixture
    counties), drops rows outside that set.

    Dedupes on (county_fips, parameter_code, date_local) because AQS returns
    multiple site/standard rows per day — prefers the max non-null AQI.
    """
    allow = county_allowlist if county_allowlist is not None else fixture_county_fips()
    best: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
    for r in raw_records:
        try:
            state_code = str(r["state_code"]).zfill(2)[-2:]
            county_code = str(r["county_code"]).zfill(3)[-3:]
            county_fips = f"{state_code}{county_code}"
            if allow and county_fips not in allow:
                continue
            aqi_raw = r.get("aqi")
            aqi = (
                int(aqi_raw)
                if aqi_raw is not None and str(aqi_raw).strip() != ""
                else None
            )
            date_local = r.get("date_local")
            parameter_code = r.get("parameter_code")
            key = (county_fips, parameter_code, date_local)
            candidate = {
                "county_fips": county_fips,
                "parameter_code": parameter_code,
                "parameter_name": r.get("parameter"),
                "aqi": aqi,
                "category": r.get("category"),
                "date_local": date_local,
                "state_name": r.get("state"),
                "county_name": r.get("county"),
            }
            prev = best.get(key)
            if prev is None:
                best[key] = candidate
            else:
                prev_aqi = prev.get("aqi")
                if aqi is not None and (prev_aqi is None or aqi > prev_aqi):
                    best[key] = candidate
        except (KeyError, TypeError, ValueError):
            continue
    return list(best.values())
