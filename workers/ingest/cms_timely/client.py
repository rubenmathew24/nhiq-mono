"""CMS Provider Data Catalog — Timely & Effective Care client."""

from __future__ import annotations

import logging
from typing import Any, Iterator

import httpx

logger = logging.getLogger("cms_timely.client")

CMS_API_BASE = "https://data.cms.gov/provider-data/api/1"
METASTORE_URL = f"{CMS_API_BASE}/metastore/schemas/dataset/items"
QUERY_TEMPLATE = f"{CMS_API_BASE}/datastore/query/{{dataset_id}}/0"
PAGE_SIZE = 1000

_TIMELY_DATASET_IDS: dict[str, str | None] = {
    "hospital": None,
    "state": None,
    "national": None,
}


def _clean_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def discover_timely_dataset_ids(*, timeout: float = 45.0) -> dict[str, str | None]:
    """Resolve hospital/state/national dataset IDs from metastore (cached)."""
    if all(_TIMELY_DATASET_IDS.values()):
        return dict(_TIMELY_DATASET_IDS)

    with httpx.Client(timeout=timeout) as client:
        response = client.get(METASTORE_URL, headers={"Accept": "application/json"})
        response.raise_for_status()
        rows = response.json()

    matches: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = _clean_text(row.get("title")).lower()
            if "timely and effective care" in title:
                matches.append(row)

    for row in matches:
        title = _clean_text(row.get("title")).lower()
        dataset_id = _clean_text(row.get("identifier"))
        if not dataset_id or "rural" in title:
            continue
        if "timely and effective care - hospital" in title:
            _TIMELY_DATASET_IDS["hospital"] = dataset_id
        elif "timely and effective care - state" in title:
            _TIMELY_DATASET_IDS["state"] = dataset_id
        elif "timely and effective care - national" in title:
            _TIMELY_DATASET_IDS["national"] = dataset_id

    if not _TIMELY_DATASET_IDS["hospital"]:
        raise RuntimeError(
            "Could not find CMS 'Timely and Effective Care - Hospital' dataset"
        )
    return dict(_TIMELY_DATASET_IDS)


def iter_dataset_pages(
    dataset_id: str,
    *,
    timeout: float = 120.0,
    page_size: int = PAGE_SIZE,
) -> Iterator[list[dict[str, Any]]]:
    """Yield paginated rows from a CMS datastore dataset."""
    url = QUERY_TEMPLATE.format(dataset_id=dataset_id)
    offset = 0
    with httpx.Client(timeout=timeout) as client:
        while True:
            response = client.get(
                url,
                params={"limit": page_size, "offset": offset, "keys": "true"},
            )
            response.raise_for_status()
            data = response.json()
            records = data.get("results") or []
            if not records:
                break
            yield records
            if len(records) < page_size:
                break
            offset += page_size
            logger.debug(
                "CMS dataset %s: fetched offset %s (%s rows)",
                dataset_id,
                offset,
                len(records),
            )


def fetch_benchmark_by_measure(
    dataset_id: str | None,
    *,
    timeout: float = 120.0,
) -> dict[str, dict[str, Any]]:
    """Load measure_id → row for state/national benchmark datasets."""
    if not dataset_id:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for page in iter_dataset_pages(dataset_id, timeout=timeout):
        for row in page:
            mid = _clean_text(row.get("measure_id")).upper().replace("-", "_")
            if mid and mid not in out:
                out[mid] = row
    return out
