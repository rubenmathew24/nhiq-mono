-- EPA AQS monitor-county universe for coverage / inventory denominators.
-- Apply on existing Azure / Compose volumes (idempotent; does NOT truncate data):
--   psql "$DATABASE_URL" -f infra/sql/008_epa_monitor_counties.sql
-- Fresh volumes: also covered by infra/sql/init.sql.
--
-- Why: EPA AirData only publishes counties with monitors. Coverage used to divide
-- by all ~3144 geo_counties (~5–6% ceiling). Denominator is now this catalog
-- (same pattern as urban ÷ NCES counties). Backfill from existing readings so
-- coverage is correct before the next bulk discover pass.

CREATE TABLE IF NOT EXISTS epa_aqs_monitor_counties (
    county_fips VARCHAR(5) PRIMARY KEY,
    source_year INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE epa_aqs_monitor_counties IS
  'Counties EPA AQS/AirData published for (monitor presence). Coverage total for epa.';

INSERT INTO epa_aqs_monitor_counties (county_fips, source_year, updated_at)
SELECT
    county_fips,
    EXTRACT(YEAR FROM MAX(date_local))::integer,
    NOW()
FROM epa_aqi_readings
GROUP BY county_fips
ON CONFLICT (county_fips) DO NOTHING;
