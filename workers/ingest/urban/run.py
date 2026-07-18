"""Urban Institute CCD directory ingest — join to NCES schools via state fips."""

from __future__ import annotations

import logging
import sys

import psycopg2

from ingest.base import BaseIngestionWorker
from ingest.checkpoints import log_skip
from ingest.force import force_enabled
from ingest.geo.scope import active_county_fips
from ingest.status_pulse import StatusPulse
from ingest.urban.client import DEFAULT_YEAR, fetch_directory_for_states
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
        allow_counties = active_county_fips(database_url=self.database_url)
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
                    SELECT ncessch, state_fips
                    FROM schools_nces
                    WHERE ncessch IS NOT NULL
                      AND state_fips IS NOT NULL
                      AND (state_fips || county_fips) = ANY(%s)
                    """,
                    (sorted(allow_counties),),
                )
                rows = cur.fetchall()
                if not rows:
                    # National batch may still have NCES without county_fips match;
                    # fall back to state filter from allowlist.
                    states = sorted({c[:2] for c in allow_counties})
                    cur.execute(
                        """
                        SELECT ncessch, state_fips
                        FROM schools_nces
                        WHERE ncessch IS NOT NULL
                          AND state_fips = ANY(%s)
                        """,
                        (states,),
                    )
                    rows = cur.fetchall()

                ncessch_all = {
                    str(r[0])[:12] for r in rows if r[0]
                }
                if force_enabled() or not ncessch_all:
                    done: set[str] = set()
                else:
                    cur.execute(
                        """
                        SELECT ncessch
                        FROM schools_urban
                        WHERE year = %s AND ncessch = ANY(%s)
                        """,
                        (self._year, sorted(ncessch_all)),
                    )
                    done = {str(r[0])[:12] for r in cur.fetchall() if r[0]}
        finally:
            conn.close()

        if not rows:
            raise RuntimeError(
                "schools_nces is empty for active counties — run worker-nces first"
            )

        pending_ncessch = ncessch_all - done
        log_skip(self.logger, "urban", len(done), len(pending_ncessch))
        self._ncessch_allow = frozenset(pending_ncessch if pending_ncessch else ncessch_all)

        # States that still have missing urban rows (or all states if forced).
        if force_enabled():
            pending_states = sorted({str(r[1]).zfill(2)[-2:] for r in rows if r[1]})
        else:
            pending_by_state: dict[str, int] = {}
            for ncessch, state_fips in rows:
                if not ncessch or not state_fips:
                    continue
                key = str(ncessch)[:12]
                if key in done:
                    continue
                st = str(state_fips).zfill(2)[-2:]
                pending_by_state[st] = pending_by_state.get(st, 0) + 1
            pending_states = sorted(pending_by_state)

        if not pending_states:
            self.logger.info("Urban skip-done: nothing pending for year=%s", self._year)
            return

        self.logger.info(
            "Urban fetch for states=%s covering up to %s pending NCESSCH",
            pending_states,
            len(pending_ncessch),
        )

        pulse = StatusPulse(self.database_url)
        try:
            self._raw_rows = fetch_directory_for_states(
                pending_states, year=self._year
            )
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Urban state fetch failed: %s", exc)
            raise
        pulse.tick()
        pulse.flush()
        self.logger.info("Urban raw rows=%s", len(self._raw_rows))

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
