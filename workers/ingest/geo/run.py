"""County registry ingest from Census TIGER county files."""

from __future__ import annotations

import logging
import os
import sys

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values

from ingest.base import BaseIngestionWorker
from ingest.checkpoints import counties_with_geo, log_skip
from ingest.geo.jurisdictions import INCLUDED_STATE_FIPS, STATE_FIPS_TO_ABBR
from ingest.geo.scope import parse_state_batch, require_national_state_batch, resolve_ingest_scope

logger = logging.getLogger("geo")

TIGER_COUNTY_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2023/COUNTY/tl_2023_us_county.zip"
)


def states_to_load() -> frozenset[str]:
    if (os.getenv("INGEST_GEO_LOAD_ALL") or "").strip() == "1":
        return INCLUDED_STATE_FIPS
    scope = resolve_ingest_scope()
    if scope == "national":
        return require_national_state_batch()
    batch = parse_state_batch(os.getenv("INGEST_STATE_BATCH"))
    if batch:
        unknown = sorted(batch - INCLUDED_STATE_FIPS)
        if unknown:
            raise RuntimeError(f"INGEST_STATE_BATCH invalid for geo load: {unknown}")
        return batch
    from ingest.fixtures.canonical_addresses import fixture_state_fips

    return fixture_state_fips()


class GeoCountyWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("geo")
        self._gdf: gpd.GeoDataFrame | None = None
        self._states: frozenset[str] = frozenset()
        self._rows: list[tuple] = []

    def fetch(self) -> None:
        self._states = states_to_load()
        self.logger.info(
            "Fetching national TIGER counties; filter states=%s",
            sorted(self._states),
        )
        self._gdf = gpd.read_file(TIGER_COUNTY_URL).to_crs("EPSG:4326")
        self.logger.info("Downloaded %d county polygons", len(self._gdf))

    def transform(self) -> None:
        raw: list[tuple] = []
        if self._gdf is None:
            self._rows = []
            return
        for _, row in self._gdf.iterrows():
            state_fp = str(row.get("STATEFP") or "").zfill(2)
            if state_fp not in self._states:
                continue
            county_fp = str(row.get("COUNTYFP") or "").zfill(3)
            if len(county_fp) != 3:
                continue
            cf = f"{state_fp}{county_fp}"
            name = str(row.get("NAME") or row.get("NAMELSAD") or "")
            abbr = STATE_FIPS_TO_ABBR.get(state_fp, "")
            lat = row.get("INTPTLAT")
            lon = row.get("INTPTLON")
            try:
                lat_f = float(lat) if lat is not None else None
                lon_f = float(lon) if lon is not None else None
            except (TypeError, ValueError):
                lat_f, lon_f = None, None
            if lat_f is None or lon_f is None:
                geom = row.geometry
                if geom is not None and not geom.is_empty:
                    c = geom.centroid
                    lat_f, lon_f = float(c.y), float(c.x)
            if lat_f is None or lon_f is None:
                continue
            raw.append((cf, state_fp, name, abbr, lat_f, lon_f, "tiger2023"))

        all_cf = [r[0] for r in raw]
        done = counties_with_geo(self.database_url, all_cf) if all_cf else set()
        self._rows = [r for r in raw if r[0] not in done]
        log_skip(self.logger, "geo", len(done & set(all_cf)), len(self._rows))

    def load(self) -> None:
        if not self._rows:
            self.logger.info("No new geo_counties rows to upsert")
            return
        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO geo_counties (
                        county_fips, state_fips, county_name, state_abbr,
                        centroid_lat, centroid_lon, source, updated_at
                    ) VALUES %s
                    ON CONFLICT (county_fips) DO UPDATE SET
                        state_fips = EXCLUDED.state_fips,
                        county_name = EXCLUDED.county_name,
                        state_abbr = EXCLUDED.state_abbr,
                        centroid_lat = EXCLUDED.centroid_lat,
                        centroid_lon = EXCLUDED.centroid_lon,
                        source = EXCLUDED.source,
                        updated_at = NOW()
                    """,
                    self._rows,
                    template="(%s, %s, %s, %s, %s, %s, %s, NOW())",
                    page_size=500,
                )
            conn.commit()
            self.logger.info("Upserted %d geo_counties rows", len(self._rows))
        finally:
            conn.close()


def main() -> int:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    try:
        GeoCountyWorker().run()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
