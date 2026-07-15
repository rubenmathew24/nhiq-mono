"""Score computation: healthcare, environment, safety, education, economic."""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_batch

# workers/ on path for `python -m scoring.compute`
_WORKERS_ROOT = Path(__file__).resolve().parents[1]
if str(_WORKERS_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKERS_ROOT))

from dotenv import load_dotenv

from ingest.fixtures.canonical_addresses import fixture_county_fips
from ingest.fixtures.constants import (
    DATA_VINTAGE,
    EPA_END_LAG_DAYS,
    EPA_LOOKBACK_DAYS,
    PLACEHOLDER_ECONOMIC_SCORE,
    PLACEHOLDER_EDUCATION_SCORE,
    SOURCE_CMS_HOSPITALS,
    SOURCE_DEFAULT,
    SOURCE_PLACEHOLDER,
)
from scoring.economic import EconomicInputs, economic_from_sources
from scoring.education import EducationInputs, education_from_sources
from scoring.environment import EpaCountyAqi, resolve_environment
from scoring.formulas import healthcare_from_nearest, weighted_overall
from scoring.open_meteo import fetch_mean_us_aqi
from scoring.safety import CountyCrime, safety_from_cde

load_dotenv(_WORKERS_ROOT.parent / ".env")
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)
logger = logging.getLogger("scoring")


def aqi_window() -> tuple[date, date]:
    """Match EPA ingest lag/lookback so scoring uses data that was loaded."""
    end = date.today() - timedelta(days=EPA_END_LAG_DAYS)
    start = end - timedelta(days=EPA_LOOKBACK_DAYS - 1)
    return start, end


TRACT_INPUTS_SQL = """
SELECT
    t.geoid,
    t.state_fips,
    t.county_fips,
    n.avg_stars,
    n.nearest_er_miles,
    edu.ncessch,
    edu.nearest_school_miles,
    edu.locale,
    edu.enrollment,
    edu.teachers_fte,
    acs.median_hh_income,
    acs.acs_year,
    bls.unemployment_rate,
    bls.laus_period
FROM census_tracts t
LEFT JOIN LATERAL (
    SELECT
        AVG(nn.star_rating)::float AS avg_stars,
        MIN(nn.miles)::float AS nearest_er_miles
    FROM (
        SELECT
            h.star_rating,
            ST_Distance(
                h.geometry::geography,
                ST_Centroid(t.geometry)::geography
            ) / 1609.34 AS miles
        FROM hospitals h
        WHERE h.emergency_services = true
          AND h.geometry IS NOT NULL
        ORDER BY h.geometry <-> ST_Centroid(t.geometry)
        LIMIT 3
    ) nn
) n ON true
{education_join}
{acs_join}
{bls_join}
WHERE (t.state_fips || t.county_fips) = ANY(%s)
ORDER BY t.geoid
"""

_EDUCATION_JOIN_TEMPLATE = """
LEFT JOIN LATERAL (
    SELECT
        s.ncessch,
        s.locale,
        ST_Distance(
            s.geometry::geography,
            ST_Centroid(t.geometry)::geography
        ) / 1609.34 AS nearest_school_miles,
        {urban_select}
    FROM schools_nces s
    {urban_join}
    WHERE s.geometry IS NOT NULL
    ORDER BY s.geometry <-> ST_Centroid(t.geometry)
    LIMIT 1
) edu ON true
"""

_URBAN_JOIN = """
    LEFT JOIN schools_urban u ON u.ncessch = s.ncessch
        AND u.year = (
            SELECT MAX(u2.year)
            FROM schools_urban u2
            WHERE u2.ncessch = s.ncessch
        )
"""

_ACS_JOIN = """
LEFT JOIN LATERAL (
    SELECT
        a.median_hh_income,
        a.acs_year
    FROM acs_indicators a
    WHERE a.geoid = t.geoid
      AND a.geo_level = 'tract'
    ORDER BY a.acs_year DESC
    LIMIT 1
) acs ON true
"""

_BLS_JOIN = """
LEFT JOIN LATERAL (
    SELECT
        b.unemployment_rate,
        b.period AS laus_period
    FROM bls_laus_county b
    WHERE b.county_fips = (t.state_fips || t.county_fips)
    ORDER BY b.period DESC
    LIMIT 1
) bls ON true
"""

_NULL_EDUCATION_JOIN = """
LEFT JOIN LATERAL (
    SELECT
        NULL::varchar AS ncessch,
        NULL::varchar AS locale,
        NULL::float AS nearest_school_miles,
        NULL::int AS enrollment,
        NULL::numeric AS teachers_fte
    WHERE false
) edu ON true
"""

_NULL_ACS_JOIN = """
LEFT JOIN LATERAL (
    SELECT NULL::numeric AS median_hh_income, NULL::varchar AS acs_year
    WHERE false
) acs ON true
"""

_NULL_BLS_JOIN = """
LEFT JOIN LATERAL (
    SELECT NULL::numeric AS unemployment_rate, NULL::varchar AS laus_period
    WHERE false
) bls ON true
"""


def _tract_inputs_sql(tables: dict[str, bool]) -> str:
    if tables["nces"]:
        education_join = _EDUCATION_JOIN_TEMPLATE.format(
            urban_select=(
                "u.enrollment, u.teachers_fte"
                if tables["urban"]
                else "NULL::int AS enrollment, NULL::numeric AS teachers_fte"
            ),
            urban_join=_URBAN_JOIN if tables["urban"] else "",
        )
    else:
        education_join = _NULL_EDUCATION_JOIN
    return TRACT_INPUTS_SQL.format(
        education_join=education_join,
        acs_join=_ACS_JOIN if tables["acs"] else _NULL_ACS_JOIN,
        bls_join=_BLS_JOIN if tables["bls"] else _NULL_BLS_JOIN,
    )

COUNTY_CENTROID_SQL = """
SELECT
    state_fips || county_fips AS county_fips,
    ST_Y(ST_Centroid(ST_Collect(geometry))) AS lat,
    ST_X(ST_Centroid(ST_Collect(geometry))) AS lng
FROM census_tracts
WHERE (state_fips || county_fips) = ANY(%s)
GROUP BY state_fips, county_fips
"""

UPSERT_SCORE_SQL = """
INSERT INTO neighborhood_scores (
    geoid, healthcare_score, safety_score, environment_score,
    education_score, economic_score, overall_score, data_vintage,
    score_sources, computed_at
) VALUES (
    %(geoid)s, %(healthcare)s, %(safety)s, %(environment)s,
    %(education)s, %(economic)s, %(overall)s, %(vintage)s,
    %(score_sources)s, NOW()
)
ON CONFLICT (geoid, data_vintage) DO UPDATE SET
    healthcare_score = EXCLUDED.healthcare_score,
    safety_score = EXCLUDED.safety_score,
    environment_score = EXCLUDED.environment_score,
    education_score = EXCLUDED.education_score,
    economic_score = EXCLUDED.economic_score,
    overall_score = EXCLUDED.overall_score,
    score_sources = EXCLUDED.score_sources,
    computed_at = NOW()
"""


def fetch_epa_county_stats(cur, start: date, end: date) -> dict[str, EpaCountyAqi]:
    cur.execute(
        """
        SELECT
            county_fips,
            AVG(aqi)::float AS avg_aqi,
            COUNT(DISTINCT date_local)::int AS distinct_days,
            MIN(date_local) AS min_date,
            MAX(date_local) AS max_date
        FROM epa_aqi_readings
        WHERE date_local BETWEEN %s AND %s
          AND aqi IS NOT NULL
        GROUP BY county_fips
        """,
        (start, end),
    )
    out: dict[str, EpaCountyAqi] = {}
    for county_fips, avg_aqi, distinct_days, min_d, max_d in cur.fetchall():
        out[county_fips] = EpaCountyAqi(
            county_fips=county_fips,
            avg_aqi=float(avg_aqi),
            distinct_days=int(distinct_days),
            min_date=min_d,
            max_date=max_d,
        )
    return out


def fetch_county_centroids(cur, counties: list[str]) -> dict[str, tuple[float, float]]:
    cur.execute(COUNTY_CENTROID_SQL, (counties,))
    return {
        row[0]: (float(row[1]), float(row[2]))
        for row in cur.fetchall()
        if row[1] is not None and row[2] is not None
    }


def fetch_cde_by_county(cur, counties: list[str]) -> dict[str, CountyCrime]:
    """Load county-merged CDE offense aggregates + agency counts for safety."""
    cur.execute(
        """
        SELECT to_regclass('public.crime_agency_selection') IS NOT NULL,
               to_regclass('public.crime_offense_monthly') IS NOT NULL
        """
    )
    has_agency, has_offense = cur.fetchone()
    if not has_agency or not has_offense:
        logger.warning("CDE tables missing — apply infra/sql/004_safety_education_economic.sql")
        return {}

    cur.execute(
        """
        SELECT county_fips, COUNT(*)::int
        FROM crime_agency_selection
        WHERE data_vintage = %s AND county_fips = ANY(%s)
        GROUP BY county_fips
        """,
        (DATA_VINTAGE, counties),
    )
    ori_counts = {row[0]: int(row[1]) for row in cur.fetchall()}

    cur.execute(
        """
        SELECT county_fips, offense_slug, incidents_12mo, state_benchmark_12mo
        FROM crime_offense_monthly
        WHERE data_vintage = %s
          AND county_fips = ANY(%s)
          AND ori = ''
        """,
        (DATA_VINTAGE, counties),
    )

    by_county: dict[str, dict[str, tuple[float, float | None]]] = {}
    for county_fips, slug, incidents, bench in cur.fetchall():
        bucket = by_county.setdefault(county_fips, {})
        try:
            inc_f = float(incidents) if incidents is not None else 0.0
        except (TypeError, ValueError):
            inc_f = 0.0
        try:
            bench_f = float(bench) if bench is not None else None
        except (TypeError, ValueError):
            bench_f = None
        bucket[str(slug).upper()] = (inc_f, bench_f)

    out: dict[str, CountyCrime] = {}
    for county in set(ori_counts) | set(by_county):
        out[county] = CountyCrime(
            county_fips=county,
            by_offense=by_county.get(county, {}),
            ori_count=ori_counts.get(county, 0),
        )
    return out


def build_open_meteo_by_county(
    counties: list[str],
    centroids: dict[str, tuple[float, float]],
    *,
    need_fallback: set[str],
) -> dict[str, float]:
    """Fetch Open-Meteo only for counties that fail the EPA worthiness gate."""
    out: dict[str, float] = {}
    for county in counties:
        if county not in need_fallback:
            continue
        coords = centroids.get(county)
        if not coords:
            logger.warning("No centroid for county %s — skip Open-Meteo", county)
            continue
        lat, lng = coords
        avg = fetch_mean_us_aqi(lat, lng)
        if avg is not None:
            out[county] = avg
            logger.info("Open-Meteo county %s mean US AQI=%.1f", county, avg)
        else:
            logger.warning("Open-Meteo returned no AQI for county %s", county)
    return out


def _healthcare_provenance(nearest_miles: float | None) -> dict:
    if nearest_miles is None:
        return {"source_id": SOURCE_DEFAULT, "reason": "no_nearby_er"}
    return {
        "source_id": SOURCE_CMS_HOSPITALS,
        "reason": "nearest_er",
        "nearest_er_miles": round(float(nearest_miles), 2),
    }


def _placeholder_prov(name: str) -> dict:
    return {"source_id": SOURCE_PLACEHOLDER, "reason": f"{name}_pending_source_worker"}


def _source_tables_present(cur) -> dict[str, bool]:
    cur.execute(
        """
        SELECT
            to_regclass('public.schools_nces') IS NOT NULL,
            to_regclass('public.schools_urban') IS NOT NULL,
            to_regclass('public.acs_indicators') IS NOT NULL,
            to_regclass('public.bls_laus_county') IS NOT NULL
        """
    )
    nces, urban, acs, bls = cur.fetchone()
    return {
        "nces": bool(nces),
        "urban": bool(urban),
        "acs": bool(acs),
        "bls": bool(bls),
    }


def _count_table_rows(cur, table: str) -> int:
    cur.execute(f"SELECT COUNT(*)::int FROM {table}")
    return int(cur.fetchone()[0])


def _invalidate_report_cache() -> None:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return
    try:
        import redis

        client = redis.from_url(redis_url, decode_responses=True)
        pattern = f"report:{DATA_VINTAGE}:*"
        deleted = 0
        for key in client.scan_iter(match=pattern):
            deleted += client.delete(key)
        client.close()
        logger.info("Invalidated %s Redis report keys (%s)", deleted, pattern)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis report cache invalidation skipped: %s", exc)


def run() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    counties = sorted(fixture_county_fips())
    start, end = aqi_window()
    logger.info(
        "Scoring fixture counties=%s vintage=%s AQI window=%s..%s",
        counties,
        DATA_VINTAGE,
        start,
        end,
    )

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            epa_by_county = fetch_epa_county_stats(cur, start, end)
            worthy = {c for c, s in epa_by_county.items() if s.is_worthy}
            need_fallback = set(counties) - worthy
            logger.info(
                "EPA worthy counties=%s; Open-Meteo fallback candidates=%s",
                sorted(worthy),
                sorted(need_fallback),
            )

            centroids = fetch_county_centroids(cur, counties)
            om_by_county = build_open_meteo_by_county(
                counties, centroids, need_fallback=need_fallback
            )
            cde_by_county = fetch_cde_by_county(cur, counties)
            tables = _source_tables_present(cur)
            has_nces_data = tables["nces"] and _count_table_rows(cur, "schools_nces") > 0
            has_urban_data = tables["urban"] and _count_table_rows(cur, "schools_urban") > 0
            has_acs_data = tables["acs"] and _count_table_rows(cur, "acs_indicators") > 0
            has_bls_data = tables["bls"] and _count_table_rows(cur, "bls_laus_county") > 0
            logger.info(
                "Education tables: nces=%s urban=%s; economic tables: acs=%s bls=%s",
                has_nces_data,
                has_urban_data,
                has_acs_data,
                has_bls_data,
            )

            cur.execute(_tract_inputs_sql(tables), (counties,))
            tracts = cur.fetchall()
            if not tracts:
                logger.error(
                    "No census tracts found for fixture counties — run census worker first"
                )
                return 1

            rows: list[dict] = []
            env_counts: dict[str, int] = {}
            safety_counts: dict[str, int] = {}
            education_counts: dict[str, int] = {}
            economic_counts: dict[str, int] = {}
            for row in tracts:
                (
                    geoid,
                    state_fips,
                    county_fips,
                    avg_stars,
                    nearest_miles,
                    ncessch,
                    nearest_school_miles,
                    locale,
                    enrollment,
                    teachers_fte,
                    median_hh_income,
                    acs_year,
                    unemployment_rate,
                    laus_period,
                ) = row
                county = f"{state_fips}{county_fips}"
                healthcare = healthcare_from_nearest(avg_stars, nearest_miles)
                env = resolve_environment(
                    epa=epa_by_county.get(county),
                    open_meteo_avg=om_by_county.get(county),
                )
                sid = str(env.provenance.get("source_id", SOURCE_DEFAULT))
                env_counts[sid] = env_counts.get(sid, 0) + 1
                safety_res = safety_from_cde(cde_by_county.get(county))
                safety = safety_res.score
                ssid = str(safety_res.provenance.get("source_id", SOURCE_DEFAULT))
                safety_counts[ssid] = safety_counts.get(ssid, 0) + 1

                if has_nces_data or has_urban_data:
                    edu_res = education_from_sources(
                        EducationInputs(
                            nearest_miles=float(nearest_school_miles)
                            if nearest_school_miles is not None
                            else None,
                            locale=locale,
                            enrollment=int(enrollment) if enrollment is not None else None,
                            teachers_fte=float(teachers_fte)
                            if teachers_fte is not None
                            else None,
                            ncessch=ncessch,
                        ),
                        has_nces_table=has_nces_data,
                        has_urban_table=has_urban_data,
                    )
                    education = edu_res.score
                    education_prov = edu_res.provenance
                else:
                    education = PLACEHOLDER_EDUCATION_SCORE
                    education_prov = _placeholder_prov("education")

                if has_acs_data or has_bls_data:
                    econ_res = economic_from_sources(
                        EconomicInputs(
                            median_hh_income=float(median_hh_income)
                            if median_hh_income is not None
                            else None,
                            unemployment_rate=float(unemployment_rate)
                            if unemployment_rate is not None
                            else None,
                            acs_year=acs_year,
                            laus_period=laus_period,
                        ),
                        has_acs_table=has_acs_data,
                        has_bls_table=has_bls_data,
                    )
                    economic = econ_res.score
                    economic_prov = econ_res.provenance
                else:
                    economic = PLACEHOLDER_ECONOMIC_SCORE
                    economic_prov = _placeholder_prov("economic")

                esid = str(education_prov.get("source_id", SOURCE_DEFAULT))
                education_counts[esid] = education_counts.get(esid, 0) + 1
                ecsid = str(economic_prov.get("source_id", SOURCE_DEFAULT))
                economic_counts[ecsid] = economic_counts.get(ecsid, 0) + 1

                overall = weighted_overall(
                    healthcare, safety, education, env.score, economic
                )
                score_sources = {
                    "healthcare": _healthcare_provenance(nearest_miles),
                    "safety": safety_res.provenance,
                    "environment": env.provenance,
                    "education": education_prov,
                    "economic": economic_prov,
                }
                rows.append(
                    {
                        "geoid": geoid,
                        "healthcare": healthcare,
                        "safety": safety,
                        "environment": env.score,
                        "education": education,
                        "economic": economic,
                        "overall": overall,
                        "vintage": DATA_VINTAGE,
                        "score_sources": Json(score_sources),
                    }
                )

            logger.info("Writing %s score rows…", len(rows))
            execute_batch(cur, UPSERT_SCORE_SQL, rows, page_size=200)
        conn.commit()
        logger.info(
            "Upserted %s neighborhood_scores rows (vintage=%s)",
            len(rows),
            DATA_VINTAGE,
        )
        logger.info("Environment source mix: %s", env_counts)
        logger.info("Safety source mix: %s", safety_counts)
        logger.info("Education source mix: %s", education_counts)
        logger.info("Economic source mix: %s", economic_counts)
        _invalidate_report_cache()
    finally:
        conn.close()
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
