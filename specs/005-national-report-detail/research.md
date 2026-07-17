# Research: National Report Detail Ingest

**Feature**: `005-national-report-detail` | **Date**: 2026-07-16

Resolves design decisions for production schema ops and national gap-fill of 004 report-detail inputs.

---

## 1. Schema on Azure

**Decision**: Operators apply existing additive `infra/sql/007_report_detail.sql` on Azure Postgres (idempotent `ADD COLUMN` / `CREATE TABLE IF NOT EXISTS`). Also confirm `acs_indicators.total_population` (from `004_safety_education_economic.sql` / `init.sql` ALTER). Document in `docs/azure-setup-and-cicd.md` schema list after `006`.

**Rationale**: Spec FR-001/002; 007 already ships in repo from 004; prod docs currently stop at 006.

**Alternatives considered**: New `008_*.sql` wrapper (rejected — duplicate); recreate DB (rejected — destroys national progress).

---

## 2. Lift national refuse on FEMA / CMS Timely

**Decision**: Replace `assert_dev_scope()` in `ingest.fema` and `ingest.cms_timely` with normal scope resolution: allow `smoke` | `metro_10` | `national`. Under `national`, require `INGEST_STATE_BATCH` via existing `require_national_state_batch()` / `active_county_fips()` patterns used by other workers.

**Rationale**: Spec edge case and FR-003/004; 004 intentionally refused national locally.

**Alternatives considered**: Separate `ingest.fema_national` module (rejected — duplicate); keep refuse and only manual force (rejected — contradicts clarify).

---

## 3. Inventory pipeline membership

**Decision**: Extend `PIPELINE_WORKERS` and `WORKER_ACA_JOB` to:

```text
census → epa → cms → fbi → nces → urban → acs → bls → fema → cms_timely → scoring
```

- **fema**: county grain — counties where scoped tracts lack `fema_nri_tracts` rows (reuse/extend `geoids_with_fema_nri` → county-level done set).
- **cms_timely**: state grain (like cms) — states where in-scope hospitals lack timely measures for active vintage (or zero timely rows for providers in that state).
- **acs**: tighten done-check (see §4).
- **scoring**: done only when county has fbi_cde safety **and** non-empty `score_detail` for active vintage (align inventory with `compute.py` re-score-empty-detail behavior).

**Rationale**: FR-005/006/006a; orchestrator only starts jobs for inventory gaps.

**Alternatives considered**: Fold FEMA into scoring (rejected — network + long runtime); CMS Timely as county grain (rejected — hospital/state source).

---

## 4. ACS population without force

**Decision**: Change `counties_with_acs` so a county is “done” only if it has tract `acs_indicators` rows **and** those tracts have non-null `total_population` (and preferably state-level pop rows exist for the state’s FIPS). Counties with ACS income/labor but null population remain gaps → normal ACS re-run upserts B01003 without `INGEST_FORCE` and without touching other workers.

**Rationale**: FR-007; clarify “no force”; current checkpoint only checks row existence.

**Alternatives considered**: Always `INGEST_FORCE=1` on ACS (rejected); one-off SQL backfill script (rejected — bypasses worker contract).

---

## 5. State selection priority (max_states)

**Decision**: In `states_needing_work` (when not force / not exclusive filter-only):

1. Build set **A** = states with **no** gaps in base workers (`census`…`bls` + prior scoring completeness for base) but **any** gap in `fema` | `cms_timely` | `acs` (pop) | `scoring` (empty detail).
2. Build set **B** = all other states that still need any pipeline work (virgin / partial base).
3. Order = `sorted(A) + sorted(B - A)`, then apply `max_states` cap.

When `force_states` or exclusive `state_filter` is set, keep today’s exclusive semantics (no padding; no special priority required beyond operator list).

**Rationale**: Clarify option B / FR-006b / SC-003b.

**Alternatives considered**: Sorted FIPS only (rejected — virgin states could starve report-detail backfill); always prefer virgin (rejected by user).

**Definition note**: “Base-complete” for set A = no gaps in `census, epa, cms, fbi, nces, urban, bls` and no ACS gap **except** we treat ACS-pop-only as report-detail (ACS still in pipeline — a state with only ACS pop missing is in A via ACS gap). States missing census etc. are in B.

Simpler operational definition matching clarify example:

- **A**: every county in state is done for census…bls **and** scoring has fbi_cde rows (old scores OK), but fema and/or cms_timely and/or acs-pop and/or empty score_detail still gapped.
- If ACS-pop gap exists, ACS worker runs (not force).

---

## 6. Azure ACA jobs

**Decision**: Document and create (ops) `niq-worker-fema` (`python -m ingest.fema.run`) and `niq-worker-cms-timely` (`python -m ingest.cms_timely.run`) mirroring other jobs (Manual trigger, same image `neighborhoodiq-worker:dev` or current tag, `WORKER-DATABASE-URL`, national env when orchestrated). Wire `WORKER_ACA_JOB` map so orchestrator can start them.

**Rationale**: FR-005/010; azure docs list lacks these jobs.

**Alternatives considered**: Run FEMA inside scoring container (rejected — timeout/complexity).

---

## 7. CMS Timely national fetch cost

**Decision**: Keep page-iterate + provider allowlist filter (existing). Optional follow-up (not required for v1): checkpoint providers already having measures to skip full catalog re-download — upsert remains idempotent. Document that re-runs may re-fetch CMS pages but will not corrupt keys.

**Rationale**: SC-004; pragmatic v1.

**Alternatives considered**: Provider-level skip-fetch (nice-to-have; defer if timeboxed).

---

## 8. Status / Workbook

**Decision**: Extend `JOB_NAMES` in `ingest.status` with `fema` and `cms_timely`; define % complete similarly (tracts with NRI / hospitals with timely vs scope). Scoring % should count tracts with non-empty `score_detail` (or document dual metric). Workbook JSON needs no structural change if it already expands `payload.jobs` dynamically — re-run status job after deploy. FR-012 satisfied by extending status (preferred over docs-only).

**Rationale**: Clarify deferred observability → choose extend status in-feature.

---

## 9. Operator sequence (smoke gate)

**Decision**: Document:

1. Merge PR `005` → `dev`; promote `dev` → `master`; wait for Deploy (API/web) + rebuild/push worker image used by ACA jobs.
2. Apply `007_report_detail.sql` on Azure Postgres.
3. Create ACA jobs if missing; point image to new worker build.
4. Smoke: set jobs to `INGEST_SCOPE=smoke` (or allowlist `05007`), run acs (if pop gap) → fema → cms_timely → scoring; open Bentonville on prod site; compare to local/dev expand.
5. Only then: Actions → National ingest (`max_states`, no force needed for AR/MA/… backfill).

**Rationale**: US2 clarifications.

---

## 10. Testing strategy

- Unit: `states_needing_work` priority (A before B); `counties_with_acs` requires population; fema/cms_timely accept `INGEST_SCOPE=national` with batch; refuse still when batch missing.
- Integration/docs: quickstart Azure smoke checklist (manual SC-002).
- No change to web Vitest (004 owns UI).

---

## 11. Out of scope

- Re-implementing score formulas / expand UI (004).
- Auto-start national on Deploy.
- Territories.
- Provider-level CMS Timely download skip (optional later).
