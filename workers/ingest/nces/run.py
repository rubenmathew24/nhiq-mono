"""NCES EDGE school ingest — fixture counties only."""

from __future__ import annotations

import logging
import sys

import psycopg2

from ingest.base import BaseIngestionWorker
from ingest.checkpoints import counties_with_nces, log_skip
from ingest.geo.scope import active_county_fips
from ingest.nces.client import iter_state_school_pages
from ingest.nces.transform import transform_nces_features

logger = logging.getLogger("nces")

UPSERT_SQL = """
INSERT INTO schools_nces (
    ncessch, leaid, name, state_fips, county_fips, locale,
    latitude, longitude, geometry
) VALUES (
    %(ncessch)s, %(leaid)s, %(name)s, %(state_fips)s, %(county_fips)s,
    %(locale)s, %(latitude)s, %(longitude)s,
    ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326)
)
ON CONFLICT (ncessch) DO UPDATE SET
    leaid = EXCLUDED.leaid,
    name = EXCLUDED.name,
    state_fips = EXCLUDED.state_fips,
    county_fips = EXCLUDED.county_fips,
    locale = EXCLUDED.locale,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    geometry = EXCLUDED.geometry,
    updated_at = NOW()
"""


class NcesSchoolWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("nces")
        self._raw_features: list[dict] = []
        self._records: list[dict] = []

    def fetch(self) -> None:
        self._raw_features = []
        self._allow = active_county_fips(database_url=self.database_url)
        done = counties_with_nces(self.database_url, sorted(self._allow))
        pending = self._allow - done
        log_skip(self.logger, "nces", len(done), len(pending))
        self._pending = pending
        states = frozenset(cf[:2] for cf in pending)
        for state_fips in sorted(states):
            page = 0
            for raw_page in iter_state_school_pages(state_fips):
                page += 1
                self._raw_features.extend(raw_page)
                self.logger.info(
                    "NCES state %s page %s: fetched %s schools",
                    state_fips,
                    page,
                    len(raw_page),
                )

    def transform(self) -> None:
        allow = getattr(self, "_pending", None) or getattr(self, "_allow", frozenset())
        self._records = transform_nces_features(
            self._raw_features, county_allowlist=allow
        )
        self.logger.info(
            "Fixture-county filter kept %s / %s NCES schools",
            len(self._records),
            len(self._raw_features),
        )

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No NCES school records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                for record in self._records:
                    cur.execute(UPSERT_SQL, record)
            conn.commit()
            self.logger.info("Upserted %s schools_nces rows", len(self._records))
        finally:
            conn.close()


def main() -> int:
    try:
        NcesSchoolWorker().run()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
