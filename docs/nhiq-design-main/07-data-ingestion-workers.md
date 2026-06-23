# 07 — Data Ingestion Workers

> **Claude instructions:** Each worker is a standalone Python script that fetches from one government data source, transforms it, and writes to PostgreSQL. Workers run as Azure Container Apps Jobs on a schedule. Build workers in this priority order: EPA (easiest) → Census → CMS → FBI → FEMA → Zillow.

---

## Worker Structure (Each Source)

```
workers/ingest/<source>/
├── __init__.py
├── run.py          # Entry point — calls fetch → transform → load
├── client.py       # HTTP client for this specific API
├── transform.py    # Data cleaning and normalization
└── schema.sql      # Source-specific table(s) if needed
```

---

## Shared Base Class (`workers/ingest/base.py`)

Already defined in `docs/01-monorepo-setup.md`. All workers extend `BaseIngestionWorker`.

---

## Priority 1: EPA Air Quality (`workers/ingest/epa/`)

**API:** EPA Air Quality System (AQS)
**Auth:** Email + API key (register at https://aqs.epa.gov/data/api/signup)
**Schedule:** Daily at 2am UTC
**Writes to table:** `epa_aqi_readings`

### `workers/ingest/epa/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS epa_aqi_readings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_fips VARCHAR(5) NOT NULL,       -- state + county FIPS
    parameter_code VARCHAR(10),            -- e.g. "44201" = Ozone
    parameter_name VARCHAR(100),
    aqi INTEGER,
    category VARCHAR(50),                  -- Good/Moderate/Unhealthy...
    date_local DATE NOT NULL,
    state_name VARCHAR(50),
    county_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(county_fips, parameter_code, date_local)
);

CREATE INDEX IF NOT EXISTS idx_epa_aqi_county ON epa_aqi_readings(county_fips);
CREATE INDEX IF NOT EXISTS idx_epa_aqi_date ON epa_aqi_readings(date_local);
```

### `workers/ingest/epa/client.py`

```python
import httpx
import os
from datetime import date, timedelta

EPA_BASE = "https://aqs.epa.gov/data/api"


async def fetch_daily_aqi(state_code: str, start_date: date, end_date: date) -> list[dict]:
    """Fetch daily AQI summary for a state."""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            f"{EPA_BASE}/dailyData/byState",
            params={
                "email": os.getenv("EPA_AQS_EMAIL"),
                "key": os.getenv("EPA_AQS_KEY"),
                "param": "44201,88101,42401",   # Ozone, PM2.5, SO2
                "bdate": start_date.strftime("%Y%m%d"),
                "edate": end_date.strftime("%Y%m%d"),
                "state": state_code,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("Data", [])
```

### `workers/ingest/epa/transform.py`

```python
def transform_aqi_records(raw_records: list[dict]) -> list[dict]:
    """Normalize raw EPA API records to our DB schema."""
    results = []
    for r in raw_records:
        try:
            results.append({
                "county_fips": f"{r['state_code']}{r['county_code']}",
                "parameter_code": r.get("parameter_code"),
                "parameter_name": r.get("parameter"),
                "aqi": int(r["aqi"]) if r.get("aqi") else None,
                "category": r.get("category"),
                "date_local": r.get("date_local"),
                "state_name": r.get("state"),
                "county_name": r.get("county"),
            })
        except (KeyError, ValueError):
            continue
    return results
```

### `workers/ingest/epa/run.py`

```python
import asyncio
import asyncpg
import os
from datetime import date, timedelta
from client import fetch_daily_aqi
from transform import transform_aqi_records

# All 50 state codes
US_STATE_CODES = [
    "01","02","04","05","06","08","09","10","11","12","13","15","16","17","18",
    "19","20","21","22","23","24","25","26","27","28","29","30","31","32","33",
    "34","35","36","37","38","39","40","41","42","44","45","46","47","48","49",
    "50","51","53","54","55","56",
]


async def run():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    # Fetch yesterday's data
    yesterday = date.today() - timedelta(days=1)
    total = 0

    for state_code in US_STATE_CODES:
        raw = await fetch_daily_aqi(state_code, yesterday, yesterday)
        records = transform_aqi_records(raw)

        if records:
            await conn.executemany("""
                INSERT INTO epa_aqi_readings
                    (county_fips, parameter_code, parameter_name, aqi, category, date_local, state_name, county_name)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (county_fips, parameter_code, date_local) DO UPDATE
                    SET aqi = EXCLUDED.aqi, category = EXCLUDED.category
            """, [
                (r["county_fips"], r["parameter_code"], r["parameter_name"],
                 r["aqi"], r["category"], r["date_local"], r["state_name"], r["county_name"])
                for r in records
            ])
            total += len(records)

        print(f"State {state_code}: {len(records)} records")

    await conn.close()
    print(f"EPA ingestion complete. Total records: {total}")


if __name__ == "__main__":
    asyncio.run(run())
```

---

## Priority 2: Census Tract Boundaries (`workers/ingest/census/`)

**Source:** Census TIGER/Line shapefiles (no API key needed)
**Schedule:** Monthly
**Writes to table:** `census_tracts` (geometry)

### `workers/ingest/census/run.py`

```python
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine
import os

TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_{state_fips}_tract.zip"

US_STATE_FIPS = [
    "01","02","04","05","06","08","09","10","11","12","13","15","16","17","18",
    "19","20","21","22","23","24","25","26","27","28","29","30","31","32","33",
    "34","35","36","37","38","39","40","41","42","44","45","46","47","48","49",
    "50","51","53","54","55","56",
]


def run():
    engine = create_engine(os.getenv("DATABASE_URL"))

    for state_fips in US_STATE_FIPS:
        url = TIGER_URL.format(state_fips=state_fips)
        print(f"Fetching tracts for state {state_fips}...")

        try:
            gdf = gpd.read_file(url)
            gdf = gdf.to_crs("EPSG:4326")   # Ensure WGS84

            gdf["geoid"] = gdf["GEOID"]
            gdf["state_fips"] = gdf["STATEFP"]
            gdf["county_fips"] = gdf["COUNTYFP"]
            gdf["tract_fips"] = gdf["TRACTCE"]

            gdf[["geoid", "state_fips", "county_fips", "tract_fips", "geometry"]].to_postgis(
                "census_tracts",
                engine,
                if_exists="append",
                index=False,
                chunksize=500,
            )
            print(f"  Loaded {len(gdf)} tracts")

        except Exception as e:
            print(f"  Error for state {state_fips}: {e}")

    print("Census tract ingestion complete")


if __name__ == "__main__":
    run()
```

---

## Priority 3: CMS Hospital Data (`workers/ingest/cms/`)

**Source:** CMS Provider Data Catalog — Hospital General Information
**Auth:** None (public)
**Schedule:** Monthly
**Writes to table:** `hospitals`

```sql
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
    star_rating INTEGER,            -- 1-5, NULL if not rated
    emergency_services BOOLEAN,
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    geometry GEOMETRY(POINT, 4326),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hospitals_geometry ON hospitals USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_hospitals_state ON hospitals(state);
```

### `workers/ingest/cms/run.py`

```python
import httpx
import asyncpg
import asyncio
import os

CMS_URL = "https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0"


async def run():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    async with httpx.AsyncClient(timeout=120) as client:
        offset = 0
        total = 0

        while True:
            response = await client.get(CMS_URL, params={
                "limit": 1000,
                "offset": offset,
                "keys": "true",
            })
            response.raise_for_status()
            data = response.json()
            records = data.get("results", [])

            if not records:
                break

            for r in records:
                lat = float(r.get("lat", 0) or 0)
                lng = float(r.get("lng", 0) or 0)
                star = r.get("hospital_overall_rating")

                await conn.execute("""
                    INSERT INTO hospitals (
                        cms_provider_id, name, address, city, state, zip,
                        phone, hospital_type, star_rating, emergency_services,
                        latitude, longitude,
                        geometry
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,
                              ST_SetSRID(ST_MakePoint($12, $11), 4326))
                    ON CONFLICT (cms_provider_id) DO UPDATE SET
                        star_rating = EXCLUDED.star_rating,
                        updated_at = NOW()
                """,
                    r.get("facility_id"), r.get("facility_name"),
                    r.get("address"), r.get("city"), r.get("state"),
                    r.get("zip_code"), r.get("phone_number"),
                    r.get("hospital_type"),
                    int(star) if star and star != "Not Available" else None,
                    r.get("emergency_services") == "Yes",
                    lat, lng,
                )

            total += len(records)
            offset += 1000
            print(f"Loaded {total} hospitals so far...")

    await conn.close()
    print(f"CMS ingestion complete. Total hospitals: {total}")


if __name__ == "__main__":
    asyncio.run(run())
```

---

## Priority 4: FBI Crime Data (`workers/ingest/fbi/`)

**API:** FBI Crime Data Explorer
**Auth:** API key — register at https://api.usa.gov/signup
**Schedule:** Monthly
**Writes to table:** `crime_stats`

```sql
CREATE TABLE IF NOT EXISTS crime_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ori VARCHAR(10),                  -- Agency identifier
    agency_name VARCHAR(255),
    state_abbr VARCHAR(2),
    year INTEGER,
    population INTEGER,
    violent_crime INTEGER,
    property_crime INTEGER,
    violent_crime_rate NUMERIC(8,2),  -- per 100k
    property_crime_rate NUMERIC(8,2),
    county_fips VARCHAR(5),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ori, year)
);
```

---

## Score Computation from Raw Data

After ingestion, the scoring pipeline reads from all raw tables and computes `neighborhood_scores`.

### Scoring Logic (`workers/scoring/compute.py`)

```python
"""
Score computation: reads raw ingested data, computes 0-100 scores per census tract,
writes to neighborhood_scores table.

Score methodology:
- Each raw metric is normalized to 0-100 using percentile ranking across all tracts
- Subscores are weighted averages of their component metrics
- Overall score is a weighted average of subscores
"""
import asyncpg
import asyncio
import os

SCORE_WEIGHTS = {
    "healthcare": 0.25,
    "safety": 0.25,
    "education": 0.20,
    "environment": 0.15,
    "economic": 0.15,
}


async def compute_healthcare_score(conn, geoid: str) -> float:
    """
    Inputs:
    - Hospital star rating (nearest 3 hospitals, average)
    - Distance to nearest ER (drive time proxy via haversine)
    - Trauma center availability (within 30 miles)
    Returns: 0-100 score
    """
    # Query nearest hospitals using PostGIS ST_Distance
    result = await conn.fetchrow("""
        SELECT
            AVG(h.star_rating) as avg_stars,
            MIN(ST_Distance(
                h.geometry::geography,
                (SELECT ST_Centroid(geometry)::geography FROM census_tracts WHERE geoid = $1)
            )) / 1609.34 as nearest_er_miles    -- convert meters to miles
        FROM hospitals h
        WHERE h.emergency_services = true
        ORDER BY h.geometry <-> (
            SELECT ST_Centroid(geometry) FROM census_tracts WHERE geoid = $1
        )
        LIMIT 3
    """, geoid)

    if not result:
        return 50.0   # Default to average if no data

    avg_stars = result["avg_stars"] or 3.0
    nearest_miles = result["nearest_er_miles"] or 10.0

    # Star rating: 1-5 → 0-100
    star_score = (avg_stars - 1) / 4 * 100

    # Distance: < 2 miles = 100, > 20 miles = 0 (linear)
    distance_score = max(0, 100 - (nearest_miles - 2) * (100 / 18))

    return round(star_score * 0.6 + distance_score * 0.4, 1)


async def compute_environment_score(conn, geoid: str) -> float:
    """
    Inputs:
    - Average AQI over last 30 days for the tract's county
    - FEMA flood/wildfire/earthquake risk (when available)
    Returns: 0-100 score (higher = better environment)
    """
    # Get county FIPS from geoid (first 5 chars)
    county_fips = geoid[:5]

    result = await conn.fetchrow("""
        SELECT AVG(aqi) as avg_aqi
        FROM epa_aqi_readings
        WHERE county_fips = $1
          AND date_local >= CURRENT_DATE - INTERVAL '30 days'
    """, county_fips)

    avg_aqi = result["avg_aqi"] if result else 50.0

    # AQI: 0-50 = Good → 100 score, 0-300+ linear decline
    aqi_score = max(0, 100 - (avg_aqi / 3))

    return round(aqi_score, 1)


async def compute_and_store_scores(geoid: str):
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    try:
        healthcare = await compute_healthcare_score(conn, geoid)
        environment = await compute_environment_score(conn, geoid)
        # TODO: safety, education, economic (same pattern)
        safety = 65.0       # Placeholder
        education = 70.0    # Placeholder
        economic = 60.0     # Placeholder

        overall = (
            healthcare * SCORE_WEIGHTS["healthcare"] +
            safety * SCORE_WEIGHTS["safety"] +
            education * SCORE_WEIGHTS["education"] +
            environment * SCORE_WEIGHTS["environment"] +
            economic * SCORE_WEIGHTS["economic"]
        )

        await conn.execute("""
            INSERT INTO neighborhood_scores
                (geoid, healthcare_score, safety_score, environment_score,
                 education_score, economic_score, overall_score, data_vintage)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (geoid, data_vintage) DO UPDATE SET
                healthcare_score = EXCLUDED.healthcare_score,
                safety_score = EXCLUDED.safety_score,
                environment_score = EXCLUDED.environment_score,
                education_score = EXCLUDED.education_score,
                economic_score = EXCLUDED.economic_score,
                overall_score = EXCLUDED.overall_score,
                computed_at = NOW()
        """, geoid, healthcare, safety, environment, education, economic,
             round(overall, 1), "2024-Q4")

    finally:
        await conn.close()
```

---

## Testing Workers Locally

```bash
# Run EPA worker against local DB
cd neighborhoodiq
docker compose up db -d   # Start just the DB

docker compose run --rm worker-epa

# Or run directly with venv
cd workers/ingest
python -m epa.run
```

---

## Checklist

- [ ] `workers/ingest/base.py` created
- [ ] EPA worker fetches, transforms, and loads AQI data
- [ ] Census worker loads tract boundaries with PostGIS geometry
- [ ] CMS worker loads hospital data with spatial points
- [ ] FBI worker skeleton created (full implementation next)
- [ ] Scoring worker computes healthcare and environment scores
- [ ] All workers run without error against local Docker DB
- [ ] Azure Container Apps Jobs created for each worker
