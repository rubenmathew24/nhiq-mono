"""Urban Institute CCD directory ingest — join to fixture NCES schools via LEAID."""

from __future__ import annotations

import logging
import sys

import psycopg2

from ingest.base import BaseIngestionWorker
from ingest.status_pulse import StatusPulse
from ingest.urban.client import DEFAULT_YEAR, fetch_directory_for_leaid
from ingest.urban.transform import transform_urban_records

logger = logging.getLogger("urban")

UPSERT_SQL = """
INSERT INTO schools_urban (
    ncessch, year, enrollment, teachers_fte, school_level, school_type,
    school_status, charter, magnet, virtual, payload
) VALUES (
    %(ncessch)s, %(year)s, %(enrollment)s, %(teachers_fte)s,
    %(school_level)s, %(school_type)s, %(school_status)s,
    %(charter)s, %(magnet)s, %(virtual)s, %(payload)s
)
ON CONFLICT (ncessch, year) DO UPDATE SET
    enrollment = EXCLUDED.enrollment,
    teachers_fte = EXCLUDED.teachers_fte,
    school_level = EXCLUDED.school_level,
    school_type = EXCLUDED.school_type,
    school_status = EXCLUDED.school_status,
    charter = EXCLUDED.charter,
    magnet = EXCLUDED.magnet,
    virtual = EXCLUDED.virtual,
    payload = EXCLUDED.payload,
    updated_at = NOW()
"""


class UrbanSchoolWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("urban")
        self._raw_rows: list[dict] = []
        self._records: list[dict] = []
        self._ncessch_allow: frozenset[str] = frozenset()
        self._year = DEFAULT_YEAR

    def fetch(self) -> None:
        self._raw_rows = []
        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.schools_nces') IS NOT NULL")
                if not cur.fetchone()[0]:
                    raise RuntimeError(
                        "schools_nces is missing — run worker-nces before worker-urban"
                    )
                cur.execute(
                    """
                    SELECT DISTINCT leaid, ncessch
                    FROM schools_nces
                    WHERE leaid IS NOT NULL AND ncessch IS NOT NULL
                    """
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        if not rows:
            raise RuntimeError(
                "schools_nces is empty — run worker-nces before worker-urban"
            )

        leaids = sorted({str(r[0]) for r in rows if r[0]})
        self._ncessch_allow = frozenset(str(r[1])[:12] for r in rows if r[1])
        self.logger.info(
            "Urban fetch for %s LEAIDs covering %s NCES schools",
            len(leaids),
            len(self._ncessch_allow),
        )

        pulse = StatusPulse(self.database_url)
        for i, leaid in enumerate(leaids, start=1):
            try:
                page_rows = fetch_directory_for_leaid(leaid, year=self._year)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning("Urban LEAID %s failed: %s", leaid, exc)
                continue
            self._raw_rows.extend(page_rows)
            pulse.tick()
            if i % 25 == 0 or i == len(leaids):
                self.logger.info(
                    "Urban LEAID progress %s/%s (raw rows=%s)",
                    i,
                    len(leaids),
                    len(self._raw_rows),
                )
        pulse.flush()

    def transform(self) -> None:
        self._records = transform_urban_records(
            self._raw_rows,
            year=self._year,
            ncessch_allowlist=self._ncessch_allow,
        )
        self.logger.info(
            "Urban kept %s / %s raw rows for NCES allowlist (year=%s)",
            len(self._records),
            len(self._raw_rows),
            self._year,
        )

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No Urban school records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                for record in self._records:
                    cur.execute(UPSERT_SQL, record)
            conn.commit()
            self.logger.info("Upserted %s schools_urban rows", len(self._records))
        finally:
            conn.close()


def main() -> int:
    try:
        UrbanSchoolWorker().run()
    except Exception as exc:  # noqa: BLE001
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
