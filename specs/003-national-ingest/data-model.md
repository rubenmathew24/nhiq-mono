# Data Model: National Ingest

**Feature**: `003-national-ingest`

No new tables beyond existing migrations (`006_geo_counties.sql`, `007_report_detail.sql`, ingest/score tables from 002/004). Behavior = registry + checkpoints + report-detail completeness + status/continuous semantics.

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

Indexes: `(state_fips)`.

Empty or incomplete registry for included 50+DC → fail closed for national continuous/status success.

## Table: `census_tracts` (shared with 002; land/water amend)

National census worker writes the same table as local fixture ingest. Additive columns (see [`002` data-model](../002-data-ingestion-workers/data-model.md)):

| Column | Type | Notes |
|--------|------|-------|
| aland | BIGINT NULL | TIGER land area m²; `0` = water-only |
| awater | BIGINT NULL | TIGER water area m² |

**Completeness**: Census checkpoint still “≥1 tract for county.” After migration, force or backfill census for counties whose rows have NULL `aland`/`awater` if Discover needs water-only filtering. Do **not** drop water-only tracts from the warehouse.

## Report-detail entities (reuse; schema `007_report_detail.sql`)

| Entity | Storage | Role |
|--------|---------|------|
| NeighborhoodScore | `neighborhood_scores` | Category scores + `score_detail` JSONB |
| FemaNriTract | `fema_nri_tracts` | Tract hazard / composite risk (bulk NRI CSV) |
| HospitalTimelyMeasure | `hospital_timely_measures` | Facility timely-care / ER wait |
| AcsIndicator | `acs_indicators` | Labor/income + **`total_population`** (B01003) |

### Identity / uniqueness

- `neighborhood_scores`: `(geoid, data_vintage)`
- `fema_nri_tracts`: `geoid` PK
- `hospital_timely_measures`: `(cms_provider_id, measure_id, data_vintage)`
- `acs_indicators`: `(geoid, geo_level, acs_year)`

## Checkpoint / completeness rules (inventory)

| Worker | Unit done when |
|--------|----------------|
| geo | row in `geo_counties` |
| census | ≥1 `census_tracts` for county |
| epa | ≥1 `epa_aqi_readings` for county |
| cms | ≥1 `hospitals` for state (state grain) |
| fbi | ≥1 `crime_agency_selection` for county |
| nces | ≥1 `schools_nces` for county |
| urban | joinable urban for county’s NCES schools (skip-done on schools) |
| **acs** | Tract rows exist for county **and** `total_population IS NOT NULL`; state geo_level pop when state in scope |
| bls | ≥1 `bls_laus_county` for county |
| **fema** | Every census tract geoid in county has a `fema_nri_tracts` row |
| **cms_timely** | State done when in-scope hospitals have timely measures for active vintage (or documented empty after worker pass) |
| **scoring** | Every tract in county has `score_sources.safety.source_id = fbi_cde` **and** non-empty `score_detail` for active vintage |

## Status semantics (national)

| Job | Done | Total |
|-----|------|-------|
| Most county-grain jobs | Counties with required rows | `COUNT(*)` from `geo_counties` (50+DC) |
| **scoring** | Counties where every tract has fbi_cde + non-empty `score_detail` | Same national county count |
| cms / cms_timely | State-grain | Included state count in universe |
| EPA (coverage product) | Monitor-county rules may apply in public coverage UI; ingest status uses documented job grain |

## State classes (orchestrator)

| Class | Meaning |
|-------|---------|
| **A — Report-detail backfill** | Base workers complete for all counties in state; at least one of acs-pop / fema / cms_timely / scoring-detail still gapped |
| **B — Virgin / other** | Any base-pipeline gap remains |
| **Done** | No pipeline gaps |

Selection (normal gap-fill / continuous, no force, no exclusive filter): process A before B.

## `ingest_status_snapshot`

Unchanged shape; `scope=national` rows are real. Console log line = metrics only; Postgres retains full `detail`.

## Orchestrator run state (ephemeral)

Not persisted: continuous loop clock, current worker, `ORCH_BATCH_STATES` list, exit code. Observed via logs (`orch_cycle_result`, `Will process states`, `Exclude states`) + snapshots.

## Relationships

```text
geo_counties → counties in national universe
census_tracts 1──0..1 fema_nri_tracts
hospitals 1──* hospital_timely_measures
acs_indicators (tract/state) → scoring safety rates + economy stats
neighborhood_scores.score_detail ← scoring after fema/timely/acs inputs
```

## Validation

- Applying `007_report_detail.sql` on populated DB must not drop rows.
- Empty `score_detail` remains valid API input (limited expand) until scoring gap closed.
- Re-score may change category numerics when hazard/timeliness enter the blend — accepted.
