"""FEMA NRI client — bulk national tracts CSV (preferred) + ArcGIS county fallback."""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("fema.client")

FEMA_NRI_LAYER = (
    "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
    "National_Risk_Index_Census_Tracts/FeatureServer/0/query"
)

# Official NRI "All Census tracts" Table Format zip (OpenFEMA v1.20).
# Override with FEMA_NRI_BULK_URL if FEMA relocates the file. Note: fema.gov
# often returns Akamai 403 HTML to non-browser clients; national ingest then
# falls back to ArcGIS FeatureServer queries (see fema/run.py).
DEFAULT_FEMA_NRI_BULK_URL = (
    "https://www.fema.gov/about/reports-and-data/openfema/nri/v120/"
    "NRI_Table_CensusTracts.zip"
)

# Prefer TRACTFIPS when present (ArcGIS / Table Format).
ROOT_FIELDS = (
    "STCOFIPS",
    "TRACT",
    "TRACTFIPS",
    "RISK_SCORE",
    "RISK_RATNG",
    "EAL_SCORE",
    "SOVI_SCORE",
    "RESL_SCORE",
)

PAGE_SIZE = 2000

# Process-local cache: url -> (sha256_hex, list[dict attrs])
_BULK_CACHE: dict[str, tuple[str, list[dict[str, Any]]]] = {}


def hazard_riskr_fields(prefixes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f"{p}_RISKR" for p in prefixes)


def build_out_fields(prefixes: tuple[str, ...]) -> str:
    return ",".join(ROOT_FIELDS + hazard_riskr_fields(prefixes))


def bulk_url() -> str:
    return (os.getenv("FEMA_NRI_BULK_URL") or DEFAULT_FEMA_NRI_BULK_URL).strip()


def use_bulk_files() -> bool:
    raw = (os.getenv("FEMA_USE_BULK_FILES") or "1").strip().lower()
    return raw in ("1", "true", "yes")


def _normalize_csv_row(row: dict[str, str]) -> dict[str, Any]:
    """Map NRI Table Format CSV columns to ArcGIS-like attribute keys."""
    # Strip BOM / whitespace from headers already handled by DictReader.
    get = row.get

    def first(*keys: str) -> str | None:
        for k in keys:
            v = get(k)
            if v is not None and str(v).strip() != "":
                return str(v).strip()
        return None

    geoid = first("TRACTFIPS", "GEOID", "CensusTract", "census_tract")
    stcofips = first("STCOFIPS", "COUNTYFIPS", "COUNTYFP")
    tract = first("TRACT", "TRACTCE", "TRACTCODE")

    if geoid and len(geoid) == 11 and geoid.isdigit():
        stcofips = geoid[:5]
        tract = geoid[5:]
    elif stcofips and len(stcofips) == 5 and tract:
        pass
    elif stcofips and len(stcofips) == 5 and not tract and geoid and len(geoid) >= 6:
        tract = geoid[-6:]

    attrs: dict[str, Any] = {
        "STCOFIPS": stcofips,
        "TRACT": tract,
        "RISK_SCORE": first("RISK_SCORE"),
        "RISK_RATNG": first("RISK_RATNG", "RISK_RATING"),
        "EAL_SCORE": first("EAL_SCORE"),
        "SOVI_SCORE": first("SOVI_SCORE"),
        "RESL_SCORE": first("RESL_SCORE"),
    }
    # Copy hazard *_RISKR columns verbatim (CSV and ArcGIS share names).
    for key, val in row.items():
        if key.endswith("_RISKR") and key not in attrs:
            attrs[key] = val
    return attrs


def _parse_nri_csv_bytes(
    data: bytes,
    *,
    stcofips_filter: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    text = data.decode("utf-8-sig", errors="replace")
    return _parse_nri_csv_text(text, stcofips_filter=stcofips_filter)


def _parse_nri_csv_text(
    text: str,
    *,
    stcofips_filter: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    out: list[dict[str, Any]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        attrs = _normalize_csv_row(
            {str(k): ("" if v is None else str(v)) for k, v in row.items()}
        )
        stco = attrs.get("STCOFIPS")
        if not stco or not attrs.get("TRACT"):
            continue
        if stcofips_filter is not None and str(stco) not in stcofips_filter:
            continue
        out.append(attrs)
    return out


def _extract_csv_member_name(zf: zipfile.ZipFile) -> str:
    names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not names:
        raise RuntimeError("FEMA NRI bulk zip contains no CSV files")
    preferred = next((n for n in names if "tract" in n.lower()), names[0])
    logger.info("FEMA bulk zip entry=%s (%s csv files)", preferred, len(names))
    return preferred


def _extract_csv_from_zip(zip_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        return zf.read(_extract_csv_member_name(zf))


def _stream_parse_zip_path(
    zip_path: Path,
    *,
    stcofips_filter: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """Parse tracts CSV from a zip on disk without holding the full CSV in RAM."""
    out: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        member = _extract_csv_member_name(zf)
        with zf.open(member, "r") as raw:
            text_stream = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
            reader = csv.DictReader(text_stream)
            for row in reader:
                if not isinstance(row, dict):
                    continue
                attrs = _normalize_csv_row(
                    {str(k): ("" if v is None else str(v)) for k, v in row.items()}
                )
                stco = attrs.get("STCOFIPS")
                if not stco or not attrs.get("TRACT"):
                    continue
                if stcofips_filter is not None and str(stco) not in stcofips_filter:
                    continue
                out.append(attrs)
    return out


def download_national_tract_rows(
    *,
    url: str | None = None,
    timeout: float = 600.0,
    stcofips_filter: frozenset[str] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Download + parse national NRI tracts CSV zip. Returns (sha256, rows).

    When ``stcofips_filter`` is set, only matching counties are kept (streamed from
    a temp file so the ~600MB+ zip does not expand fully into RAM). Unfiltered
    full-nation parses are cached in-process for multi-batch reuse.
    """
    target = url or bulk_url()
    cache_key = target if stcofips_filter is None else None
    if cache_key and cache_key in _BULK_CACHE:
        sha, rows = _BULK_CACHE[cache_key]
        logger.info(
            "FEMA bulk cache hit url=%s sha256=%s rows=%s", target, sha[:12], len(rows)
        )
        return sha, rows

    logger.info(
        "FEMA bulk download starting url=%s filter_counties=%s",
        target,
        len(stcofips_filter) if stcofips_filter is not None else "all",
    )
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream("GET", target) as response:
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                for chunk in response.iter_bytes(1024 * 1024):
                    tmp.write(chunk)

    try:
        zip_size = tmp_path.stat().st_size
        if zip_size < 1000:
            raise RuntimeError(
                f"FEMA NRI bulk download too small ({zip_size} bytes) from {target}"
            )
        with tmp_path.open("rb") as fh:
            magic = fh.read(2)
        if magic != b"PK":
            raise RuntimeError(
                f"FEMA NRI bulk response is not a zip "
                f"(magic={magic!r} size={zip_size} url={target})"
            )

        sha = hashlib.sha256()
        with tmp_path.open("rb") as fh:
            while True:
                block = fh.read(1024 * 1024)
                if not block:
                    break
                sha.update(block)
        sha_hex = sha.hexdigest()

        rows = _stream_parse_zip_path(tmp_path, stcofips_filter=stcofips_filter)
        if not rows:
            raise RuntimeError(
                f"FEMA NRI bulk CSV parsed to 0 rows "
                f"(sha256={sha_hex[:12]} url={target} "
                f"filter={len(stcofips_filter) if stcofips_filter else 'all'})"
            )

        if cache_key:
            _BULK_CACHE[cache_key] = (sha_hex, rows)
        logger.info(
            "FEMA bulk ready sha256=%s zip_bytes=%s rows=%s filter=%s",
            sha_hex[:12],
            zip_size,
            len(rows),
            len(stcofips_filter) if stcofips_filter is not None else "all",
        )
        return sha_hex, rows
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def query_county_features(
    stcofips: str,
    *,
    out_fields: str,
    timeout: float = 120.0,
) -> list[dict[str, Any]]:
    """Return raw ArcGIS feature attribute dicts for one county (STCOFIPS)."""
    where = f"STCOFIPS='{stcofips}'"
    offset = 0
    features: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout) as client:
        while True:
            response = client.get(
                FEMA_NRI_LAYER,
                params={
                    "where": where,
                    "outFields": out_fields,
                    "returnGeometry": "false",
                    "f": "json",
                    "resultRecordCount": PAGE_SIZE,
                    "resultOffset": offset,
                },
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(
                    f"FEMA NRI query failed for {stcofips}: {payload['error']}"
                )
            batch = payload.get("features") or []
            if not batch:
                break
            for feat in batch:
                attrs = feat.get("attributes") if isinstance(feat, dict) else None
                if isinstance(attrs, dict):
                    features.append(attrs)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            logger.debug(
                "FEMA county %s: fetched offset %s (%s features)",
                stcofips,
                offset,
                len(batch),
            )
    return features
