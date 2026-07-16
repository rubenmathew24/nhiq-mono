# Data Model: Data Ingestion Workers

**Feature**: `002-data-ingestion-workers` | **Date**: 2026-07-14 (reopened)

Canonical schemas align with `docs/nhiq-design-main/08-database-schema.md` and `infra/sql/init.sql`. System of record: PostgreSQL + PostGIS.

Reopen adds CDE crime staging, NCES + Urban school tables, ACS indicators, and LAUS series (via `infra/sql/004_*.sql` slices as needed). Hospital ZIP centroids and Open-Meteo score-time fallback remain as in the MVP.

---

## Entities

### CensusTract

| Field | Type | Rules |
|-------|------|--------|
| id | UUID | PK, default generate |
| geoid | VARCHAR(11) | UNIQUE, NOT NULL — full tract GEOID |
| state_fips | VARCHAR(2) | NOT NULL |
| county_fips | VARCHAR(3) | NOT NULL (county portion; full county key = state+county) |
| tract_fips | VARCHAR(6) | NOT NULL |
| geometry | MULTIPOLYGON 4326 | REQUIRED for scoring / point-in-polygon |
| created_at | timestamptz | default now |

**Indexes**: unique geoid; GIST(geometry); `(state_fips, county_fips)`.

**Scope**: Fixture counties only after TIGER load + filter.

---

### EpaAqiReading

| Field | Type | Rules |
|-------|------|--------|
| id | UUID | PK |
| county_fips | VARCHAR(5) | NOT NULL — `SSCCC` |
| parameter_code | VARCHAR(10) | |
| parameter_name | VARCHAR(100) | |
| aqi | INTEGER | nullable if source missing |
| category | VARCHAR(50) | |
| date_local | DATE | NOT NULL |
| state_name | VARCHAR(50) | |
| county_name | VARCHAR(100) | |
| created_at | timestamptz | default now |

**Uniqueness**: `(county_fips, parameter_code, date_local)` — upsert on conflict.

**Scope**: Fixture counties only. May be sparse — scoring falls back to Open-Meteo.

---

### Hospital

| Field | Type | Rules |
|-------|------|--------|
| id | UUID | PK |
| cms_provider_id | VARCHAR(10) | UNIQUE NOT NULL |
| name | VARCHAR(255) | |
| address / city / state / zip | text fields | CMS aliases |
| county_name | VARCHAR(100) | |
| phone | VARCHAR(20) | |
| hospital_type | VARCHAR(100) | |
| star_rating | INTEGER 1–5 | NULL if “Not Available” |
| emergency_services | BOOLEAN | default false |
| trauma_level | VARCHAR(10) | optional / null |
| latitude / longitude | NUMERIC(10,7) | Often ZIP geocode |
| geometry | POINT 4326 | set from lon/lat when valid |
| updated_at | timestamptz | bump on upsert |

**Scope**: Fixture-state filter.

---

### CrimeAgencySelection (R1)

Selected ORIs per fixture county / bootstrap point.

| Field | Type | Rules |
|-------|------|--------|
| id | UUID | PK |
| county_fips | VARCHAR(5) | NOT NULL — fixture county `SSCCC` |
| ori | VARCHAR(10) | NOT NULL |
| agency_name | VARCHAR(255) | |
| state_abbr | VARCHAR(2) | |
| distance_miles | NUMERIC | from bootstrap point |
| is_primary_hint | BOOLEAN | UX hint only; merge uses all selected |
| selected_at | timestamptz | default now |
| data_vintage | VARCHAR(10) | e.g. `2026-Q3` |

**Uniqueness**: `(county_fips, ori, data_vintage)`.

---

### CrimeOffenseMonthly (R1)

Agency (or merged county-aggregate) offense series + benchmarks from CDE charts.

| Field | Type | Rules |
|-------|------|--------|
| id | UUID | PK |
| county_fips | VARCHAR(5) | NOT NULL |
| ori | VARCHAR(10) | nullable if row is county-merged aggregate |
| offense_slug | VARCHAR(8) | e.g. `HOM`,`ROB`,`ASS` |
| period_start / period_end | DATE | chart window |
| incidents_12mo | NUMERIC | nullable |
| rate_12mo | NUMERIC | nullable |
| state_benchmark_12mo | NUMERIC | nullable |
| payload | JSONB | optional compact probe-shaped excerpt |
| data_vintage | VARCHAR(10) | |
| updated_at | timestamptz | |

**Uniqueness**: `(county_fips, COALESCE(ori,''), offense_slug, data_vintage)` (implement with explicit empty-string or sentinel).

**Legacy**: `crime_stats` (ORI+year) may remain for forward-compat but R1 scoring SHOULD prefer CDE monthly/benchmark tables.

---

### SchoolNces (R2)

| Field | Type | Rules |
|-------|------|--------|
| ncessch | VARCHAR(12) | PK — NCES school id |
| leaid | VARCHAR(7) | |
| name | VARCHAR(255) | |
| state_fips / county_fips | VARCHAR | from STFIP/CNTY |
| locale | VARCHAR(10) | NCES locale code |
| latitude / longitude | NUMERIC | |
| geometry | POINT 4326 | |
| updated_at | timestamptz | |

**Scope**: Schools in fixture states/counties.

---

### SchoolUrban (R2)

| Field | Type | Rules |
|-------|------|--------|
| ncessch | VARCHAR(12) | PK / FK logical → SchoolNces |
| year | INTEGER | directory year |
| enrollment | INTEGER | nullable |
| teachers_fte | NUMERIC | nullable |
| school_level / school_type / school_status | VARCHAR | |
| charter / magnet / virtual | BOOLEAN or VARCHAR | as ingested |
| payload | JSONB | optional extras |
| updated_at | timestamptz | |

**Uniqueness**: `(ncessch, year)` if multi-year retained; else latest year wins.

---

### AcsIndicator (R3)

| Field | Type | Rules |
|-------|------|--------|
| geoid | VARCHAR(11) | tract GEOID preferred |
| geo_level | VARCHAR(16) | `tract` \| `zcta` \| `county` |
| median_hh_income | NUMERIC | e.g. B19013 |
| labor_force / employed / unemployed | NUMERIC | optional ACS labor vars |
| acs_year | VARCHAR(8) | vintage label of ACS release |
| payload | JSONB | optional |
| updated_at | timestamptz | |

**Uniqueness**: `(geoid, geo_level, acs_year)`.

---

### BlsLausCounty (R3)

| Field | Type | Rules |
|-------|------|--------|
| county_fips | VARCHAR(5) | PK portion |
| series_id | VARCHAR(32) | e.g. `LAUCN…000000003` |
| period | VARCHAR(16) | year-month or annual key |
| unemployment_rate | NUMERIC | |
| fetched_at | timestamptz | |

**Uniqueness**: `(county_fips, series_id, period)`.

---

### NeighborhoodScore

| Field | Type | Rules |
|-------|------|--------|
| id | UUID | PK |
| geoid | VARCHAR(11) | FK → census_tracts.geoid |
| healthcare_score | NUMERIC(4,1) | 0–100 |
| safety_score | NUMERIC(4,1) | placeholder until R1 |
| environment_score | NUMERIC(4,1) | 0–100 |
| education_score | NUMERIC(4,1) | placeholder until R2 |
| economic_score | NUMERIC(4,1) | placeholder until R3 |
| overall_score | NUMERIC(4,1) | weighted composite |
| data_vintage | VARCHAR(10) | `2026-Q3` |
| score_sources | JSONB | NOT NULL default `{}` |
| computed_at | timestamptz | |

**Uniqueness**: `(geoid, data_vintage)`.

**Weights**: healthcare 0.25, safety 0.25, education 0.20, environment 0.15, economic 0.15.

**Placeholders (pre-phase)**: safety 65.0, education 70.0, economic 60.0.

**`score_sources` shape** (example after R1+R2 partial):

```json
{
  "environment": { "source_id": "open_meteo", "reason": "fallback_no_epa", "avg_aqi": 56.5 },
  "healthcare": { "source_id": "cms_hospital_general_info", "reason": "nearest_er", "nearest_er_miles": 3.4 },
  "safety": { "source_id": "fbi_cde", "reason": "agency_aggregate", "ori_count": 3 },
  "education": {
    "source_id": "nces_urban",
    "contributors": ["nces_school_data", "urban_school_data"],
    "reason": "nearest_school_blend"
  },
  "economic": { "source_id": "placeholder", "reason": "economic_pending_source_worker" }
}
```

Stable ids: `epa_aqs` | `open_meteo` | `default` | `cms_hospital_general_info` | `fbi_cde` | `nces_urban` | `acs_bls_laus` | `placeholder`.

---

### CanonicalTestAddress (fixture config)

Checked-in under `workers/ingest/fixtures/` — not required as a DB table.

---

## Relationships

```text
CanonicalTestAddress --(geocode)--> point
point --(within)--> CensusTract (fixture county)
CensusTract 1──* NeighborhoodScore (per vintage)
CensusTract.county --reads--> EpaAqiReading
CensusTract --spatial nearest--> Hospital
CensusTract.county --agency selection--> CrimeAgencySelection --> CrimeOffenseMonthly --> safety_score
CensusTract --nearest--> SchoolNces --(ncessch)--> SchoolUrban --> education_score
CensusTract --reads--> AcsIndicator
CensusTract.county --reads--> BlsLausCounty --> economic_score
AddressLookup.geoid --> NeighborhoodScore
```

---

## Validation / idempotency

- All raw tables: upsert on natural keys; re-runs must not duplicate.
- Census: upsert on `geoid`.
- Dual-source phases: partial source failure must not claim dual-success in provenance.
- Missing inputs after a phase lands: documented default + provenance (not silent old placeholder constants).

---

## Migration notes

1. MVP tables in `init.sql` / `002_raw_ingest_tables.sql` / `003_score_sources.sql`.
2. Reopen: apply `004_safety_education_economic.sql` (or sliced 004a CDE / 004b schools / 004c economic) on existing volumes.
3. Alembic optional follow-up.
