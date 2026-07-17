# Contract: National Orchestrator (report-detail gaps)

**Feature**: `005-national-report-detail` | **Date**: 2026-07-16

Extends national inventory + orchestrator behavior. GitHub workflow inputs unchanged (`max_states`, `state_filter`, `force_states`).

## Pipeline order

```text
census → epa → cms → fbi → nces → urban → acs → bls → fema → cms_timely → scoring
```

| Logical worker | ACA job name | Module |
|----------------|--------------|--------|
| fema | `niq-worker-fema` | `python -m ingest.fema.run` |
| cms_timely | `niq-worker-cms-timely` | `python -m ingest.cms_timely.run` |
| (existing) | as today | … |

## Inventory gaps

- Include `fema`, `cms_timely` in `gaps` / `by_state` / `summary`.
- `acs` done-check requires non-null `total_population` (see data-model).
- `scoring` done-check requires non-empty `score_detail` for active vintage (in addition to fbi_cde safety).

## `states_needing_work`

When `force_states` empty and not exclusive-only:

1. Prefer states in **class A** (base-complete, report-detail gaps only).
2. Then **class B** (any other gaps).
3. Apply `max_states` cap.

`force_states` / exclusive `state_filter`: unchanged exclusive lists (no padding).

## Per-state workers

`workers_needed_for_state` returns only gapped stages in pipeline order. Example: AR base-complete missing FEMA + empty `score_detail` → `["fema", "cms_timely?", "scoring"]` as applicable — **not** census…bls.

## Worker env (orchestrator-started)

| Variable | Notes |
|----------|--------|
| `INGEST_SCOPE=national` | Required for national path |
| `INGEST_STATE_BATCH` | State(s) for this unit (orchestrator sets) |
| `INGEST_FORCE` | Only when state in `force_states` |
| `DATABASE_URL` | Worker Key Vault URL |

FEMA / CMS Timely MUST accept national scope (no `assert_dev_scope` refuse).

## Exit / idempotency

- Skip-done checkpoints; upserts on natural keys.
- Empty national batch → refuse with clear error (existing pattern).
