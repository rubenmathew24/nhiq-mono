# 08 — Database Schema

> **Claude instructions:** This is the authoritative schema reference. Use it when writing SQLAlchemy models, Alembic migrations, or raw SQL. Run `alembic revision --autogenerate` after adding new ORM models. Never modify columns directly — always create a new migration.

---

## Technology

- **PostgreSQL 16** with **PostGIS 3.4** extension
- **Alembic** for migrations (in `apps/api/migrations/`)
- **SQLAlchemy 2.0** (async) as ORM
- Coordinates stored as `GEOMETRY(POINT, 4326)` or `GEOMETRY(MULTIPOLYGON, 4326)` (WGS84)
- UUIDs as primary keys throughout

---

## Full Schema

### Core / Spatial

```sql
-- PostGIS and UUID support (run once on DB creation)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────
-- Census tract boundaries (loaded by census ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE census_tracts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    geoid       VARCHAR(11) UNIQUE NOT NULL,   -- 11-digit FIPS (state+county+tract)
    state_fips  VARCHAR(2)  NOT NULL,
    county_fips VARCHAR(3)  NOT NULL,
    tract_fips  VARCHAR(6)  NOT NULL,
    geometry    GEOMETRY(MULTIPOLYGON, 4326),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_census_tracts_geoid    ON census_tracts(geoid);
CREATE INDEX idx_census_tracts_geometry ON census_tracts USING GIST(geometry);
CREATE INDEX idx_census_tracts_county   ON census_tracts(state_fips, county_fips);
```

### User & Auth

```sql
-- ─────────────────────────────────────────────────────────────
-- Users
-- ─────────────────────────────────────────────────────────────
CREATE TABLE users (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email                    VARCHAR(255) UNIQUE NOT NULL,
    hashed_password          TEXT,
    full_name                VARCHAR(255),
    tier                     VARCHAR(20) DEFAULT 'free'
                             CHECK (tier IN ('free','buyer','buyer_pro','agent','brokerage')),
    lookup_count_this_month  INTEGER DEFAULT 0,
    billing_cycle_start      TIMESTAMPTZ,
    stripe_customer_id       VARCHAR(255),
    stripe_subscription_id   VARCHAR(255),
    is_active                BOOLEAN DEFAULT true,
    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tier  ON users(tier);

-- Reset lookup counts monthly (run via scheduled worker or cron)
-- UPDATE users SET lookup_count_this_month = 0
-- WHERE billing_cycle_start <= NOW() - INTERVAL '1 month';
```

### Address & Scoring

```sql
-- ─────────────────────────────────────────────────────────────
-- Address lookup cache (dedup geocoding calls)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE address_lookups (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address_raw         TEXT NOT NULL,
    address_normalized  TEXT,
    latitude            NUMERIC(10,7),
    longitude           NUMERIC(10,7),
    geometry            GEOMETRY(POINT, 4326),
    geoid               VARCHAR(11) REFERENCES census_tracts(geoid),
    lookup_count        INTEGER DEFAULT 1,
    first_looked_up_at  TIMESTAMPTZ DEFAULT NOW(),
    last_looked_up_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_address_normalized ON address_lookups(address_normalized);
CREATE INDEX idx_address_geoid      ON address_lookups(geoid);
CREATE INDEX idx_address_geometry   ON address_lookups USING GIST(geometry);

-- ─────────────────────────────────────────────────────────────
-- Neighborhood scores (computed per census tract, per vintage)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE neighborhood_scores (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    geoid             VARCHAR(11) NOT NULL REFERENCES census_tracts(geoid),
    healthcare_score  NUMERIC(4,1) CHECK (healthcare_score BETWEEN 0 AND 100),
    safety_score      NUMERIC(4,1) CHECK (safety_score BETWEEN 0 AND 100),
    environment_score NUMERIC(4,1) CHECK (environment_score BETWEEN 0 AND 100),
    education_score   NUMERIC(4,1) CHECK (education_score BETWEEN 0 AND 100),
    economic_score    NUMERIC(4,1) CHECK (economic_score BETWEEN 0 AND 100),
    overall_score     NUMERIC(4,1) CHECK (overall_score BETWEEN 0 AND 100),
    data_vintage      VARCHAR(10),    -- e.g. "2024-Q4"
    computed_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(geoid, data_vintage)
);

CREATE INDEX idx_scores_geoid    ON neighborhood_scores(geoid);
CREATE INDEX idx_scores_vintage  ON neighborhood_scores(data_vintage);
CREATE INDEX idx_scores_overall  ON neighborhood_scores(overall_score);

-- ─────────────────────────────────────────────────────────────
-- Score history (for trend charts — Buyer Pro feature)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE score_history (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    geoid             VARCHAR(11) NOT NULL REFERENCES census_tracts(geoid),
    period            VARCHAR(10) NOT NULL,   -- "2022-Q1", "2023-Q1", etc.
    healthcare_score  NUMERIC(4,1),
    safety_score      NUMERIC(4,1),
    environment_score NUMERIC(4,1),
    education_score   NUMERIC(4,1),
    economic_score    NUMERIC(4,1),
    overall_score     NUMERIC(4,1),
    UNIQUE(geoid, period)
);
```

### Raw Ingested Data

```sql
-- ─────────────────────────────────────────────────────────────
-- EPA Air Quality (from epa ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE epa_aqi_readings (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_fips    VARCHAR(5) NOT NULL,
    parameter_code VARCHAR(10),
    parameter_name VARCHAR(100),
    aqi            INTEGER,
    category       VARCHAR(50),
    date_local     DATE NOT NULL,
    state_name     VARCHAR(50),
    county_name    VARCHAR(100),
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(county_fips, parameter_code, date_local)
);

CREATE INDEX idx_epa_county ON epa_aqi_readings(county_fips);
CREATE INDEX idx_epa_date   ON epa_aqi_readings(date_local);

-- ─────────────────────────────────────────────────────────────
-- Hospitals (from CMS ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE hospitals (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cms_provider_id     VARCHAR(10) UNIQUE NOT NULL,
    name                VARCHAR(255),
    address             TEXT,
    city                VARCHAR(100),
    state               VARCHAR(2),
    zip                 VARCHAR(10),
    county_name         VARCHAR(100),
    phone               VARCHAR(20),
    hospital_type       VARCHAR(100),
    star_rating         INTEGER CHECK (star_rating BETWEEN 1 AND 5),
    emergency_services  BOOLEAN DEFAULT false,
    trauma_level        VARCHAR(10),        -- I, II, III, IV, V, NULL
    latitude            NUMERIC(10,7),
    longitude           NUMERIC(10,7),
    geometry            GEOMETRY(POINT, 4326),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hospitals_geometry ON hospitals USING GIST(geometry);
CREATE INDEX idx_hospitals_state    ON hospitals(state);
CREATE INDEX idx_hospitals_er       ON hospitals(emergency_services);

-- ─────────────────────────────────────────────────────────────
-- Crime stats (from FBI ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE crime_stats (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ori                 VARCHAR(10),
    agency_name         VARCHAR(255),
    state_abbr          VARCHAR(2),
    county_fips         VARCHAR(5),
    year                INTEGER NOT NULL,
    population          INTEGER,
    violent_crime       INTEGER,
    property_crime      INTEGER,
    violent_crime_rate  NUMERIC(8,2),   -- per 100k population
    property_crime_rate NUMERIC(8,2),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ori, year)
);

CREATE INDEX idx_crime_county ON crime_stats(county_fips);
CREATE INDEX idx_crime_year   ON crime_stats(year);

-- ─────────────────────────────────────────────────────────────
-- FEMA National Risk Index (from FEMA ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE fema_risk (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_fips         VARCHAR(5) UNIQUE NOT NULL,
    county_name         VARCHAR(100),
    state_name          VARCHAR(50),
    -- Overall risk
    nri_id              INTEGER,
    risk_score          NUMERIC(6,2),
    risk_rating         VARCHAR(20),    -- Very High / High / Medium / Low / Very Low
    -- Individual hazard risk scores (0-100)
    flood_risk          NUMERIC(6,2),
    wildfire_risk       NUMERIC(6,2),
    earthquake_risk     NUMERIC(6,2),
    hurricane_risk      NUMERIC(6,2),
    tornado_risk        NUMERIC(6,2),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fema_county ON fema_risk(county_fips);

-- ─────────────────────────────────────────────────────────────
-- Schools (from NCES ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE schools (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nces_id         VARCHAR(20) UNIQUE NOT NULL,
    name            VARCHAR(255),
    state           VARCHAR(2),
    county_fips     VARCHAR(5),
    zip             VARCHAR(10),
    school_type     VARCHAR(50),    -- Elementary / Middle / High / K-12
    grade_low       VARCHAR(5),
    grade_high      VARCHAR(5),
    students        INTEGER,
    latitude        NUMERIC(10,7),
    longitude       NUMERIC(10,7),
    geometry        GEOMETRY(POINT, 4326),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_schools_geometry ON schools USING GIST(geometry);
CREATE INDEX idx_schools_county   ON schools(county_fips);

-- ─────────────────────────────────────────────────────────────
-- Property value trends (from Zillow ingestion worker)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE zillow_home_values (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    region_id    VARCHAR(20),
    region_name  VARCHAR(255),   -- ZIP code or metro area name
    region_type  VARCHAR(20),    -- zip / metro / city
    zip          VARCHAR(10),
    state        VARCHAR(2),
    period       DATE,           -- First day of the month
    zhvi         NUMERIC(12,2),  -- Zillow Home Value Index
    yoy_change   NUMERIC(6,4),   -- Year-over-year % change
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(region_id, period)
);

CREATE INDEX idx_zillow_zip    ON zillow_home_values(zip);
CREATE INDEX idx_zillow_period ON zillow_home_values(period);
```

### User Activity

```sql
-- ─────────────────────────────────────────────────────────────
-- Saved lookups per user
-- ─────────────────────────────────────────────────────────────
CREATE TABLE saved_lookups (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address_lookup_id UUID NOT NULL REFERENCES address_lookups(id),
    label             VARCHAR(255),
    notes             TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, address_lookup_id)
);

CREATE INDEX idx_saved_lookups_user ON saved_lookups(user_id);

-- ─────────────────────────────────────────────────────────────
-- API usage log (for rate limiting and billing)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE api_usage_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id),
    endpoint    VARCHAR(100),
    method      VARCHAR(10),
    geoid       VARCHAR(11),
    response_ms INTEGER,
    status_code INTEGER,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_log_user    ON api_usage_log(user_id);
CREATE INDEX idx_api_log_created ON api_usage_log(created_at);
```

---

## Common Queries

```sql
-- Get full neighborhood report for an address (given geoid)
SELECT
    ct.geoid,
    ns.overall_score,
    ns.healthcare_score,
    ns.safety_score,
    ns.environment_score,
    ns.education_score,
    ns.economic_score,
    ns.data_vintage,
    ns.computed_at
FROM census_tracts ct
JOIN neighborhood_scores ns ON ct.geoid = ns.geoid
WHERE ct.geoid = '06037201400'
  AND ns.data_vintage = '2024-Q4';

-- Find which census tract a point falls in
SELECT geoid
FROM census_tracts
WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(-118.2437, 34.0522), 4326));

-- Find nearest 5 hospitals to a point (with emergency services)
SELECT
    name,
    star_rating,
    ST_Distance(
        geometry::geography,
        ST_SetSRID(ST_MakePoint(-118.2437, 34.0522), 4326)::geography
    ) / 1609.34 AS distance_miles
FROM hospitals
WHERE emergency_services = true
ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(-118.2437, 34.0522), 4326)
LIMIT 5;

-- Average AQI by county for last 30 days
SELECT county_fips, AVG(aqi) as avg_aqi, COUNT(*) as reading_count
FROM epa_aqi_readings
WHERE date_local >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY county_fips
ORDER BY avg_aqi DESC;

-- Score trend for a tract (for trend chart)
SELECT period, overall_score, healthcare_score, safety_score
FROM score_history
WHERE geoid = '06037201400'
ORDER BY period ASC;
```

---

## Alembic Workflow

```bash
# Create a new migration after changing ORM models
cd apps/api
alembic revision --autogenerate -m "add schools table"

# Apply pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration state
alembic current

# Show migration history
alembic history --verbose
```

---

## Checklist

- [ ] PostGIS and uuid-ossp extensions enabled
- [ ] `census_tracts` table created with spatial index
- [ ] `users` table created
- [ ] `address_lookups` table created
- [ ] `neighborhood_scores` table created
- [ ] All raw ingestion tables created
- [ ] Initial Alembic migration generated and applied
- [ ] `alembic current` shows `head`
- [ ] Common queries run without errors
