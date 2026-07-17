-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Census tracts (spatial)
CREATE TABLE IF NOT EXISTS census_tracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    geoid VARCHAR(11) UNIQUE NOT NULL,
    state_fips VARCHAR(2) NOT NULL,
    county_fips VARCHAR(3) NOT NULL,
    tract_fips VARCHAR(6) NOT NULL,
    geometry GEOMETRY(MULTIPOLYGON, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_census_tracts_geoid ON census_tracts(geoid);
CREATE INDEX IF NOT EXISTS idx_census_tracts_geometry ON census_tracts USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_census_tracts_county ON census_tracts(state_fips, county_fips);

-- Neighborhood scores (cached per tract)
CREATE TABLE IF NOT EXISTS neighborhood_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    geoid VARCHAR(11) NOT NULL REFERENCES census_tracts(geoid),
    healthcare_score NUMERIC(4,1),
    safety_score NUMERIC(4,1),
    environment_score NUMERIC(4,1),
    education_score NUMERIC(4,1),
    economic_score NUMERIC(4,1),
    overall_score NUMERIC(4,1),
    data_vintage VARCHAR(10),
    -- Per-dimension provenance for future "show sources" UI (JSONB object).
    -- Example: {"environment":{"source_id":"epa_aqs","reason":"primary","avg_aqi":42.1,"distinct_days":28}}
    score_sources JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Sub-scores + expand stats for report accordion (see 007_report_detail.sql).
    score_detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(geoid, data_vintage)
);

-- Address lookup cache
CREATE TABLE IF NOT EXISTS address_lookups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address_raw TEXT NOT NULL,
    address_normalized TEXT,
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    geoid VARCHAR(11),
    lookup_count INTEGER DEFAULT 1,
    first_looked_up_at TIMESTAMPTZ DEFAULT NOW(),
    last_looked_up_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_address_lookups_address ON address_lookups(address_normalized);

-- Users (auth)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT,
    full_name VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'free'
        CHECK (tier IN ('free', 'buyer', 'buyer_pro', 'agent', 'brokerage')),
    lookup_count_this_month INTEGER DEFAULT 0,
    billing_cycle_start TIMESTAMPTZ,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);

-- Saved lookups per user (dashboard history)
CREATE TABLE IF NOT EXISTS saved_lookups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address_lookup_id UUID NOT NULL REFERENCES address_lookups(id),
    label VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, address_lookup_id)
);

CREATE INDEX IF NOT EXISTS idx_saved_lookups_user ON saved_lookups(user_id);

-- ─────────────────────────────────────────────────────────────
-- EPA Air Quality (from epa ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS epa_aqi_readings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_fips VARCHAR(5) NOT NULL,
    parameter_code VARCHAR(10),
    parameter_name VARCHAR(100),
    aqi INTEGER,
    category VARCHAR(50),
    date_local DATE NOT NULL,
    state_name VARCHAR(50),
    county_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(county_fips, parameter_code, date_local)
);

CREATE INDEX IF NOT EXISTS idx_epa_aqi_county ON epa_aqi_readings(county_fips);
CREATE INDEX IF NOT EXISTS idx_epa_aqi_date ON epa_aqi_readings(date_local);

-- ─────────────────────────────────────────────────────────────
-- Hospitals (from CMS ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hospitals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cms_provider_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(10),
    county_name VARCHAR(100),
    phone VARCHAR(20),
    hospital_type VARCHAR(100),
    star_rating INTEGER CHECK (star_rating IS NULL OR star_rating BETWEEN 1 AND 5),
    emergency_services BOOLEAN DEFAULT false,
    trauma_level VARCHAR(10),
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    geometry GEOMETRY(POINT, 4326),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hospitals_geometry ON hospitals USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_hospitals_state ON hospitals(state);
CREATE INDEX IF NOT EXISTS idx_hospitals_er ON hospitals(emergency_services);

-- ─────────────────────────────────────────────────────────────
-- Crime stats (FBI worker target; skeleton may leave empty)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crime_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ori VARCHAR(10),
    agency_name VARCHAR(255),
    state_abbr VARCHAR(2),
    county_fips VARCHAR(5),
    year INTEGER NOT NULL,
    population INTEGER,
    violent_crime INTEGER,
    property_crime INTEGER,
    violent_crime_rate NUMERIC(8,2),
    property_crime_rate NUMERIC(8,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ori, year)
);

CREATE INDEX IF NOT EXISTS idx_crime_county ON crime_stats(county_fips);
CREATE INDEX IF NOT EXISTS idx_crime_year ON crime_stats(year);
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

-- Idempotent for DBs created before total_population existed
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

-- ── R4 Report detail (FEMA NRI + CMS Timely) ─────────────────
CREATE TABLE IF NOT EXISTS fema_nri_tracts (
    geoid VARCHAR(11) PRIMARY KEY,
    state_fips VARCHAR(2),
    county_fips VARCHAR(3),
    risk_score NUMERIC(12,4),
    risk_rating VARCHAR(64),
    eal_score NUMERIC(12,4),
    sovi_score NUMERIC(12,4),
    resl_score NUMERIC(12,4),
    hazards JSONB NOT NULL DEFAULT '{}'::jsonb,
    data_vintage VARCHAR(10) NOT NULL DEFAULT '2026-Q3',
    payload JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_fema_nri_county ON fema_nri_tracts (state_fips, county_fips);

CREATE TABLE IF NOT EXISTS hospital_timely_measures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cms_provider_id VARCHAR(10) NOT NULL,
    measure_id VARCHAR(32) NOT NULL,
    measure_name VARCHAR(255),
    score_value NUMERIC(12,4),
    score_text VARCHAR(64),
    sample NUMERIC(12,2),
    footnote TEXT,
    state_score NUMERIC(12,4),
    national_score NUMERIC(12,4),
    start_date DATE,
    end_date DATE,
    data_vintage VARCHAR(10) NOT NULL DEFAULT '2026-Q3',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (cms_provider_id, measure_id, data_vintage)
);
CREATE INDEX IF NOT EXISTS idx_timely_provider ON hospital_timely_measures (cms_provider_id);
