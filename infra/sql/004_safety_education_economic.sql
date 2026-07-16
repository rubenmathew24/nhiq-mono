-- Reopen DDL: safety (FBI CDE), education (NCES + Urban), economic (ACS + BLS LAUS)
-- Apply on existing Compose volumes:
--   docker compose exec -T db psql -U postgres -d neighborhoodiq < infra/sql/004_safety_education_economic.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;

-- ── R1 FBI CDE ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crime_agency_selection (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_fips VARCHAR(5) NOT NULL,
    ori VARCHAR(10) NOT NULL,
    agency_name VARCHAR(255),
    state_abbr VARCHAR(2),
    distance_miles NUMERIC(8,2),
    is_primary_hint BOOLEAN DEFAULT FALSE,
    data_vintage VARCHAR(10) NOT NULL DEFAULT '2026-Q3',
    selected_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (county_fips, ori, data_vintage)
);

CREATE INDEX IF NOT EXISTS idx_crime_agency_county
    ON crime_agency_selection (county_fips);

CREATE TABLE IF NOT EXISTS crime_offense_monthly (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_fips VARCHAR(5) NOT NULL,
    ori VARCHAR(10) NOT NULL DEFAULT '',
    offense_slug VARCHAR(8) NOT NULL,
    period_start DATE,
    period_end DATE,
    incidents_12mo NUMERIC(12,2),
    rate_12mo NUMERIC(12,4),
    state_benchmark_12mo NUMERIC(12,4),
    payload JSONB,
    data_vintage VARCHAR(10) NOT NULL DEFAULT '2026-Q3',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (county_fips, ori, offense_slug, data_vintage)
);

CREATE INDEX IF NOT EXISTS idx_crime_offense_county
    ON crime_offense_monthly (county_fips);

-- ── R2 Education ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schools_nces (
    ncessch VARCHAR(12) PRIMARY KEY,
    leaid VARCHAR(7),
    name VARCHAR(255),
    state_fips VARCHAR(2),
    county_fips VARCHAR(3),
    locale VARCHAR(10),
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    geometry GEOMETRY(Point, 4326),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schools_nces_county
    ON schools_nces (state_fips, county_fips);
CREATE INDEX IF NOT EXISTS idx_schools_nces_geom
    ON schools_nces USING GIST (geometry);

CREATE TABLE IF NOT EXISTS schools_urban (
    ncessch VARCHAR(12) NOT NULL,
    year INTEGER NOT NULL,
    enrollment INTEGER,
    teachers_fte NUMERIC(10,2),
    school_level VARCHAR(64),
    school_type VARCHAR(64),
    school_status VARCHAR(64),
    charter VARCHAR(32),
    magnet VARCHAR(32),
    virtual VARCHAR(32),
    payload JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (ncessch, year)
);

-- ── R3 Economic ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS acs_indicators (
    geoid VARCHAR(11) NOT NULL,
    geo_level VARCHAR(16) NOT NULL DEFAULT 'tract',
    median_hh_income NUMERIC(12,2),
    labor_force NUMERIC(12,2),
    employed NUMERIC(12,2),
    unemployed NUMERIC(12,2),
    total_population NUMERIC(14,2),
    acs_year VARCHAR(8) NOT NULL,
    payload JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (geoid, geo_level, acs_year)
);

ALTER TABLE acs_indicators ADD COLUMN IF NOT EXISTS total_population NUMERIC(14,2);

CREATE INDEX IF NOT EXISTS idx_acs_geoid ON acs_indicators (geoid);

CREATE TABLE IF NOT EXISTS bls_laus_county (
    county_fips VARCHAR(5) NOT NULL,
    series_id VARCHAR(32) NOT NULL,
    period VARCHAR(16) NOT NULL,
    unemployment_rate NUMERIC(8,4),
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (county_fips, series_id, period)
);

CREATE INDEX IF NOT EXISTS idx_bls_laus_county ON bls_laus_county (county_fips);
