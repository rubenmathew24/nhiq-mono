# Contract: Azure Ops (schema, jobs, smoke gate)

**Feature**: `003-national-ingest`

Operator-facing contract. Narrative source of truth: [`docs/azure-setup-and-cicd.md`](../../../docs/azure-setup-and-cicd.md) §16.

## 1. Promote before smoke

```text
feature PR → merge to dev → promote dev → master
→ GitHub Deploy updates niq-api / niq-web
→ Rebuild/push worker image; ACA jobs use new image
```

Local Compose success does **not** clear the national gate.

## 2. Schema (Azure Postgres)

Apply in order if missing (see azure-setup §16 Schema on Azure):

```text
… existing through 006 …
infra/sql/007_report_detail.sql
```

Confirm `acs_indicators.total_population` exists. Use Docker `psql` + `sslmode=require` pattern from azure-setup §7.

Expect: `neighborhood_scores.score_detail`, `fema_nri_tracts`, `hospital_timely_measures`.

## 3. ACA Jobs (report-detail + orchestrator)

| Job | Command | Notes |
|-----|---------|--------|
| `niq-worker-fema` | `python -m ingest.fema.run` | Same secrets/image as other ingest jobs |
| `niq-worker-cms-timely` | `python -m ingest.cms_timely.run` | No new API keys |
| `niq-worker-orchestrate` | `python -m ingest.orchestrate.run` | Inventory + continuous/bounded scheduling |

Wire into orchestrator via `WORKER_ACA_JOB` in `workers/ingest/inventory.py`.

## 4. Azure smoke gate (required before National Ingest)

1. Schema applied; worker image current.
2. Configure smoke: `INGEST_SCOPE=smoke` (and/or allowlist `05007`) on fema, cms_timely, acs, scoring as needed.
3. Run: `acs` (if pop gap) → `fema` → `cms_timely` → `scoring`.
4. Open production site → Bentonville fixture → expand report matches local/dev 004 experience.
5. **Stop** if gate fails; do not start National Ingest.

## 5. National Ingest after smoke

GitHub → Actions → **National ingest** → prefer `continuous=true`; or bounded `max_states` with empty `force_states` / `state_filter`.

Expect: previously gathered states with only report-detail gaps are preferred; only fema / cms_timely / acs-pop / scoring-detail jobs run for them when that is all that remains. **Force is not required.**

## 6. Status

`niq-worker-status` includes `fema` and `cms_timely`. Scoring % requires non-empty `score_detail` at county grain vs full `geo_counties`. Re-run status; Workbook table expands dynamically from snapshot jobs.
