-- Keep in sync with infra/sql/init.sql / 002_raw_ingest_tables.sql
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