"""FBI CDE chart ingestion for fixture counties (replaces skeleton).

Probe path: specs/002-data-ingestion-workers/research.md §8.
Requires FBI_CDE_API_KEY (api.data.gov).
"""

from __future__ import annotations

import logging
import sys
from datetime import date

import psycopg2
from psycopg2.extras import Json, execute_batch

from ingest.base import BaseIngestionWorker
from ingest.fbi import client as cde
from ingest.fbi.transform import agencies_to_rows, offense_aggregate_row
from ingest.fixtures.canonical_addresses import active_canonical_addresses
from ingest.fixtures.constants import DATA_VINTAGE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fbi")

UPSERT_AGENCY_SQL = """
INSERT INTO crime_agency_selection (
    county_fips, ori, agency_name, state_abbr, distance_miles,
    is_primary_hint, data_vintage, selected_at
) VALUES (
    %(county_fips)s, %(ori)s, %(agency_name)s, %(state_abbr)s,
    %(distance_miles)s, %(is_primary_hint)s, %(data_vintage)s, NOW()
)
ON CONFLICT (county_fips, ori, data_vintage) DO UPDATE SET
    agency_name = EXCLUDED.agency_name,
    distance_miles = EXCLUDED.distance_miles,
    is_primary_hint = EXCLUDED.is_primary_hint,
    selected_at = NOW()
"""

UPSERT_OFFENSE_SQL = """
INSERT INTO crime_offense_monthly (
    county_fips, ori, offense_slug, period_start, period_end,
    incidents_12mo, rate_12mo, state_benchmark_12mo, payload, data_vintage, updated_at
) VALUES (
    %(county_fips)s, %(ori)s, %(offense_slug)s, %(period_start)s, %(period_end)s,
    %(incidents_12mo)s, %(rate_12mo)s, %(state_benchmark_12mo)s,
    %(payload)s, %(data_vintage)s, NOW()
)
ON CONFLICT (county_fips, ori, offense_slug, data_vintage) DO UPDATE SET
    period_start = EXCLUDED.period_start,
    period_end = EXCLUDED.period_end,
    incidents_12mo = EXCLUDED.incidents_12mo,
    rate_12mo = EXCLUDED.rate_12mo,
    state_benchmark_12mo = EXCLUDED.state_benchmark_12mo,
    payload = EXCLUDED.payload,
    updated_at = NOW()
"""


class FbiCdeWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("fbi")
        self._agency_rows: list[dict] = []
        self._offense_rows: list[dict] = []

    def run(self) -> None:
        # Fail before "Starting" logs if the key is missing.
        cde.require_api_key()
        super().run()

    def fetch(self) -> None:
        # Fetch happens per-county inside transform (needs lat/lon + state together).
        self._agency_rows = []
        self._offense_rows = []

    def transform(self) -> None:
        offenses = cde.chart_offenses()
        from_mm, to_mm = cde.chart_window()
        seen_counties: set[str] = set()
        counties_with_offenses: set[str] = set()

        for addr in active_canonical_addresses():
            if addr.county_fips in seen_counties:
                continue
            seen_counties.add(addr.county_fips)
            self.logger.info(
                "CDE county=%s state=%s lat=%.4f lon=%.4f",
                addr.county_fips,
                addr.state_abbr,
                addr.latitude,
                addr.longitude,
            )
            try:
                agencies = cde.fetch_agencies_by_state(addr.state_abbr)
                selected = cde.select_nearest_agencies(
                    agencies,
                    lat=addr.latitude,
                    lon=addr.longitude,
                    county_name=addr.county_name,
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "Agency selection failed for %s: %s", addr.county_fips, exc
                )
                continue

            if not selected:
                self.logger.warning("No agencies selected for %s", addr.county_fips)
                continue

            self._agency_rows.extend(
                agencies_to_rows(
                    county_fips=addr.county_fips,
                    state_abbr=addr.state_abbr,
                    agencies=selected,
                    data_vintage=DATA_VINTAGE,
                )
            )

            hom_ok = False
            offense_rows_before = len(self._offense_rows)
            for slug in offenses:
                local_total = 0.0
                for agency in selected:
                    try:
                        chart = cde.fetch_agency_offense_chart(
                            agency["ori"], slug, from_mm, to_mm
                        )
                        local_total += cde.sum_last_n_month_counts(chart, n=12)
                        cde.pause_between_requests()
                    except Exception as exc:  # noqa: BLE001
                        self.logger.warning(
                            "Chart %s/%s failed: %s", agency["ori"], slug, exc
                        )
                if slug == "HOM" and local_total >= 0:
                    # HOM path reached without hard failure — mark ok even if 0 counts.
                    hom_ok = True

                state_bench: float | None = None
                try:
                    state_chart = cde.fetch_state_offense_chart(
                        addr.state_abbr, slug, from_mm, to_mm
                    )
                    state_bench = cde.sum_last_n_month_counts(state_chart, n=12)
                    cde.pause_between_requests()
                except Exception as exc:  # noqa: BLE001
                    self.logger.warning(
                        "State chart %s/%s failed: %s", addr.state_abbr, slug, exc
                    )

                row = offense_aggregate_row(
                    county_fips=addr.county_fips,
                    offense_slug=slug,
                    incidents_12mo=local_total,
                    state_benchmark_12mo=state_bench,
                    data_vintage=DATA_VINTAGE,
                    period_end=date.today().replace(day=1),
                    payload={
                        "from": from_mm,
                        "to": to_mm,
                        "ori_count": len(selected),
                    },
                )
                row["payload"] = Json(row["payload"]) if row["payload"] else None
                self._offense_rows.append(row)

            if len(self._offense_rows) > offense_rows_before:
                counties_with_offenses.add(addr.county_fips)

            if not hom_ok:
                self.logger.error(
                    "HOM charts failed for county %s — safety may use default",
                    addr.county_fips,
                )

        total_counties = len(seen_counties)
        ok_counties = len(counties_with_offenses)
        self.logger.info(
            "Prepared %s agency rows, %s offense aggregates "
            "(fixture counties with offense rows: %s/%s)",
            len(self._agency_rows),
            len(self._offense_rows),
            ok_counties,
            total_counties,
        )
        if ok_counties < total_counties:
            missing = sorted(seen_counties - counties_with_offenses)
            self.logger.warning(
                "Partial CDE fixture coverage — %s/%s counties have offense rows; "
                "missing=%s. Re-run when the upstream API recovers; do not treat "
                "this as full fixture-set success.",
                ok_counties,
                total_counties,
                missing,
            )

    def load(self) -> None:
        if not self._agency_rows and not self._offense_rows:
            self.logger.warning("No CDE rows to load")
            return
        conn = psycopg2.connect(self.database_url)
        try:
            with conn.cursor() as cur:
                if self._agency_rows:
                    execute_batch(cur, UPSERT_AGENCY_SQL, self._agency_rows, page_size=100)
                if self._offense_rows:
                    execute_batch(cur, UPSERT_OFFENSE_SQL, self._offense_rows, page_size=100)
            conn.commit()
            self.logger.info(
                "Upserted agencies=%s offenses=%s",
                len(self._agency_rows),
                len(self._offense_rows),
            )
        finally:
            conn.close()


def main() -> int:
    try:
        FbiCdeWorker().run()
        return 0
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
