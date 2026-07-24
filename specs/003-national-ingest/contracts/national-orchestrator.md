# Contract: National Orchestrator (inventory + report-detail + continuous)

**Feature**: `003-national-ingest`

Extends inventory + orchestrator behavior. GitHub workflow inputs: `continuous`, `max_states`, `state_filter`, `force_states`, `state_exclude`, `chain_depth`.

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
3. Apply continuous `ORCH_BATCH_STATES` or bounded `max_states` cap.

`force_states` / exclusive `state_filter`: unchanged exclusive lists (no padding).

## Per-state workers

`workers_needed_for_state` returns only gapped stages in pipeline order. Example: AR base-complete missing FEMA + empty `score_detail` → `["fema", …, "scoring"]` as applicable — **not** census…bls.

## Worker env (orchestrator-started)

| Variable | Notes |
|----------|--------|
| `INGEST_SCOPE=national` | Required for national path |
| `INGEST_STATE_BATCH` | State(s) for this unit (orchestrator sets; may be multi-state) |
| `INGEST_FORCE` | Only when state in `force_states` |
| `DATABASE_URL` | Worker Key Vault URL |

FEMA / CMS Timely MUST accept national scope (no `assert_dev_scope` refuse).

## Continuous

See [continuous-orchestrator.md](./continuous-orchestrator.md) for exit codes, chaining, and fail-closed registry rules.

## Exit / idempotency

- Skip-done checkpoints; upserts on natural keys.
- Empty national batch → refuse with clear error.
- Empty/incomplete `geo_counties` → fail closed (never complete).
