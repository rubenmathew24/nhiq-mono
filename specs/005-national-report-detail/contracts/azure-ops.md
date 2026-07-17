# Contract: Azure Ops (schema, jobs, smoke gate)

**Feature**: `005-national-report-detail` | **Date**: 2026-07-16

Operator-facing contract for production. Authoritative narrative also lands in `docs/azure-setup-and-cicd.md`.

## 1. Promote before smoke

```text
005 PR → merge to dev → promote dev → master
→ GitHub Deploy updates niq-api / niq-web
→ Rebuild/push worker image; ACA jobs use new image
```

Local Compose success does **not** clear the national gate.

## 2. Schema (Azure Postgres)

Apply in order if missing:

```text
… existing through 006 …
infra/sql/007_report_detail.sql
```

Confirm `acs_indicators.total_population` exists. Use Docker `psql` + `sslmode=require` pattern from azure-setup §7.

Expect: `neighborhood_scores.score_detail`, `fema_nri_tracts`, `hospital_timely_measures`.

## 3. New ACA Jobs

| Job | Command | Notes |
|-----|---------|--------|
| `niq-worker-fema` | `python -m ingest.fema.run` | Same secrets/image as other ingest jobs |
| `niq-worker-cms-timely` | `python -m ingest.cms_timely.run` | No new API keys |

Add to orchestrator job map. Document in azure-setup §16 job list.

## 4. Azure smoke gate (required before National Ingest)

1. Schema applied; worker image current.
2. Configure smoke: `INGEST_SCOPE=smoke` (and/or allowlist `05007`) on fema, cms_timely, acs, scoring as needed.
3. Run: `acs` (if pop gap) → `fema` → `cms_timely` → `scoring` (base data for Benton assumed present from prior metro/national).
4. Open production site → Bentonville fixture address → expand report matches local/dev 004 experience.
5. **Stop** if gate fails; do not start National Ingest.

## 5. National Ingest after smoke

GitHub → Actions → **National ingest** → `max_states` (e.g. 3), leave `force_states` empty.

Expect: previously gathered states with only report-detail gaps are preferred; only fema / cms_timely / acs-pop / scoring-detail jobs run for them.

## 6. Status

`niq-worker-status` includes `fema` and `cms_timely` in snapshot jobs after this feature. Re-run status; Workbook table expands dynamically.
