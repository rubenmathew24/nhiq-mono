"""CMS Provider Data Catalog — Hospital General Information client."""

from __future__ import annotations

from typing import Any, Iterator

import httpx

CMS_URL = "https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0"
PAGE_SIZE = 1000


def iter_hospital_pages(
    *,
    timeout: float = 120.0,
    page_size: int = PAGE_SIZE,
) -> Iterator[list[dict[str, Any]]]:
    """Yield pages of hospital records from the public CMS datastore API."""
    offset = 0
    with httpx.Client(timeout=timeout) as client:
        while True:
            response = client.get(
                CMS_URL,
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
