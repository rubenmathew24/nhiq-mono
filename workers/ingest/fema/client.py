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

# Official NRI "All Census tracts" Table Format zip (hazards.fema.gov static path).
# Override with FEMA_NRI_BULK_URL if FEMA relocates the file.
DEFAULT_FEMA_NRI_BULK_URL = (
    "https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload/"
    "NRI_Table_CensusTracts/NRI_Table_CensusTracts.zip"
)

ROOT_FIELDS = (
    "STCOFIPS",
    "TRACT",
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


def _parse_nri_csv_bytes(data: bytes) -> list[dict[str, Any]]:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    out: list[dict[str, Any]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        attrs = _normalize_csv_row({str(k): ("" if v is None else str(v)) for k, v in row.items()})
        if attrs.get("STCOFIPS") and attrs.get("TRACT"):
            out.append(attrs)
    return out


def _extract_csv_from_zip(zip_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise RuntimeError("FEMA NRI bulk zip contains no CSV files")
        # Prefer a tracts-named CSV when multiple exist.
        preferred = next(
            (n for n in names if "tract" in n.lower()),
            names[0],
        )
        logger.info("FEMA bulk zip entry=%s (%s csv files)", preferred, len(names))
        return zf.read(preferred)


def download_national_tract_rows(
    *,
    url: str | None = None,
    timeout: float = 600.0,
) -> tuple[str, list[dict[str, Any]]]:
    """Download + parse national NRI tracts CSV zip. Returns (sha256, rows).

    Cached in-process so multi-state batches reuse one download.
    """
    target = url or bulk_url()
    if target in _BULK_CACHE:
        sha, rows = _BULK_CACHE[target]
        logger.info(
            "FEMA bulk cache hit url=%s sha256=%s rows=%s", target, sha[:12], len(rows)
        )
        return sha, rows

    logger.info("FEMA bulk download starting url=%s", target)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(target)
        response.raise_for_status()
        zip_bytes = response.content

    if len(zip_bytes) < 1000:
        raise RuntimeError(
            f"FEMA NRI bulk download too small ({len(zip_bytes)} bytes) from {target}"
        )

    sha = hashlib.sha256(zip_bytes).hexdigest()
    csv_bytes = _extract_csv_from_zip(zip_bytes)
    rows = _parse_nri_csv_bytes(csv_bytes)
    if not rows:
        raise RuntimeError(
            f"FEMA NRI bulk CSV parsed to 0 rows (sha256={sha[:12]} url={target})"
        )

    _BULK_CACHE[target] = (sha, rows)
    logger.info(
        "FEMA bulk ready sha256=%s bytes=%s rows=%s",
        sha[:12],
        len(zip_bytes),
        len(rows),
    )
    # Optional: keep a temp copy for ops debugging (deleted with process).
    try:
        cache_dir = Path(tempfile.gettempdir()) / "niq_fema_nri"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"{sha[:16]}.meta").write_text(
            f"url={target}\nrows={len(rows)}\n", encoding="utf-8"
        )
    except OSError:
        pass
    return sha, rows


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
