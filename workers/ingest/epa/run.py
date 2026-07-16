"""EPA air quality ingestion — fixture counties only."""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import date, timedelta

import psycopg2
from psycopg2.extras import execute_values

from ingest.base import BaseIngestionWorker
from ingest.epa.client import fetch_daily_aqi, require_epa_credentials
from ingest.epa.transform import transform_aqi_records
from ingest.checkpoints import counties_with_epa, log_skip
from ingest.fixtures.constants import EPA_END_LAG_DAYS, EPA_LOOKBACK_DAYS
from ingest.geo.scope import active_county_fips

logger = logging.getLogger("epa")


def _ingest_date_window() -> tuple[date, date]:
    """AQS lags — end a few days ago, span lookback for environment averages."""
    end = date.today() - timedelta(days=EPA_END_LAG_DAYS)
    start = end - timedelta(days=EPA_LOOKBACK_DAYS - 1)
    return start, end


class EpaAqiWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("epa")
        self._raw_by_state: dict[str, list[dict]] = {}
        self._records: list[dict] = []

    def fetch(self) -> None:
        require_epa_credentials()
        self._allow = active_county_fips(database_url=self.database_url)
        done = counties_with_epa(self.database_url, sorted(self._allow))
        pending = self._allow - done
        log_skip(self.logger, "epa", len(done), len(pending))
        self._pending_counties = pending
        start, end = _ingest_date_window()
        self.logger.info(
            "EPA date window %s → %s (lag=%sd, lookback=%sd)",
            start,
            end,
            EPA_END_LAG_DAYS,
            EPA_LOOKBACK_DAYS,
        )
        # Fetch whole states that still have pending counties (AQS is state-scoped).
        states = frozenset(cf[:2] for cf in pending) or frozenset()
        self._raw_by_state = asyncio.run(self._fetch_states(states, start, end))

    async def _fetch_states(
        self, states: frozenset[str], start: date, end: date
    ) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for state_code in sorted(states):
            try:
                raw = await fetch_daily_aqi(state_code, start, end)
                out[state_code] = raw
                self.logger.info(
                    "State %s: fetched %d raw EPA rows for %s..%s",
                    state_code,
                    len(raw),
                    start.isoformat(),
                    end.isoformat(),
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.error("State %s fetch failed: %s", state_code, exc)
                out[state_code] = []
        return out

    def transform(self) -> None:
        allow = getattr(self, "_pending_counties", None) or getattr(
            self, "_allow", frozenset()
        )
        combined: list[dict] = []
        for state_code, raw in self._raw_by_state.items():
            records = transform_aqi_records(raw, county_allowlist=allow)
            self.logger.info(
                "State %s: %d county records after transform",
                state_code,
                len(records),
            )
            combined.extend(records)
        self._records = combined

    def load(self) -> None:
        if not self._records:
            self.logger.warning("No EPA records to load")
            return

        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                rows = [
                    (
                        r["county_fips"],
                        r["parameter_code"],
                        r["parameter_name"],
                        r["aqi"],
                        r["category"],
                        r["date_local"],
                        r["state_name"],
                        r["county_name"],
                    )
                    for r in self._records
                    if r.get("date_local")
                ]
                execute_values(
                    cur,
                    """
                    INSERT INTO epa_aqi_readings
                        (county_fips, parameter_code, parameter_name, aqi,
                         category, date_local, state_name, county_name)
                    VALUES %s
                    ON CONFLICT (county_fips, parameter_code, date_local) DO UPDATE
                        SET aqi = EXCLUDED.aqi,
                            category = EXCLUDED.category,
                            parameter_name = EXCLUDED.parameter_name,
                            state_name = EXCLUDED.state_name,
                            county_name = EXCLUDED.county_name
                    """,
                    rows,
                    page_size=500,
                )
            conn.commit()
            self.logger.info(
                "EPA ingestion complete. Upserted %d records", len(rows)
            )
        finally:
            conn.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    )
    try:
        EpaAqiWorker().run()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
