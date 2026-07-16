# Tasks: Report Sub-Scores & Category Detail

**Input**: Design documents from `/specs/004-report-subscores/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Scope lock**: Local Compose only; `INGEST_SCOPE` ∈ {`smoke`, `metro_10`} — not national.

**Status**: First implement (T001–T044) and UX polish round 1 (T045–T074) **complete**. Open work is **UX polish round 2** (T075+) per plan revision 2026-07-16 §11.

**Tests**: Constitution VI — pytest in `workers/tests/` and `apps/api/tests/`; Vitest in `apps/web/src/__tests__/`.

**Organization**: By user story. Round-2 order: ACS population foundation → Safety rate (US2/US1) → Healthcare `★-` + Schools 25 mi (US2) → full-box UI (US2) → operator re-score (US4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no incomplete blockers)
- **[Story]**: US1…US4 from spec.md
- Exact file paths in every task

## Path Conventions

- Workers: `workers/ingest/<source>/`, `workers/scoring/`
- API: `apps/api/app/`, tests `apps/api/tests/`
- Web: `apps/web/src/`
- SQL: `infra/sql/`

---

## Phase 1–13: Prior work (COMPLETE)

<details>
<summary>Completed task IDs (T001–T074)</summary>

- T001–T044 First implement (schema, FEMA/Timely, sub_scores, accordion)
- T045–T074 UX polish round 1 (tone_score, plain English, ordinals, boxes header-click, employment rate)

</details>

---

## Phase 14: Round 2 — Foundational (ACS population)

**Purpose**: Persist ACS B01003 total population so Safety can normalize county vs state **per resident** (research.md §11.1). Blocks honest Safety copy.

**⚠️ CRITICAL**: Do not ship absolute county÷state share as the violent-crime meaning after this phase lands

- [ ] T075 Add `total_population` to ACS ingest (B01003_001E) in `workers/ingest/acs/client.py`, `workers/ingest/acs/transform.py`, and upsert SQL in `workers/ingest/acs/run.py`
- [ ] T076 [P] Extend `acs_indicators` DDL with `total_population NUMERIC` (nullable) in `infra/sql/004_safety_education_economic.sql` and `infra/sql/init.sql` (additive `ALTER` note or one-shot if preferred)
- [ ] T077 Fetch/store **state-level** ACS population (`geo_level='state'`) for fixture states used by smoke/metro_10 in `workers/ingest/acs/` (same B01003)
- [ ] T078 [P] Add `SCHOOL_MAX_EXPAND_MILES = 25` to `workers/ingest/fixtures/constants.py`

**Checkpoint**: Population available after `worker-acs` for smoke; school cutoff constant defined

---

## Phase 15: User Story 1 — Safety sub-score uses per-resident intensity (Priority: P1)

**Goal**: Personal (and property when applicable) safety sub-scores use population-normalized intensity ratio, not absolute share

**Independent Test**: Unit tests: equal per-resident rates → score ~75; higher local rate → lower score; missing pop → limited/default without inventing absolute-share “wins”

### Tests for User Story 1

- [ ] T079 [P] [US1] Update/rewrite safety formula tests for per-resident ratio in `workers/tests/test_safety_formula.py` (pass county_pop/state_pop into `safety_from_cde` or new helper)

### Implementation for User Story 1

- [ ] T080 [US1] Change `safety_from_cde` / `_weighted_local_state` consumers in `workers/scoring/safety.py` to compute `intensity_ratio = (local/county_pop) / (state/state_pop)` (equiv. form OK); if either population missing → default/unavailable provenance (no absolute-share fallback)
- [ ] T081 [US1] Thread county + state population into safety scoring from ACS in `workers/scoring/compute.py`

**Checkpoint**: Safety category numbers reflect per-resident intensity

---

## Phase 16: User Story 2 — Expand polish round 2 (Priority: P1) 🎯 MVP

**Goal**: Per-resident violent-crime copy; ER `★-`; schools ≤25 mi; entire category box clickable with stronger hover

**Independent Test**: Bentonville — no `0.03×` absolute share; no 457 mi Pre-K; unrated ERs show `★-`; click sub-score area expands; hover clearly stronger

### Tests for User Story 2

- [ ] T082 [P] [US2] Unit tests: violent-crime expand copy percent lower/higher/same (per resident); ER `★-` when no stars; school beyond 25 mi → no-schools-found in `workers/tests/test_score_detail.py`
- [ ] T083 [P] [US2] Vitest: entire box toggles expand (click outside title); hover class stronger than pre-round-2 muted wash; no “View details” in `apps/web/src/__tests__/score-breakdown-expand.test.tsx`
- [ ] T084 [P] [US2] API assertions: Safety factor value contains “per resident” (or equivalent) and not tiny `0.0x` absolute-share pattern; ER values may include `★-` in `apps/api/tests/test_score_subscores.py`

### Implementation for User Story 2

- [ ] T085 [US2] Rewrite violent-crime expand stat in `workers/scoring/detail.py` to Fair Housing–neutral percent vs state average **per resident**; set `tone_score` from personal sub-score; never show absolute county÷state share
- [ ] T086 [US2] Always append `★{n}` or `★-` on Healthcare ER expand values in `workers/scoring/detail.py`
- [ ] T087 [US2] Apply `SCHOOL_MAX_EXPAND_MILES` in `workers/scoring/detail.py` (and filter in `workers/scoring/compute.py` if needed): beyond cutoff → “No schools found within 25 mi”; access sub-score only uses in-range schools
- [ ] T088 [US2] Restructure `apps/web/src/components/report/ScoreBreakdown.tsx` so the **entire category box** is one activatable control (sub-scores + summary included) with a **stronger hover** highlight (existing tokens only)

**Checkpoint**: Round-2 expand UX MVP on Bentonville after re-score

---

## Phase 17: User Story 3 — Timely/hazard unchanged honesty (Priority: P2)

**Goal**: Round-2 changes must not regress wait tone / hazard unavailable paths

**Independent Test**: Existing timely tone &lt; 75 when wait ≥ national; hazard unavailable still clear

### Tests for User Story 3

- [ ] T089 [P] [US3] Confirm wait `tone_score` &lt; 75 when local ≥ national still passes in `workers/tests/test_score_detail.py` / `apps/api/tests/test_score_hazard_timely.py`

### Implementation for User Story 3

- [ ] T090 [US3] Smoke-check `workers/scoring/detail.py` ER wait + hazard unavailable paths after round-2 edits (fix only if regressions)

**Checkpoint**: SC-005 / SC-009 still hold

---

## Phase 18: User Story 4 — Operator ACS + re-score (Priority: P2)

**Goal**: Documented smoke path loads ACS population and force-rescores so Safety/Schools JSON match round 2

**Independent Test**: Follow quickstart: `worker-acs` then `worker-scoring` under `INGEST_SCOPE=smoke`; Bentonville SC-010–SC-012

### Tests for User Story 4

- [ ] T091 [P] [US4] Confirm national refuse tests still pass in `workers/tests/test_scope_refuse_national.py`

### Implementation for User Story 4

- [ ] T092 [US4] Align `specs/004-report-subscores/quickstart.md` with ACS B01003 + 25 mi + per-resident Safety checklist after implementation
- [ ] T093 [US4] Run Compose `worker-acs` then `worker-scoring` with `INGEST_SCOPE=smoke` `INGEST_FORCE=1`; spot-check Bentonville Safety/Schools/Healthcare expand

**Checkpoint**: Local DB `score_detail` matches round-2 contract

---

## Phase 19: Polish & Cross-Cutting Validation

- [ ] T094 [P] Run worker pytest for safety/detail/school/tone in `workers/tests/`
- [ ] T095 [P] Run API pytest for score/subscores/hazard-timely in `apps/api/tests/`
- [ ] T096 [P] Run web Vitest for `score-breakdown-expand` (+ report-score-unavailable) in `apps/web/src/__tests__/`
- [ ] T097 Manual Bentonville checklist: per-resident Safety, `★-`, no distant Pre-K, full-box click + strong hover (`quickstart.md` V2)
- [ ] T098 [P] Confirm `SCORE_UNAVAILABLE` unchanged in `apps/web/src/__tests__/report-score-unavailable.test.tsx`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phases 1–13**: Complete
- **Phase 14**: Blocks US1 safety rate + US2 Safety copy that needs real pop
- **US1 (Phase 15)**: After T075–T077 (pop available in code path; data via T093)
- **US2 (Phase 16)**: T086–T088 can start after constants/UI; T085 needs T080
- **US3 (Phase 17)**: After detail edits (regression)
- **US4 (Phase 18)**: After code complete; ACS + re-score
- **Phase 19**: After desired stories

### User Story Dependencies (round 2)

- **US1**: Population-normalized safety score math
- **US2**: Expand copy + ER/schools/UI — MVP for user-visible wins; Safety expand copy depends on US1 ratio
- **US3**: Regression only
- **US4**: Operator refresh

### Parallel Opportunities

- T075 / T076 / T078 parallel in Phase 14 (T077 after client supports B01003)
- T082–T084 parallel US2 tests
- T086 / T087 / T088 parallel once T085 not conflicting on `detail.py` (prefer one agent on detail)
- T094–T096 / T098 parallel in Phase 19

---

## Parallel Example: User Story 2 (round 2)

```bash
# Tests in parallel:
Task: "workers/tests/test_score_detail.py ★- / 25mi / per-resident copy"
Task: "apps/web/.../score-breakdown-expand.test.tsx full-box + hover"
Task: "apps/api/tests/test_score_subscores.py contract assertions"

# Then:
Task: "safety.py + detail.py Safety copy"
Task: "detail.py ER ★- + school cutoff"
Task: "ScoreBreakdown.tsx full-box + stronger hover"
```

---

## Implementation Strategy

### Round-2 MVP

1. Phase 14 — ACS population + `SCHOOL_MAX_EXPAND_MILES`  
2. Phase 15 US1 — per-resident safety score  
3. Phase 16 US2 — expand copy, `★-`, 25 mi, full-box UI  
4. **STOP** — smoke ACS + re-score + Bentonville checklist  

### Suggested MVP scope

**Phase 14 + US1 + US2** — fixes misleading Safety stat, distant schools, star alignment, and box affordance.

---

## Notes

- Never fall back to absolute county÷state share for user-facing violent crime
- Never list schools beyond 25 miles
- Fair Housing–neutral Safety wording only
- Refuse `INGEST_SCOPE=national` unchanged
- Plan + this `tasks.md` stay **uncommitted** until `/speckit-implement` Commit #2
