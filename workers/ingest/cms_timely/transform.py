"""Normalize CMS Timely & Effective Care hospital measure rows."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from ingest.fixtures.constants import DATA_VINTAGE

# ED wait-time measures (store whatever is present from this set).
ED_MEASURE_IDS = frozenset({"OP_18B", "OP_18C", "OP_18A", "EDV"})
ED_MEASURE_PREFIXES = ("OP_18A_", "OP_18B_", "OP_18C_")

_NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _clean_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def norm_measure_id(value: Any) -> str:
    return _clean_text(value).upper().replace("-", "_")


def is_ed_measure(measure_id: str) -> bool:
    mid = norm_measure_id(measure_id)
    if mid in ED_MEASURE_IDS:
        return True
    return any(mid.startswith(p) for p in ED_MEASURE_PREFIXES)


def _parse_date(value: Any) -> date | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_score(raw: Any) -> tuple[float | None, str | None]:
    if raw is None:
        return None, None
    text = _clean_text(raw)
    if not text:
        return None, None
    if _NUMERIC_RE.match(text):
        try:
            return float(text), None
        except ValueError:
            pass
    return None, text


def _parse_sample(raw: Any) -> float | None:
    if raw is None:
        return None
    text = _clean_text(raw)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _provider_id(row: dict[str, Any]) -> str | None:
    pid = _clean_text(row.get("facility_id") or row.get("cms_provider_id"))
    return pid or None


def transform_measure_row(
    row: dict[str, Any],
    *,
    provider_allowlist: frozenset[str] | None = None,
    state_benchmarks: dict[str, dict[str, Any]] | None = None,
    national_benchmarks: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    provider_id = _provider_id(row)
    if not provider_id:
        return None
    if provider_allowlist is not None and provider_id not in provider_allowlist:
        return None

    measure_id_raw = _clean_text(row.get("measure_id"))
    if not measure_id_raw or not is_ed_measure(measure_id_raw):
        return None

    measure_norm = norm_measure_id(measure_id_raw)
    score_value, score_text = _parse_score(row.get("score"))
    state_row = (state_benchmarks or {}).get(measure_norm, {})
    national_row = (national_benchmarks or {}).get(measure_norm, {})
    state_score, _ = _parse_score(state_row.get("score"))
    national_score, _ = _parse_score(national_row.get("score"))

    return {
        "cms_provider_id": provider_id,
        "measure_id": measure_id_raw,
        "measure_name": _clean_text(row.get("measure_name")) or None,
        "score_value": score_value,
        "score_text": score_text,
        "sample": _parse_sample(row.get("sample")),
        "footnote": _clean_text(row.get("footnote")) or None,
        "state_score": state_score,
        "national_score": national_score,
        "start_date": _parse_date(row.get("start_date")),
        "end_date": _parse_date(row.get("end_date")),
        "data_vintage": DATA_VINTAGE,
    }


def transform_measure_rows(
    rows: list[dict[str, Any]],
    *,
    provider_allowlist: frozenset[str] | None = None,
    state_benchmarks: dict[str, dict[str, Any]] | None = None,
    national_benchmarks: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        record = transform_measure_row(
            row,
            provider_allowlist=provider_allowlist,
            state_benchmarks=state_benchmarks,
            national_benchmarks=national_benchmarks,
        )
        if record is None:
            continue
        key = (record["cms_provider_id"], norm_measure_id(record["measure_id"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(record)
    return out
