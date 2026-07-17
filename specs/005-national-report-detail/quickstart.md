# Quickstart: National Report Detail (Azure smoke → national)

**Feature**: `005-national-report-detail` | **Date**: 2026-07-16

Validates production path for report expand data. **Not** satisfied by local Compose alone. Full narrative: [`docs/azure-setup-and-cicd.md`](../../docs/azure-setup-and-cicd.md) §16.

## Prerequisites

- [ ] Feature merged: `005` → `dev` → `master`; Deploy finished (API/web).
- [ ] Worker image rebuilt/pushed; ACA jobs on new image.
- [ ] `infra/sql/007_report_detail.sql` applied on Azure Postgres.
- [ ] Jobs `niq-worker-fema` and `niq-worker-cms-timely` exist.

## V1 — Schema check

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'neighborhood_scores' AND column_name = 'score_detail';
SELECT to_regclass('public.fema_nri_tracts'), to_regclass('public.hospital_timely_measures');
SELECT column_name FROM information_schema.columns
WHERE table_name = 'acs_indicators' AND column_name = 'total_population';
```

**Expect**: All present.

## V2 — Azure smoke fill

Set `INGEST_SCOPE=smoke` on relevant jobs, then:

```powershell
az containerapp job start --name niq-worker-acs --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-fema --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-cms-timely --resource-group neighborhoodiq-rg
az containerapp job start --name niq-worker-scoring --resource-group neighborhoodiq-rg
```

**Expect**: Benton County tracts have non-empty `score_detail`; FEMA/timely rows where sources provide data.

## V3 — Smoke UI gate

1. Open production web → search `609 SE Jamaica Dr, Bentonville, AR`.
2. Confirm category boxes, sub-scores, expand stats match known-good local/dev expand report (004).
3. Environment/Healthcare show hazard / ER wait when smoke jobs populated them.

**Fail → do not run National Ingest.**

## V4 — National gap-fill (after smoke)

GitHub → Actions → **National ingest** → e.g. `max_states=3`, empty `force_states` / `state_filter`.

**Expect** (if AR/MA/MS/TX/NY are base-complete but detail-gapped): orchestrator prefers those states; logs show fema/cms_timely/acs/scoring only — not full base redo.

## V5 — Automated checks (dev machine)

```bash
cd workers
$env:PYTHONPATH="."
python -m pytest tests/test_acs_population_checkpoint.py tests/test_inventory_report_detail.py tests/test_report_detail_checkpoints.py tests/test_scope_national_fema_timely.py tests/test_inventory.py -q
```

## Contracts

- [national-orchestrator.md](./contracts/national-orchestrator.md)
- [azure-ops.md](./contracts/azure-ops.md)
- Data: [data-model.md](./data-model.md)

## Failure signals

| Symptom | Likely cause |
|---------|--------------|
| Orchestrator never picks AR/… | Inventory missing fema/timely/score_detail gaps |
| ACS skipped but pop null | Checkpoint not requiring `total_population` |
| `INGEST_SCOPE=national` refuse on fema/timely | Old worker image still calling `assert_dev_scope` |
| Smoke UI stale | master Deploy / web image not updated |
| Must use force_states for detail | Bug — force must not be required |
