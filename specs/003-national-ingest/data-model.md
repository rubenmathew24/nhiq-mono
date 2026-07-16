# Data Model: National Ingest

## Table: `geo_counties`

County registry for national scope, FBI points, and status denominators.

| Column | Type | Notes |
|--------|------|-------|
| county_fips | CHAR(5) PK | SSCCC |
| state_fips | CHAR(2) | NOT NULL |
| county_name | TEXT | |
| state_abbr | TEXT | USPS |
| centroid_lat | DOUBLE PRECISION | from INTPTLAT or polygon centroid |
| centroid_lon | DOUBLE PRECISION | from INTPTLON or polygon centroid |
| source | TEXT | e.g. `tiger2023` |
| updated_at | TIMESTAMPTZ | |

Indexes: `(state_fips)`, optional GiST later unused in v1.

## Existing tables (unchanged schemas)

Checkpoint “done” uses existing grains:

| Worker | Done when |
|--------|-----------|
| geo | row in `geo_counties` |
| census | ≥1 `census_tracts` for county |
| epa | ≥1 `epa_aqi_readings` for county |
| cms | ≥1 `hospitals` for state (state grain) |
| fbi | ≥1 `crime_agency_selection` for county |
| nces | ≥1 `schools_nces` for county |
| urban | joinable urban for county’s NCES schools |
| acs | ≥1 ACS tract row for county |
| bls | ≥1 `bls_laus_county` for county |
| scoring | tracts with `score_sources.safety.source_id = 'fbi_cde'` / tracts in county (national status); skip-done at county if all tracts scored with fbi_cde |

## `ingest_status_snapshot`

Unchanged shape; `scope=national` rows become real.
