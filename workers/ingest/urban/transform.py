"""Normalize Urban CCD directory rows to schools_urban."""

from __future__ import annotations

from typing import Any


def _first(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _parse_int(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _parse_float(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _flag_text(raw: Any) -> str | None:
    if raw is None:
        return None
    return str(raw).strip() or None


def transform_urban_records(
    raw_records: list[dict[str, Any]],
    *,
    year: int,
    ncessch_allowlist: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Keep schools whose ncessch is in the NCES fixture allowlist when provided."""
    out: list[dict[str, Any]] = []
    for row in raw_records:
        ncessch = _first(row.get("ncessch"))
        if not ncessch:
            continue
        key = str(ncessch)[:12]
        if ncessch_allowlist is not None and key not in ncessch_allowlist:
            continue
        out.append(
            {
                "ncessch": key,
                "year": year,
                "enrollment": _parse_int(row.get("enrollment")),
                "teachers_fte": _parse_float(row.get("teachers_fte")),
                "school_level": _flag_text(row.get("school_level")),
                "school_type": _flag_text(row.get("school_type")),
                "school_status": _flag_text(row.get("school_status")),
                "charter": _flag_text(row.get("charter")),
                "magnet": _flag_text(row.get("magnet")),
                "virtual": _flag_text(row.get("virtual")),
                "payload": None,
            }
        )
    return out
