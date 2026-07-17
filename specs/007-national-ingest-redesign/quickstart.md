# Quickstart: National Ingest Redesign

## Prerequisites

1. `geo_counties` bootstrapped (`INGEST_GEO_LOAD_ALL=1` on geo worker).
2. Worker image rebuilt/pushed after this feature merges (`neighborhoodiq-worker:dev`).
3. ACA replica timeouts updated (orchestrator 21600s; workers 10800s).
4. Azure SP can start/update jobs; GHA has `AZURE_CREDENTIALS` + `actions: write` for chaining.

## A. Continuous via GitHub Actions

1. Actions → **National ingest** → Run workflow.
2. Inputs: `continuous=true` (default), leave `state_filter` empty; set `state_exclude` only if needed.
3. Watch **Poll until complete** for `Will process states`, `orch_start`, `orch_cycle_result=...`, `last_activity=...`.
4. Expect auto re-start / self-redispatch until `orch_cycle_result=complete`.

## B. Continuous via PowerShell

```powershell
.\scripts\national-ingest.ps1 -AllowMyIp   # optional firewall for inventory DB
.\scripts\national-ingest.ps1              # loops until exit 0 / hard fail
```

Requires `.env` with `DATABASE_URL` (Azure) and `AZURE_*` for job control.

## C. Verify accurate progress

```sql
SELECT job_name, pct_complete, done_count, total_count, captured_at
FROM ingest_status_snapshot
WHERE scope = 'national'
ORDER BY job_name;
```

After a status emit: `scoring.total_count` should equal national county count (~3143), not “tracts loaded so far”.

## D. Bounded diagnostic run

GHA: `continuous=false`, `max_states=2`, optional `state_filter=44`.

## E. Smoke still works

`INGEST_SCOPE=smoke` on workers — metro/smoke paths unchanged; continuous nationwide not required.
