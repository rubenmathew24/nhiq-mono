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

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT,
    full_name VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'free',
    lookup_count_this_month INTEGER DEFAULT 0,
    billing_cycle_start TIMESTAMPTZ,
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Saved lookups per user
CREATE TABLE IF NOT EXISTS saved_lookups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address_lookup_id UUID NOT NULL REFERENCES address_lookups(id),
    label VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
