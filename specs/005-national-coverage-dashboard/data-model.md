# Data Model: National Coverage Dashboard

No new tables. Read model only.

## Inputs (existing)

| Table | Role |
|-------|------|
| `geo_counties` | National / per-state denominators for ordinary county-grain jobs |
| `epa_aqs_monitor_counties` | EPA exceptional denominator (AQS monitor counties only) |
| `census_tracts`, `epa_aqi_readings`, `hospitals`, `crime_agency_selection`, `schools_nces`, `schools_urban`, `acs_indicators`, `bls_laus_county`, `fema_nri_tracts`, `hospital_timely_measures`, `neighborhood_scores` | Done-ness per source (same rules as coverage/status display) |

## Coverage API entities (response)

- **CoverageResponse**: `captured_at`, `overall_pct`, `county_universe_count`, `state_universe_count`, `sources[]`, `states[]`
- **SourceCoverage**: `job_name`, `grain` (`county`|`state`|`hospital`), `done_count`, `total_count`, `pct_complete`
- **StateCoverage**: `state_fips`, `state_abbr`, `county_total`, `sources[]` (same shape; totals scoped with the **same grain rules** as national)

### Grain rules (national and by-state)

| Job | Grain | Denominator |
|-----|-------|-------------|
| Most ingest + scoring | `county` | Counties in registry (scoring: fully scored counties) |
| epa | `county` | AQS monitor counties only (`0/0` per state if none) |
| urban | `county` | NCES-complete counties |
| cms | `state` | 0/1 per included state |
| cms_timely | `hospital` | Hospitals with ≥1 timely measure ÷ hospitals |

By-state done/total MUST sum to national done/total for every job.

## UI presentation (display only)

- **Overall tab**: national `sources[]` table (+ headline `overall_pct`).
- **By state tab**: filter = Overall | each `job_name`; rows from `states[]`. Overall filter shows mean of that state’s `sources[].pct_complete` **where `total_count > 0`** (client display formatting).
