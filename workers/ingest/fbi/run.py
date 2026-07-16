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
from ingest.checkpoints import counties_with_fbi_agencies, log_skip
from ingest.fbi import client as cde
from ingest.fbi.transform import agencies_to_rows, offense_aggregate_row
from ingest.fixtures.canonical_addresses import (
    CanonicalAddress,
    active_canonical_addresses,
)
from ingest.fixtures.constants import DATA_VINTAGE
from ingest.geo.scope import (
    CountyPoint,
    active_county_fips,
    load_county_points,
    resolve_ingest_scope,
)

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


class PartialCdeCoverageError(RuntimeError):
    """Raised when one or more allowlist counties failed to get offense rows."""


def _upsert_county_rows(
    database_url: str,
    agency_rows: list[dict],
    offense_rows: list[dict],
    *,
    logger_: logging.Logger,
) -> None:
    if not agency_rows and not offense_rows:
        return
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            if agency_rows:
                execute_batch(cur, UPSERT_AGENCY_SQL, agency_rows, page_size=100)
            if offense_rows:
                execute_batch(cur, UPSERT_OFFENSE_SQL, offense_rows, page_size=100)
        conn.commit()
        logger_.info(
            "Checkpoint upsert agencies=%s offenses=%s",
            len(agency_rows),
            len(offense_rows),
        )
    finally:
        conn.close()


def _points_for_run(database_url: str) -> list[CanonicalAddress | CountyPoint]:
    """Fixture addresses for metro/smoke; geo centroids for national."""
    scope = resolve_ingest_scope()
    if scope != "national":
        return list(active_canonical_addresses())
    counties = active_county_fips(database_url=database_url)
    done = counties_with_fbi_agencies(database_url, sorted(counties))
    pending = counties - done
    log_skip(logging.getLogger("fbi"), "fbi", len(done), len(pending))
    points = load_county_points(database_url, pending)
    missing = sorted(pending - frozenset(points))
    if missing:
        logging.getLogger("fbi").warning(
            "No geo_counties centroid for counties=%s — skipped", missing
        )
    return list(points.values())


class FbiCdeWorker(BaseIngestionWorker):
    def __init__(self) -> None:
        super().__init__("fbi")
        self._agency_rows: list[dict] = []
        self._offense_rows: list[dict] = []
        self._seen_counties: set[str] = set()
        self._counties_with_offenses: set[str] = set()

    def run(self) -> None:
        # Fail before "Starting" logs if the key is missing.
        cde.require_api_key()
        super().run()
        total = len(self._seen_counties)
        ok = len(self._counties_with_offenses)
        if total and ok < total:
            missing = sorted(self._seen_counties - self._counties_with_offenses)
            raise PartialCdeCoverageError(
                f"Partial CDE coverage: {ok}/{total} counties have offense rows; "
                f"missing={missing}. Re-run when the upstream API recovers."
            )

    def fetch(self) -> None:
        # Fetch happens per-county inside transform (needs lat/lon + state together).
        self._agency_rows = []
        self._offense_rows = []
        self._seen_counties = set()
        self._counties_with_offenses = set()

    def transform(self) -> None:
        offenses = cde.chart_offenses()
        from_mm, to_mm = cde.chart_window()

        # Metro: also skip counties that already have agencies
        points = _points_for_run(self.database_url)
        if resolve_ingest_scope() != "national":
            counties = {p.county_fips for p in points}
            done = counties_with_fbi_agencies(self.database_url, sorted(counties))
            if done:
                before = len(points)
                points = [p for p in points if p.county_fips not in done]
                log_skip(self.logger, "fbi", before - len(points), len(points))

        for addr in points:
            if addr.county_fips in self._seen_counties:
                continue
            self._seen_counties.add(addr.county_fips)
            self.logger.info(
                "CDE county=%s state=%s lat=%.4f lon=%.4f",
                addr.county_fips,
                addr.state_abbr,
                addr.latitude,
                addr.longitude,
            )
            county_agency_rows: list[dict] = []
            county_offense_rows: list[dict] = []
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

            county_agency_rows = agencies_to_rows(
                county_fips=addr.county_fips,
                state_abbr=addr.state_abbr,
                agencies=selected,
                data_vintage=DATA_VINTAGE,
            )

            hom_ok = False
            for slug in offenses:
                local_total = 0.0
                charts_ok = 0
                for agency in selected:
                    try:
                        chart = cde.fetch_agency_offense_chart(
                            agency["ori"], slug, from_mm, to_mm
                        )
                        local_total += cde.sum_last_n_month_counts(chart, n=12)
                        charts_ok += 1
                        cde.pause_between_requests()
                    except Exception as exc:  # noqa: BLE001
                        self.logger.warning(
                            "Chart %s/%s failed: %s", agency["ori"], slug, exc
                        )
                if slug == "HOM" and charts_ok > 0:
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
                county_offense_rows.append(row)

            if county_offense_rows and hom_ok:
                self._counties_with_offenses.add(addr.county_fips)
            elif not hom_ok:
                self.logger.error(
                    "HOM charts failed for county %s — safety may use default",
                    addr.county_fips,
                )

            # Checkpoint this county immediately (idempotent upserts).
            try:
                _upsert_county_rows(
                    self.database_url,
                    county_agency_rows,
                    county_offense_rows,
                    logger_=self.logger,
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "Checkpoint upsert failed for %s: %s", addr.county_fips, exc
                )
                continue

            self._agency_rows.extend(county_agency_rows)
            self._offense_rows.extend(county_offense_rows)

        total_counties = len(self._seen_counties)
        ok_counties = len(self._counties_with_offenses)
        self.logger.info(
            "Prepared %s agency rows, %s offense aggregates "
            "(counties with offense rows: %s/%s)",
            len(self._agency_rows),
            len(self._offense_rows),
            ok_counties,
            total_counties,
        )
        if ok_counties < total_counties:
            missing = sorted(self._seen_counties - self._counties_with_offenses)
            self.logger.warning(
                "Partial CDE coverage — %s/%s counties have offense rows; "
                "missing=%s.",
                ok_counties,
                total_counties,
                missing,
            )

    def load(self) -> None:
        # Rows are checkpointed per county in transform(); nothing left for bulk load.
        if not self._agency_rows and not self._offense_rows:
            self.logger.warning("No CDE rows to load")
            return
        self.logger.info(
            "Per-county checkpoints already wrote agencies=%s offenses=%s",
            len(self._agency_rows),
            len(self._offense_rows),
        )


def main() -> int:
    try:
        FbiCdeWorker().run()
        return 0
    except (RuntimeError, PartialCdeCoverageError) as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
