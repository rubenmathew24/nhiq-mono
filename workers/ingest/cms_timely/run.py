"""CMS Timely & Effective Care ingestion — smoke / metro_10 / national (batch)."""

from __future__ import annotations

import logging
import sys

import psycopg2

from ingest.base import BaseIngestionWorker
from ingest.cms_timely.client import (
    discover_timely_dataset_ids,
    fetch_benchmark_by_measure,
    iter_dataset_pages,
)
from ingest.cms_timely.transform import transform_measure_rows
from ingest.geo.scope import active_state_abbrs

logger = logging.getLogger("cms_timely")

UPSERT_SQL = """
INSERT INTO hospital_timely_measures (
    cms_provider_id, measure_id, measure_name,
    score_value, score_text, sample, footnote,
    state_score, national_score, start_date, end_date, data_vintage
) VALUES (
    %(cms_provider_id)s, %(measure_id)s, %(measure_name)s,
    %(score_value)s, %(score_text)s, %(sample)s, %(footnote)s,
    %(state_score)s, %(national_score)s, %(start_date)s, %(end_date)s,
    %(data_vintage)s
)
ON CONFLICT (cms_provider_id, measure_id, data_vintage) DO UPDATE SET
    measure_name = EXCLUDED.measure_name,
    score_value = EXCLUDED.score_value,
    score_text = EXCLUDED.score_text,
    sample = EXCLUDED.sample,
    footnote = EXCLUDED.footnote,
    state_score = EXCLUDED.state_score,
    national_score = EXCLUDED.national_score,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date,
    updated_at = NOW()
"""


def _load_hospital_provider_ids(database_url: str, states: frozenset[str]) -> frozenset[str]:
    if not states:
        return frozenset()
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT cms_provider_id
                FROM hospitals
                WHERE state = ANY(%s)
                """,
                (sorted(states),),
            )
            return frozenset(str(r[0]) for r in cur.fetchall() if r and r[0])
    finally:
        conn.close()


class CmsTimelyWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("cms_timely")
        self._raw_pages: list[list[dict]] = []
        self._records: list[dict] = []

    def fetch(self) -> None:
        # active_state_abbrs → active_county_fips (national requires INGEST_STATE_BATCH)
        self._states = active_state_abbrs(database_url=self.database_url)
        self._providers = _load_hospital_provider_ids(self.database_url, self._states)
        self.logger.info(
            "Active states=%s hospitals=%d",
            sorted(self._states),
            len(self._providers),
        )

        dataset_ids = discover_timely_dataset_ids()
        hospital_id = dataset_ids["hospital"]
        assert hospital_id

        self._state_benchmarks = fetch_benchmark_by_measure(dataset_ids.get("state"))
        self._national_benchmarks = fetch_benchmark_by_measure(
            dataset_ids.get("national")
        )
        self.logger.info(
            "Benchmark rows state=%d national=%d",
            len(self._state_benchmarks),
            len(self._national_benchmarks),
        )

        self._raw_pages = []
        page = 0
        for raw_page in iter_dataset_pages(hospital_id):
            page += 1
            self._raw_pages.append(raw_page)
            self.logger.info(
                "CMS Timely page %s: fetched %s raw rows", page, len(raw_page)
            )

    def transform(self) -> None:
        if not self._providers:
            self.logger.warning("No hospitals in scope; skipping CMS Timely transform")
            self._records = []
            return
        combined: list[dict] = []
        for raw_page in self._raw_pages:
            combined.extend(
                transform_measure_rows(
                    raw_page,
                    provider_allowlist=self._providers,
                    state_benchmarks=self._state_benchmarks,
                    national_benchmarks=self._national_benchmarks,
                )
            )
        self._records = combined
        self.logger.info("Kept %s timely measure rows after filter", len(self._records))

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No CMS Timely records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                for record in self._records:
                    cur.execute(UPSERT_SQL, record)
            conn.commit()
            self.logger.info("Upserted %s hospital timely measures", len(self._records))
        finally:
            conn.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    try:
        CmsTimelyWorker().run()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
