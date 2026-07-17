# Contract: Continuous orchestrator

## Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| Continuous | `ORCH_CONTINUOUS=1` (GHA `continuous=true` default, or PowerShell) | Ignore `ORCH_MAX_STATE_UNITS` as a hard nation cap; loop until inventory clear or time budget |
| Bounded | `ORCH_CONTINUOUS=0` / false | Existing max_states / filter / force / exclude semantics |

## Batching

For each pipeline worker in order, select up to `ORCH_BATCH_STATES` (default `10`) gap states and start **one** ACA execution with `INGEST_STATE_BATCH=SS,SS,...`.

## Exit codes

| Code | Meaning | Caller action |
|------|---------|---------------|
| `0` | Full inventory pass with zero required gaps | Stop; nation complete |
| `2` | Time budget hit; gaps remain | Start another orchestrator execution / redispatch workflow / PowerShell loop |
| `1` | Hard failure | Fail the Action / stop PowerShell |

## Log markers (must appear for GHA progress)

- `Exclude states=...` (when set)
- `Will process states=...` / batch lines per worker
- `orch_start worker=... state=...` (or multi-state batch equivalent)
- `orch_cycle_result=complete` | `orch_cycle_result=more_work`
- Optional: `national_progress` summary after status emit

## Time budget

`ORCH_TIME_BUDGET_SECONDS` default `20700`. Stop starting new work when elapsed ≥ budget; emit `orch_cycle_result=more_work` and exit `2`.

## GHA chaining

1. Poll orchestrator execution; tail interesting logs.
2. On terminal status: if `complete` → success; if `more_work` and time remains → start new execution; if workflow near timeout → `workflow_dispatch` self with `chain_depth+1` (max 50) then exit 0 (handed off).
3. `permissions: actions: write` required for self-dispatch.
