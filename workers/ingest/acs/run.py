"""Census ACS 5-year tract + state ingest — fixture counties / states."""

from __future__ import annotations

import logging
import sys

import psycopg2

from ingest.acs.client import (
    DEFAULT_ACS_YEAR,
    fetch_county_tract_rows,
    fetch_state_rows,
    tabular_to_dicts,
)
from ingest.acs.transform import transform_acs_rows, transform_acs_state_rows
from ingest.base import BaseIngestionWorker
from ingest.checkpoints import counties_with_acs, log_skip
from ingest.force import force_enabled
from ingest.geo.scope import active_county_fips
from ingest.status_pulse import StatusPulse

logger = logging.getLogger("acs")

UPSERT_SQL = """
INSERT INTO acs_indicators (
    geoid, geo_level, median_hh_income, labor_force, employed, unemployed,
    total_population, acs_year, payload
) VALUES (
    %(geoid)s, %(geo_level)s, %(median_hh_income)s, %(labor_force)s,
    %(employed)s, %(unemployed)s, %(total_population)s, %(acs_year)s, %(payload)s
)
ON CONFLICT (geoid, geo_level, acs_year) DO UPDATE SET
    median_hh_income = EXCLUDED.median_hh_income,
    labor_force = EXCLUDED.labor_force,
    employed = EXCLUDED.employed,
    unemployed = EXCLUDED.unemployed,
    total_population = EXCLUDED.total_population,
    payload = EXCLUDED.payload,
    updated_at = NOW()
"""


class AcsTractWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("acs")
        self._raw_rows: list[dict] = []
        self._raw_state_rows: list[dict] = []
        self._records: list[dict] = []
        self._acs_year = DEFAULT_ACS_YEAR

    def fetch(self) -> None:
        self._raw_rows = []
        self._raw_state_rows = []
        allow = active_county_fips(database_url=self.database_url)
        done = (
            set()
            if force_enabled()
            else counties_with_acs(self.database_url, sorted(allow))
        )
        pending = sorted(allow - done)
        log_skip(self.logger, "acs", len(done), len(pending))
        pulse = StatusPulse(self.database_url)
        for county_fips in pending:
            state_fips = county_fips[:2]
            county = county_fips[2:]
            self.logger.info(
                "Fetching ACS tracts for county %s (year=%s)…",
                county_fips,
                self._acs_year,
            )
            tabular = fetch_county_tract_rows(
                state_fips,
                county,
                acs_year=self._acs_year,
            )
            rows = tabular_to_dicts(tabular)
            self._raw_rows.extend(rows)
            self.logger.info("  Got %s tract rows", len(rows))
            pulse.tick()

        # Always refresh state population for states covered by active counties
        # (needed for per-resident safety normalization).
        states = sorted({c[:2] for c in allow})
        for state_fips in states:
            self.logger.info(
                "Fetching ACS state population for %s (year=%s)…",
                state_fips,
                self._acs_year,
            )
            try:
                tabular = fetch_state_rows(state_fips, acs_year=self._acs_year)
                self._raw_state_rows.extend(tabular_to_dicts(tabular))
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("ACS state %s failed: %s", state_fips, exc)
            pulse.tick()
        pulse.flush()

    def transform(self) -> None:
        acs_year_label = str(self._acs_year)
        self._records = transform_acs_rows(self._raw_rows, acs_year=acs_year_label)
        self._records.extend(
            transform_acs_state_rows(self._raw_state_rows, acs_year=acs_year_label)
        )
        self.logger.info("Prepared %s acs_indicators rows", len(self._records))

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No ACS records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                for record in self._records:
                    cur.execute(UPSERT_SQL, record)
            conn.commit()
            self.logger.info("Upserted %s acs_indicators rows", len(self._records))
        finally:
            conn.close()


def main() -> int:
    try:
        AcsTractWorker().run()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
