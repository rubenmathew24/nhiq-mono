-- Keep in sync with infra/sql/init.sql / 002_raw_ingest_tables.sql
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