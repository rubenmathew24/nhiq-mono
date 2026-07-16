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
| `INGEST_FORCE` | `1` / `true` / `yes` — skip-done checkpoints disabled; re-upsert full batch. Orchestrator always sets `1` or `0` when patching jobs so force cannot stick. |
| `INGEST_STATUS_EVERY_N` | Emit mid-job `INGEST_STATUS_SNAPSHOT` every N units (default `15`). Used by FBI/ACS/BLS/Urban loops. |

## Orchestrator (`niq-worker-orchestrate`)

| Variable | Purpose |
|----------|---------|
| `ORCH_MAX_STATE_UNITS` | Max states to process this run (default `5`) |
| `ORCH_STATE_FILTER` | Optional comma state FIPS — **exclusive** list when set (only gaps within filter; no padding outside). Empty = unscoped national gap-fill. |
| `ORCH_FORCE_STATES` | Optional comma state FIPS to force full pipeline re-run. **Exclusive** when set (only these FIPS, capped by max; no gap padding). |

## Status snapshot log contract (`INGEST_STATUS_SNAPSHOT`)

Console line (Log Analytics / Workbook): metrics-only JSON — `scope`, `county_count`, `captured_at`, `jobs[]` with `job_name` / `pct_complete` / `done_count` / `total_count`. Optional empty `counties: []`. **No** full FIPS lists or large `detail.missing` in the log line.

Postgres `ingest_status_snapshot` retains full `detail` JSON for ops SQL.
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
| `python -m ingest.orchestrate.run` | Inventory → start gap (or forced) ACA jobs; status after each worker |
| Existing `ingest.*.run` / `scoring.compute` | Honor scope + checkpoints + force + status pulse |
| `python -m ingest.status` | Real national % (also called in-process for mid-run pulses) |

## GitHub Actions

Workflow `.github/workflows/national-ingest.yml`: `workflow_dispatch` only (inputs `max_states`, `state_filter`, `force_states`). Does not run on push to `master`.
