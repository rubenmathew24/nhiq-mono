# Quickstart: National ingest (ops)

## Prerequisites

- Worker image with this feature; SQL `006_geo_counties.sql` applied
- Keys as for metro ingest (EPA, FBI, Census, etc.)
- County registry bootstrapped (`niq-worker-geo` with `INGEST_GEO_LOAD_ALL=1`)

## Preferred: GitHub Actions orchestrator

1. GitHub → Actions → **National ingest** → **Run workflow**
2. Inputs: `max_states` (default 5), optional `state_filter` (e.g. `44` for Rhode Island)
3. Watch the Actions log; refresh the Workbook (`INGEST_SCOPE=national`)
4. Re-run the workflow to continue — inventory skips workers/states that are already complete

## Manual one state batch (fallback)

Example Rhode Island (`44`):

```powershell
# On each job: INGEST_SCOPE=national INGEST_STATE_BATCH=44
# Order: census → epa → cms → fbi → nces → urban → acs → bls → scoring → status
az containerapp job start --name niq-worker-census --resource-group neighborhoodiq-rg
```

## Restart safety

Re-start the same worker with the same `INGEST_STATE_BATCH`. Logs should show `skip_checkpoint` for finished counties. Orchestrator re-runs use the same DB inventory.

## Local / metro regression

Unset national batch; use `INGEST_SCOPE=metro_10` or empty (fixture defaults) as today.
