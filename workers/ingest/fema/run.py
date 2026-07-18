"""FEMA NRI tract ingestion — smoke / metro_10 / national (batch) counties."""

from __future__ import annotations

import json
import logging
import sys

import psycopg2
from psycopg2.extras import execute_values

from ingest.base import BaseIngestionWorker
from ingest.checkpoints import geoids_with_fema_nri, log_skip
from ingest.fema.client import (
    build_out_fields,
    download_national_tract_rows,
    query_county_features,
    use_bulk_files,
)
from ingest.fema.transform import FEMA_NRI_HAZARD_PREFIXES, transform_tract_features
from ingest.force import force_enabled
from ingest.geo.scope import active_county_fips, resolve_ingest_scope

logger = logging.getLogger("fema")


def _load_tract_geoids_by_county(
    database_url: str, counties: frozenset[str]
) -> dict[str, frozenset[str]]:
    if not counties:
        return {}
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT geoid, (state_fips || county_fips) AS county_fips
                FROM census_tracts
                WHERE (state_fips || county_fips) = ANY(%s)
                """,
                (sorted(counties),),
            )
            out: dict[str, set[str]] = {}
            for geoid, county in cur.fetchall():
                if not geoid or not county:
                    continue
                out.setdefault(str(county), set()).add(str(geoid))
            return {k: frozenset(v) for k, v in out.items()}
    finally:
        conn.close()


class FemaNriWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("fema")
        self._raw_by_county: dict[str, list[dict]] = {}
        self._raw_bulk: list[dict] = []
        self._records: list[dict] = []
        self._use_bulk = False

    def fetch(self) -> None:
        # active_county_fips handles smoke / metro_10 / national (+ INGEST_STATE_BATCH)
        self._allow = active_county_fips(database_url=self.database_url)
        tract_map = _load_tract_geoids_by_county(self.database_url, self._allow)
        pending_counties: list[str] = []
        pending_geoids: set[str] = set()

        for county in sorted(self._allow):
            geoids = tract_map.get(county, frozenset())
            if not geoids:
                self.logger.warning(
                    "County %s has no census_tracts rows; skipping FEMA fetch",
                    county,
                )
                continue
            if force_enabled():
                pending_counties.append(county)
                pending_geoids.update(geoids)
                continue
            # One checkpoint query for all pending geoids after the loop would
            # be ideal; we still need per-county remaining sets. Batch: collect
            # all geoids first, then one DB call.
            pending_counties.append(county)
            pending_geoids.update(geoids)

        if not force_enabled() and pending_geoids:
            done = geoids_with_fema_nri(self.database_url, sorted(pending_geoids))
            remaining = pending_geoids - done
            if remaining != pending_geoids:
                # Rebuild pending counties from remaining geoids only.
                pending_counties = []
                pending_geoids = remaining
                for county in sorted(self._allow):
                    geoids = tract_map.get(county, frozenset())
                    if geoids & remaining:
                        pending_counties.append(county)

        skipped = len(self._allow) - len(pending_counties)
        log_skip(self.logger, "fema", skipped, len(pending_counties))
        self._pending_geoids = frozenset(pending_geoids)
        self._raw_by_county = {}
        self._raw_bulk = []
        self._use_bulk = False

        if not pending_counties:
            return

        scope = resolve_ingest_scope()
        prefer_bulk = use_bulk_files() and scope == "national"
        if prefer_bulk:
            try:
                sha, rows = download_national_tract_rows()
                # Filter to in-scope pending counties (STCOFIPS) before transform.
                pending_stco = set(pending_counties)
                filtered = [
                    r
                    for r in rows
                    if str(r.get("STCOFIPS") or "") in pending_stco
                ]
                self._raw_bulk = filtered
                self._use_bulk = True
                self.logger.info(
                    "FEMA bulk path sha256=%s national_rows=%s in_scope=%s",
                    sha[:12],
                    len(rows),
                    len(filtered),
                )
                return
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "FEMA bulk download failed (fail-closed for national): %s", exc
                )
                raise

        out_fields = build_out_fields(FEMA_NRI_HAZARD_PREFIXES)
        for county in pending_counties:
            try:
                raw = query_county_features(county, out_fields=out_fields)
                self._raw_by_county[county] = raw
                self.logger.info(
                    "County %s: fetched %d FEMA NRI features",
                    county,
                    len(raw),
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.error("County %s fetch failed: %s", county, exc)
                self._raw_by_county[county] = []

    def transform(self) -> None:
        pending = getattr(self, "_pending_geoids", frozenset())
        if self._use_bulk:
            self._records = transform_tract_features(
                self._raw_bulk, known_geoids=pending
            )
            self.logger.info(
                "FEMA bulk transform: %d tract records", len(self._records)
            )
            return

        combined: list[dict] = []
        for county, raw in self._raw_by_county.items():
            records = transform_tract_features(raw, known_geoids=pending)
            self.logger.info(
                "County %s: %d tract records after transform",
                county,
                len(records),
            )
            combined.extend(records)
        self._records = combined

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No FEMA NRI records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                rows = [
                    (
                        r["geoid"],
                        r["state_fips"],
                        r["county_fips"],
                        r["risk_score"],
                        r["risk_rating"],
                        r["eal_score"],
                        r["sovi_score"],
                        r["resl_score"],
                        json.dumps(r["hazards"]),
                        r["data_vintage"],
                        json.dumps(r["payload"]),
                    )
                    for r in self._records
                ]
                execute_values(
                    cur,
                    """
                    INSERT INTO fema_nri_tracts (
                        geoid, state_fips, county_fips,
                        risk_score, risk_rating, eal_score, sovi_score, resl_score,
                        hazards, data_vintage, payload
                    ) VALUES %s
                    ON CONFLICT (geoid) DO UPDATE SET
                        state_fips = EXCLUDED.state_fips,
                        county_fips = EXCLUDED.county_fips,
                        risk_score = EXCLUDED.risk_score,
                        risk_rating = EXCLUDED.risk_rating,
                        eal_score = EXCLUDED.eal_score,
                        sovi_score = EXCLUDED.sovi_score,
                        resl_score = EXCLUDED.resl_score,
                        hazards = EXCLUDED.hazards,
                        data_vintage = EXCLUDED.data_vintage,
                        payload = EXCLUDED.payload,
                        updated_at = NOW()
                    """,
                    rows,
                    template=(
                        "(%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)"
                    ),
                    page_size=500,
                )
            conn.commit()
            self.logger.info("Upserted %d FEMA NRI tract rows", len(rows))
        finally:
            conn.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    try:
        FemaNriWorker().run()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
