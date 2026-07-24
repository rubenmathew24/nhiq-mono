# Contract: Worker / orchestrator environment (national ingest)

## Required env (all workers)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres (`sslmode=require` on Azure workers) |
| `INGEST_SCOPE` | `smoke` \| `metro_10` \| `national` (default `metro_10` for status; workers may default metro behavior when unset) |

## National batch

| Variable | Purpose |
|----------|---------|
| `INGEST_STATE_BATCH` | Comma-separated 2-digit state FIPS. **Required** when `INGEST_SCOPE=national` for ingest/scoring workers. Orchestrator may set multi-state lists. |
| `INGEST_COUNTY_ALLOWLIST` | Optional SSCCC narrow within active county set |
| `INGEST_GEO_LOAD_ALL` | `1` only on `ingest.geo` — load county registry for all included 50+DC states (bootstrap denominator) |
| `INGEST_FORCE` | `1` / `true` / `yes` — skip-done checkpoints disabled; re-upsert full batch. Orchestrator always sets `1` or `0` when patching jobs so force cannot stick. |
| `INGEST_STATUS_EVERY_N` | Emit mid-job `INGEST_STATUS_SNAPSHOT` every N units (default `15`). Used by FBI/ACS/BLS/Urban loops. |

## Orchestrator (`niq-worker-orchestrate`)

| Variable | Purpose |
|----------|---------|
| `ORCH_CONTINUOUS` | `1`/`true` = continuous nationwide loop |
| `ORCH_BATCH_STATES` | Max gap states per worker execution in continuous mode (default `10`) |
| `ORCH_TIME_BUDGET_SECONDS` | Soft stop before ACA kill (default `20700`) |
| `ORCH_MAX_STATE_UNITS` | Max states to process in **bounded** mode (default `5`) |
| `ORCH_STATE_FILTER` | Optional comma state FIPS — **exclusive** list when set (only gaps within filter; no padding outside). Empty = unscoped national gap-fill. |
| `ORCH_FORCE_STATES` | Optional comma state FIPS to force full pipeline re-run. **Exclusive** when set (only these FIPS, capped by max; no gap padding). |
| `ORCH_STATE_EXCLUDE` | Optional comma state FIPS blacklist — skipped before selection so other gap states fill the quota. `ORCH_FORCE_STATES` overrides exclude for overlapping FIPS. |
| `AZURE_RESOURCE_GROUP` | e.g. `neighborhoodiq-rg` |
| `AZURE_SUBSCRIPTION_ID` | Subscription for ARM calls |
| `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` | SP that can start/update ACA jobs |

## Workers (concurrency / bulk flags)

| Variable | Purpose |
|----------|---------|
| `FBI_MAX_CONCURRENCY` | County thread pool size (default `4`) |
| `EPA_USE_BULK_FILES` | Default `1` — AirData zips vs AQS API |
| `BLS_USE_BULK_FILES` | Default `1` — LAUS flat files vs series API |
| `FEMA_NRI_BULK_URL` | Override national tracts CSV zip URL. If bulk returns non-zip / 403, national FEMA falls back to ArcGIS per-county queries. |

## ACA timeouts (ops)

| Job | `--replica-timeout` |
|-----|---------------------|
| `niq-worker-orchestrate` | `21600` |
| Per-source ingest / scoring | `10800` |

## Status snapshot log contract (`INGEST_STATUS_SNAPSHOT`)

Console line (Log Analytics / Workbook): metrics-only JSON — `scope`, `county_count`, `captured_at`, `jobs[]` with `job_name` / `pct_complete` / `done_count` / `total_count`. Optional empty `counties: []`. **No** full FIPS lists or large `detail.missing` in the log line.

Postgres `ingest_status_snapshot` retains full `detail` JSON for ops SQL.

## Fail-closed messages

- National + missing batch → exit 1: `INGEST_SCOPE=national requires INGEST_STATE_BATCH=SS,SS,...`
- Unknown state in batch → exit 1 listing invalid codes
- Territory FIPS in batch while not in included set → exit 1 (not silently ignored)
- Empty or incomplete `geo_counties` for 50+DC → exit 1; never `orch_cycle_result=complete`

## Modules

| Command | Role |
|---------|------|
| `python -m ingest.geo.run` | Upsert `geo_counties` from TIGER for batch or load-all |
| `python -m ingest.inventory` | Print gap inventory JSON |
| `python -m ingest.orchestrate.run` | Inventory → start gap (or forced) ACA jobs; continuous or bounded; status after each worker |
| Existing `ingest.*.run` / `scoring.compute` | Honor scope + checkpoints + force + status pulse + bulk/wide where applicable |
| `python -m ingest.status` | Real national % (also called in-process for mid-run pulses) |

## GitHub Actions

Workflow `.github/workflows/national-ingest.yml`: `workflow_dispatch` only (inputs `continuous`, `max_states`, `batch_states`, `state_filter`, `force_states`, `state_exclude`, `chain_depth`, `force_worker_rebuild`). Does not run on push to `master`. Before orchestrate: **detect-worker** compares `workers/` + `docker/worker.Dockerfile` to the `org.opencontainers.image.revision` on `neighborhoodiq-worker:dev` and **build-worker** pushes `:dev` + `sha-<gitsha>` only when needed (skipped when `chain_depth≠0`). Continuous mode may self-redispatch (`actions: write`; redispatches set `force_worker_rebuild=false`).
