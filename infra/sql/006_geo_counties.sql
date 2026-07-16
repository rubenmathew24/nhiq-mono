-- County registry for national ingest (centroids + status denominator).
-- Apply:
--   docker compose exec -T db psql -U postgres -d neighborhoodiq < infra/sql/006_geo_counties.sql

CREATE TABLE IF NOT EXISTS geo_counties (
    county_fips CHAR(5) PRIMARY KEY,
    state_fips CHAR(2) NOT NULL,
    county_name TEXT,
    state_abbr TEXT,
    centroid_lat DOUBLE PRECISION,
    centroid_lon DOUBLE PRECISION,
    source TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geo_counties_state
    ON geo_counties (state_fips);
