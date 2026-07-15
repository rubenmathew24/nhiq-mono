"""CMS hospital ingest worker — fixture states only."""

from __future__ import annotations

import logging
import sys

import psycopg2

from ingest.base import BaseIngestionWorker
from ingest.cms.client import iter_hospital_pages
from ingest.cms.geocode import fill_missing_coordinates
from ingest.cms.transform import transform_hospital_records
from ingest.fixtures.canonical_addresses import fixture_state_abbrs

logger = logging.getLogger("cms")

UPSERT_SQL = """
INSERT INTO hospitals (
    cms_provider_id, name, address, city, state, zip, county_name, phone,
    hospital_type, emergency_services, star_rating, latitude, longitude, geometry
) VALUES (
    %(cms_provider_id)s, %(name)s, %(address)s, %(city)s,
    %(state)s, %(zip)s, %(county_name)s, %(phone)s,
    %(hospital_type)s, %(emergency_services)s, %(star_rating)s,
    %(latitude)s, %(longitude)s,
    CASE
      WHEN %(latitude)s IS NOT NULL AND %(longitude)s IS NOT NULL
      THEN ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326)
      ELSE NULL
    END
)
ON CONFLICT (cms_provider_id) DO UPDATE SET
    name = EXCLUDED.name,
    address = EXCLUDED.address,
    city = EXCLUDED.city,
    state = EXCLUDED.state,
    zip = EXCLUDED.zip,
    county_name = EXCLUDED.county_name,
    phone = EXCLUDED.phone,
    hospital_type = EXCLUDED.hospital_type,
    emergency_services = EXCLUDED.emergency_services,
    star_rating = EXCLUDED.star_rating,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    geometry = EXCLUDED.geometry,
    updated_at = NOW()
"""


class CmsHospitalWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("cms")
        self._raw_pages: list[list[dict]] = []
        self._records: list[dict] = []

    def fetch(self) -> None:
        self._raw_pages = []
        page = 0
        for raw_page in iter_hospital_pages():
            page += 1
            self._raw_pages.append(raw_page)
            self.logger.info("CMS page %s: fetched %s raw rows", page, len(raw_page))

    def transform(self) -> None:
        states = fixture_state_abbrs()
        self.logger.info("Filtering to fixture states=%s", sorted(states))
        combined: list[dict] = []
        for raw_page in self._raw_pages:
            combined.extend(
                transform_hospital_records(raw_page, state_allowlist=states)
            )
        self._records = fill_missing_coordinates(combined)
        self.logger.info("Kept %s hospitals after state filter", len(self._records))

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No hospital records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                for r in self._records:
                    cur.execute(UPSERT_SQL, r)
            conn.commit()
            self.logger.info("Upserted %s hospitals", len(self._records))
        finally:
            conn.close()


def main() -> None:
    CmsHospitalWorker().run()


if __name__ == "__main__":
    main()
