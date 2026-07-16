"""Census TIGER tract ingestion — smoke / metro / national batch counties."""

from __future__ import annotations

import logging
import sys

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values
from shapely.geometry import MultiPolygon
from shapely import wkt

from ingest.base import BaseIngestionWorker
from ingest.checkpoints import counties_with_census_tracts, log_skip
from ingest.census.transform import filter_tract_records
from ingest.geo.scope import active_county_fips

logger = logging.getLogger("census")

TIGER_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_{state_fips}_tract.zip"
)


def _as_multipolygon(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "MultiPolygon":
        return geom
    return None


class CensusTractWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("census")
        self._frames: list[gpd.GeoDataFrame] = []
        self._records: list[dict] = []
        self._allow: frozenset[str] = frozenset()

    def fetch(self) -> None:
        self._allow = active_county_fips(database_url=self.database_url)
        done = counties_with_census_tracts(self.database_url, sorted(self._allow))
        pending_counties = self._allow - done
        log_skip(self.logger, "census", len(done), len(pending_counties))
        pending_states = frozenset(cf[:2] for cf in pending_counties)
        # Still need state downloads that have any pending county
        states = pending_states or frozenset()
        self._frames = []
        self._pending_counties = pending_counties
        for state_fips in sorted(states):
            url = TIGER_URL.format(state_fips=state_fips)
            self.logger.info("Fetching tracts for state %s …", state_fips)
            try:
                gdf = gpd.read_file(url)
                gdf = gdf.to_crs("EPSG:4326")
                self._frames.append(gdf)
                self.logger.info("  Downloaded %d tracts for %s", len(gdf), state_fips)
            except Exception as exc:  # noqa: BLE001 — continue other states
                self.logger.error("  Error for state %s: %s", state_fips, exc)

    def transform(self) -> None:
        raw: list[dict] = []
        for gdf in self._frames:
            for _, row in gdf.iterrows():
                raw.append(
                    {
                        "GEOID": row.get("GEOID"),
                        "STATEFP": row.get("STATEFP"),
                        "COUNTYFP": row.get("COUNTYFP"),
                        "TRACTCE": row.get("TRACTCE"),
                        "geometry": row.geometry,
                    }
                )
        # Only pending counties (checkpoint)
        allow = getattr(self, "_pending_counties", None) or self._allow
        self._records = filter_tract_records(raw, county_allowlist=allow)
        self.logger.info(
            "County filter kept %d / %d tracts",
            len(self._records),
            len(raw),
        )

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No tract records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                rows = []
                for r in self._records:
                    mp = _as_multipolygon(r["geometry"])
                    if mp is None:
                        continue
                    rows.append(
                        (
                            r["geoid"],
                            r["state_fips"],
                            r["county_fips"],
                            r["tract_fips"],
                            wkt.dumps(mp),
                        )
                    )
                execute_values(
                    cur,
                    """
                    INSERT INTO census_tracts
                        (geoid, state_fips, county_fips, tract_fips, geometry)
                    VALUES %s
                    ON CONFLICT (geoid) DO UPDATE SET
                        state_fips = EXCLUDED.state_fips,
                        county_fips = EXCLUDED.county_fips,
                        tract_fips = EXCLUDED.tract_fips,
                        geometry = EXCLUDED.geometry
                    """,
                    rows,
                    template="(%s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))",
                    page_size=500,
                )
            conn.commit()
            self.logger.info("Upserted %d census tracts", len(rows))
        finally:
            conn.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    try:
        CensusTractWorker().run()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
