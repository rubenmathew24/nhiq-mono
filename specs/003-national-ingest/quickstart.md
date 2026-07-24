# Quickstart: National ingest (ops)

**Feature**: `003-national-ingest`

Full narrative: [`docs/azure-setup-and-cicd.md`](../../docs/azure-setup-and-cicd.md) §16.

## Prerequisites

- [ ] SQL `006_geo_counties.sql` applied; county registry bootstrapped (`niq-worker-geo` with `INGEST_GEO_LOAD_ALL=1`)
- [ ] `infra/sql/007_report_detail.sql` applied when expand/report-detail is needed; confirm `acs_indicators.total_population`
- [ ] `infra/sql/010_census_tract_land_water.sql` applied when Discover water-only filtering / honest census coverage is needed; confirm `census_tracts.aland` / `awater`. **Deploy on `master` applies numbered SQL automatically** when `infra/sql/` changes (007). After apply, `/coverage` census % drops until counties have non-NULL `aland` (national continuous census gap-fill — no force).
- [ ] Worker image: National ingest GHA updates `neighborhoodiq-worker:dev` when `workers/` / `docker/worker.Dockerfile` changed since the labeled image SHA (or on `force_worker_rebuild`); ACA jobs include `niq-worker-fema`, `niq-worker-cms-timely`, `niq-worker-orchestrate`
- [ ] ACA timeouts: orchestrator `21600`s; workers `10800`s
- [ ] Keys as for metro ingest; Azure SP / `AZURE_CREDENTIALS`; GHA `actions: write` for continuous chaining

---

## 1. Azure smoke gate (required before trusting national expand)

Local Compose alone does **not** clear this gate.

1. Merge/promote path: feature work → `dev` → `master`; wait for Deploy (API/web) + rebuild/push worker image.
2. Schema check:

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'neighborhood_scores' AND column_name = 'score_detail';
SELECT to_regclass('public.fema_nri_tracts'), to_regclass('public.hospital_timely_measures');
SELECT column_name FROM information_schema.columns
WHERE table_name = 'acs_indicators' AND column_name = 'total_population';
```

3. Set `INGEST_SCOPE=smoke` (and/or allowlist `05007`) on relevant jobs; run:

```powershell
az containerapp job start --name niq-worker-acs --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-fema --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-cms-timely --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-scoring --resource-group neighborhoodiq-rg
```

4. Open production web → `609 SE Jamaica Dr, Bentonville, AR` → expand report matches known-good local/dev (004).

**Fail → do not start National Ingest.**

---

## 2. Continuous national (preferred)

### A. GitHub Actions

1. Actions → **National ingest** → Run workflow.
2. Inputs: `continuous=true` (default); leave `state_filter` / `force_states` empty for unscoped gap-fill; set `state_exclude` only if needed.
3. Watch for `Will process states`, `orch_start`, `orch_cycle_result=...`, `national_progress`.
4. Expect auto re-start / self-redispatch until `orch_cycle_result=complete`.

### B. PowerShell

```powershell
.\scripts\national-ingest.ps1 -AllowMyIp   # optional firewall for inventory DB
.\scripts\national-ingest.ps1              # loops until exit 0 / hard fail
```

Requires `.env` with `DATABASE_URL` (Azure) and `AZURE_*` for job control.

### Expectation (report-detail)

States that finished base ingest but lack FEMA / CMS Timely / ACS population / `score_detail` remain inventory gaps — **do not** use `force_states` only to unlock report-detail. Orchestrator prefers those (class A) over virgin states.

---

## 3. Bounded diagnostic run

GHA: `continuous=false`, `max_states=2` (or similar), optional `state_filter=44`.

**Force re-ingest**: `force_states` (exclusive — no gap padding). Workers get `INGEST_FORCE=1` for that run only.

---

## 4. Manual one state batch (fallback)

Example Rhode Island (`44`):

```powershell
# On each job: INGEST_SCOPE=national INGEST_STATE_BATCH=44
# Order: census → epa → cms → fbi → nces → urban → acs → bls → fema → cms_timely → scoring → status
az containerapp job start --name niq-worker-census --resource-group neighborhoodiq-rg
```

---

## 5. Verify accurate progress

```sql
SELECT job_name, pct_complete, done_count, total_count, captured_at
FROM ingest_status_snapshot
WHERE scope = 'national'
ORDER BY job_name;
```

`scoring.total_count` should equal national county count (~3143), not “tracts loaded so far”. Workbook refreshes after each worker and every ~15 counties mid-job. Re-import [`infra/workbook-ingest-status.json`](../../infra/workbook-ingest-status.json) if the gallery is stale.

---

## 6. Restart safety / metro regression

Re-start the same worker with the same `INGEST_STATE_BATCH`. Logs should show `skip_checkpoint` for finished counties.

Unset national batch; use `INGEST_SCOPE=metro_10` or `smoke` for fast regression — continuous nationwide not required.

---

## 7. Automated checks (dev machine)

```bash
cd workers
$env:PYTHONPATH="."
python -m pytest tests/test_acs_population_checkpoint.py tests/test_inventory_report_detail.py tests/test_report_detail_checkpoints.py tests/test_scope_national_fema_timely.py tests/test_inventory.py tests/test_status_scoring_denominator.py tests/test_orchestrate_continuous.py -q
```

---

## Contracts

- [worker-env.md](./contracts/worker-env.md)
- [continuous-orchestrator.md](./contracts/continuous-orchestrator.md)
- [azure-ops.md](./contracts/azure-ops.md)
- [national-orchestrator.md](./contracts/national-orchestrator.md)
- Data: [data-model.md](./data-model.md)

## Failure signals

| Symptom | Likely cause |
|---------|--------------|
| Orchestrator never picks report-detail-only states | Inventory missing fema/timely/score_detail/acs-pop gaps |
| ACS skipped but pop null | Checkpoint not requiring `total_population` |
| `INGEST_SCOPE=national` refuse on fema/timely | Old worker image still calling `assert_dev_scope` |
| Scoring % inflated | Loaded-tract denominator (should be geo_counties county grain) |
| Empty registry treated as complete | Fail-closed bug |
| Must use force_states for detail | Bug — force must not be required |
| Smoke UI stale | master Deploy / web image not updated |
