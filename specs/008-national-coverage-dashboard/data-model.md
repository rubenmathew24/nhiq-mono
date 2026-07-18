# Data Model: National Coverage Dashboard

No new tables. Read model only.

## Inputs (existing)

| Table | Role |
|-------|------|
| `geo_counties` | National / per-state denominators |
| `census_tracts`, `epa_aqi_readings`, `hospitals`, `crime_agency_selection`, `schools_nces`, `schools_urban`, `acs_indicators`, `bls_laus_county`, `fema_nri_tracts`, `hospital_timely_measures`, `neighborhood_scores` | Done-ness per source (same rules as status) |

## Coverage API entities (response)

- **CoverageResponse**: `captured_at`, `overall_pct`, `county_universe_count`, `state_universe_count`, `sources[]`, `states[]`
- **SourceCoverage**: `job_name`, `grain` (`county`|`state`), `done_count`, `total_count`, `pct_complete`
- **StateCoverage**: `state_fips`, `state_abbr`, `county_total`, `sources[]` (same shape, totals scoped to that state)
