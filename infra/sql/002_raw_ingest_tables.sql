-- One-shot apply for existing Compose volumes that already ran init.sql.
-- Usage:
--   docker compose exec -T db psql -U postgres -d neighborhoodiq < infra/sql/002_raw_ingest_tables.sql
--
-- Fresh volumes pick these up from infra/sql/init.sql automatically.

CREATE INDEX IF NOT EXISTS idx_census_tracts_county ON census_tracts(state_fips, county_fips);

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