# Quickstart: National ingest (ops)

## Prerequisites

- Worker image with this feature; SQL `006_geo_counties.sql` applied
- Keys as for metro ingest (EPA, FBI, Census, etc.)

## 1. Bootstrap county registry (denominator)

```powershell
# One-time / occasional: all 50+DC counties into geo_counties
# Set on niq-worker-geo (or local): INGEST_SCOPE=national INGEST_GEO_LOAD_ALL=1
az containerapp job start --name niq-worker-geo --resource-group neighborhoodiq-rg
```

Or loop states if preferred over load-all.

## 2. Run one state batch

Example Rhode Island (`44`):

```powershell
# On each job: INGEST_SCOPE=national INGEST_STATE_BATCH=44
# Order:
# geo (if not load-all) → census → epa → cms → fbi → nces → urban → acs → bls → scoring → status
az containerapp job start --name niq-worker-census --resource-group neighborhoodiq-rg
# … then remaining workers …
az containerapp job start --name niq-worker-status --resource-group neighborhoodiq-rg
# Status job: INGEST_SCOPE=national (no batch required for status)
```

## 3. Restart safety

Re-start the same worker with the same `INGEST_STATE_BATCH`. Logs should show `skip_checkpoint` for finished counties.

## 4. Local / metro regression

Unset national batch; use `INGEST_SCOPE=metro_10` or empty (fixture defaults) as today.
