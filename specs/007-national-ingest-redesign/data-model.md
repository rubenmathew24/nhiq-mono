# Data Model: National Ingest Redesign

No new tables required. Behavior changes only.

## Existing entities (unchanged schemas)

| Entity | Table | Notes |
|--------|-------|-------|
| National county universe | `geo_counties` | Denominator for national status |
| Tracts | `census_tracts` | ACS/FEMA/scoring join key |
| Hazard tracts | `fema_nri_tracts` | Loaded from bulk NRI CSV |
| ACS indicators | `acs_indicators` | State-wide fetch, county filter |
| Schools NCES / Urban | `schools_nces`, `schools_urban` | Urban skip-done on `(ncessch, year)` |
| Crime | `crime_agency_selection`, offense aggregates | FBI concurrency + agency cache |
| EPA / BLS | `epa_aqi_readings`, `bls_laus_county` | Optional bulk file loaders |
| Timely care | `hospital_timely_measures` | Skip-done by vintage |
| Scores | `neighborhood_scores` | Status done = county all tracts fbi_cde + non-empty `score_detail` |
| Status snapshot | `ingest_status_snapshot` | `scope=national` percentages |

## Status semantics (change)

| Job | Done | Total |
|-----|------|-------|
| Most county-grain jobs | Counties with required rows | `COUNT(*)` from `geo_counties` (50+DC) |
| **scoring** | Counties where every tract has fbi_cde + non-empty `score_detail` | Same national county count (was: tract count in `census_tracts`) |
| cms / cms_timely | State-grain as today | State abbr count in universe |

## Orchestrator run state (ephemeral)

Not persisted: continuous loop clock, current worker, `ORCH_BATCH_STATES` list, exit code. Progress observed via logs (`orch_cycle_result`, `Will process states`, `Exclude states`) + `ingest_status_snapshot`.
