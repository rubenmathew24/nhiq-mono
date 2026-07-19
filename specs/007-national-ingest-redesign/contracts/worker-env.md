# Contract: Worker / orchestrator environment (007 additions)

Extends `specs/003-national-ingest/contracts/worker-env.md`.

## Orchestrator

| Variable | Purpose |
|----------|---------|
| `ORCH_CONTINUOUS` | `1`/`true` = continuous nationwide loop |
| `ORCH_BATCH_STATES` | Max gap states per worker execution (default `10`) |
| `ORCH_TIME_BUDGET_SECONDS` | Soft stop before ACA kill (default `20700`) |
| `ORCH_MAX_STATE_UNITS` | Bounded mode only (unchanged) |
| `ORCH_STATE_FILTER` / `ORCH_FORCE_STATES` / `ORCH_STATE_EXCLUDE` | Unchanged semantics |

## Workers (optional concurrency / bulk flags)

| Variable | Purpose |
|----------|---------|
| `FBI_MAX_CONCURRENCY` | County thread pool size (default `4`) |
| `ACS_MAX_CONCURRENCY` | Unused if per-state fetch; keep only if retained |
| `URBAN_MAX_CONCURRENCY` | Unused if per-state fetch; keep only if retained |
| `EPA_USE_BULK_FILES` | Default `1` — AirData zips vs AQS API |
| `BLS_USE_BULK_FILES` | Default `1` — LAUS flat files vs series API |
| `FEMA_NRI_BULK_URL` | Override national tracts CSV zip URL (default: OpenFEMA v1.20). If bulk returns non-zip / 403, national FEMA falls back to ArcGIS per-county queries. |

## ACA timeouts (ops)

| Job | `--replica-timeout` |
|-----|---------------------|
| `niq-worker-orchestrate` | `21600` |
| Per-source ingest / scoring | `10800` |
