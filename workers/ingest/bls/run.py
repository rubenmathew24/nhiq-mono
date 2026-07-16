"""BLS LAUS county unemployment ingest — fixture counties only."""

from __future__ import annotations

import logging
import sys

import psycopg2

from ingest.base import BaseIngestionWorker
from ingest.bls.client import fetch_laus_series, laus_series_id
from ingest.bls.transform import transform_laus_series
from ingest.checkpoints import counties_with_bls, log_skip
from ingest.geo.scope import active_county_fips

logger = logging.getLogger("bls")

UPSERT_SQL = """
INSERT INTO bls_laus_county (
    county_fips, series_id, period, unemployment_rate
) VALUES (
    %(county_fips)s, %(series_id)s, %(period)s, %(unemployment_rate)s
)
ON CONFLICT (county_fips, series_id, period) DO UPDATE SET
    unemployment_rate = EXCLUDED.unemployment_rate,
    fetched_at = NOW()
"""

# BLS allows up to 50 series per request.
BATCH_SIZE = 50


class BlsLausWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("bls")
        self._records: list[dict] = []

    def fetch(self) -> None:
        allow = active_county_fips(database_url=self.database_url)
        done = counties_with_bls(self.database_url, sorted(allow))
        counties = sorted(allow - done)
        log_skip(self.logger, "bls", len(done), len(counties))
        series_map = {laus_series_id(cf): cf for cf in counties}
        all_series = list(series_map.keys())
        observations_by_series: dict[str, list] = {}

        for offset in range(0, len(all_series), BATCH_SIZE):
            batch = all_series[offset : offset + BATCH_SIZE]
            self.logger.info("Fetching BLS LAUS batch (%s series)…", len(batch))
            observations_by_series.update(fetch_laus_series(batch))

        self._records = []
        for series_id, county_fips in series_map.items():
            obs = observations_by_series.get(series_id) or []
            row = transform_laus_series(county_fips, series_id, obs)
            if row:
                self._records.append(row)
                self.logger.info(
                    "County %s latest unemployment=%.2f%% (%s)",
                    county_fips,
                    row["unemployment_rate"],
                    row["period"],
                )
            else:
                self.logger.warning("No LAUS data for county %s", county_fips)

    def transform(self) -> None:
        # Fetch+transform combined — records ready after fetch.
        self.logger.info("Prepared %s bls_laus_county rows", len(self._records))

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No BLS LAUS records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                for record in self._records:
                    cur.execute(UPSERT_SQL, record)
            conn.commit()
            self.logger.info("Upserted %s bls_laus_county rows", len(self._records))
        finally:
            conn.close()


def main() -> int:
    try:
        BlsLausWorker().run()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
