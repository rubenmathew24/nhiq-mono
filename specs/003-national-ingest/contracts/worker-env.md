# Contract: Worker environment (national ingest)

## Required env (all workers)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres (`sslmode=require` on Azure workers) |
| `INGEST_SCOPE` | `smoke` \| `metro_10` \| `national` (default `metro_10` for status; workers may default metro behavior when unset) |

## National batch

| Variable | Purpose |
|----------|---------|
| `INGEST_STATE_BATCH` | Comma-separated 2-digit state FIPS. **Required** when `INGEST_SCOPE=national` for ingest/scoring workers. |
| `INGEST_COUNTY_ALLOWLIST` | Optional SSCCC narrow within active county set |
| `INGEST_GEO_LOAD_ALL` | `1` only on `ingest.geo` — load county registry for all included 50+DC states (bootstrap denominator) |

## Orchestrator (`niq-worker-orchestrate`)

| Variable | Purpose |
|----------|---------|
| `ORCH_MAX_STATE_UNITS` | Max states to process this run (default `5`) |
| `ORCH_STATE_FILTER` | Optional comma state FIPS to limit inventory |
| `AZURE_RESOURCE_GROUP` | e.g. `neighborhoodiq-rg` |
| `AZURE_SUBSCRIPTION_ID` | Subscription for ARM calls |
| `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` | SP that can start/update ACA jobs |

## Fail-closed messages

- National + missing batch → exit 1: `INGEST_SCOPE=national requires INGEST_STATE_BATCH=SS,SS,...`
- Unknown state in batch → exit 1 listing invalid codes
- Territory FIPS in batch while not in included set → exit 1 (not silently ignored)

## Modules

| Command | Role |
|---------|------|
| `python -m ingest.geo.run` | Upsert `geo_counties` from TIGER for batch or load-all |
| `python -m ingest.inventory` | Print gap inventory JSON |
| `python -m ingest.orchestrate.run` | Inventory → start only gap ACA jobs |
| Existing `ingest.*.run` / `scoring.compute` | Honor scope + checkpoints |
| `python -m ingest.status` | Real national % |

## GitHub Actions

Workflow `.github/workflows/national-ingest.yml`: `workflow_dispatch` only (inputs `max_states`, `state_filter`). Does not run on push to `master`.
