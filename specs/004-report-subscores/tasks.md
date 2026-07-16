# Tasks: Report Sub-Scores & Category Detail

**Input**: Design documents from `/specs/004-report-subscores/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Scope lock**: Local Compose only; `INGEST_SCOPE` ∈ {`smoke`, `metro_10`} — not national.

**Status**: First implement (T001–T044), UX polish round 1 (T045–T074), and round 2 (T075–T098) **complete**. Open work is **UX polish round 3** (T099+) per plan revision 2026-07-16 §12 — property false-zero, school cutoff **30 mi**, full-box expand on running Compose web.

**Tests**: Constitution VI — pytest in `workers/tests/` and `apps/api/tests/`; Vitest in `apps/web/src/__tests__/`.

**Organization**: By user story. Round-3 order: property availability fix (US1) → schools 30 mi + full-box UI + web rebuild (US2) → regression (US3) → force re-score + Bentonville verify (US4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no incomplete blockers)
- **[Story]**: US1…US4 from spec.md
- Exact file paths in every task



## Path Conventions

- Workers: `workers/ingest/<source>/`, `workers/scoring/`
- API: `apps/api/app/`, tests `apps/api/tests/`
- Web: `apps/web/src/`
- SQL: `infra/sql/`
- Compose: `docker-compose.yml`, `docker/web.Dockerfile`



---



## Phase 1–19: Prior work (COMPLETE)

Completed task IDs (T001–T098)

- T001–T044 First implement (schema, FEMA/Timely, sub_scores, accordion)
- T045–T074 UX polish round 1 (tone_score, plain English, ordinals, boxes, employment rate)
- T075–T098 UX polish round 2 (ACS B01003, per-resident Safety personal, ER `★-`, 25 mi schools, source full-box)



---



## Phase 20: Round 3 — Foundational (school cutoff constant)

**Purpose**: Raise expand cutoff to 30 miles before Schools expand/access tasks (research.md §12.2).

- [X] T099 [P] Set `SCHOOL_MAX_EXPAND_MILES = 30` in `workers/ingest/fixtures/constants.py`

**Checkpoint**: Constant is 30; detail/copy will pick it up via import



---



## Phase 21: User Story 1 — Property sub-score honesty (Priority: P1)

**Goal**: Crimes against property is never a scored `0` when state benchmarks are missing; show limited-data instead (FR-021 / SC-013)

**Independent Test**: Unit test with Bentonville-like crime (BUR present, benches null) → property `available: false`, score not presented as 0; after smoke re-score Bentonville matches

### Tests for User Story 1

- [X] T100 [P] [US1] Unit test: property offenses without state benches → `available: false` (not score 0) in `workers/tests/test_score_detail.py`
- [X] T101 [P] [US1] Unit test: property with benches + pops still scores via per-resident ratio in `workers/tests/test_score_detail.py` (or `test_safety_formula.py` if helper extracted)

### Implementation for User Story 1

- [X] T102 [US1] Fix `_property_safety` in `workers/scoring/detail.py`: require ≥1 non-null property state benchmark before scoring; if only local counts exist → return `None` (no `state = local` under population normalization)
- [X] T103 [US1] Confirm `compute.py` / `build_score_detail` property sub-score path uses the fixed helper so category blend skips unavailable property in `workers/scoring/compute.py` and `workers/scoring/detail.py`

**Checkpoint**: Synthetic false-zero path gone; personal per-resident path unchanged



---



## Phase 22: User Story 2 — Schools 30 mi + full-box on localhost (Priority: P1) 🎯 MVP

**Goal**: Schools expand uses 30 mi cutoff; clicking/hovering **anywhere** on the category box (title, sub-scores, summary) expands/highlights the whole box on the running Compose web (SC-011 / SC-012)

**Independent Test**: Vitest clicks Access + summary; after `docker compose build web && up -d web`, Bentonville UI expands from sub-score/summary click with whole-box hover

### Tests for User Story 2

- [X] T104 [P] [US2] Update school cutoff tests to 30 mi / “No schools found within 30 mi” in `workers/tests/test_score_detail.py`
- [X] T105 [P] [US2] Harden Vitest: click sub-score **and** summary toggles expand; hover class on outer control in `apps/web/src/__tests__/score-breakdown-expand.test.tsx`
- [X] T106 [P] [US2] API/contract smoke assertion: education factors must not list absurd distances; property availability semantics noted in `apps/api/tests/test_score_subscores.py` if fixtures cover it

### Implementation for User Story 2

- [X] T107 [US2] Ensure schools expand + access filter use `SCHOOL_MAX_EXPAND_MILES` (30) in `workers/scoring/detail.py` (copy string via constant)
- [X] T108 [US2] Verify/adjust `apps/web/src/components/report/ScoreBreakdown.tsx` so one control wraps title, score bar, **sub-score rows**, and **summary**; whole-box hover highlight; no header-only hit target
- [X] T109 [US2] Rebuild and restart Compose web so localhost:3000 serves the control: `docker compose build web && docker compose up -d web` (document if anything else needed; prefer rebuild over bind-mount unless rebuild fails acceptance)

**Checkpoint**: Source + running image both full-box; schools text says 30 mi



---



## Phase 23: User Story 3 — No regression on wait/hazard (Priority: P2)

**Goal**: Round-3 edits must not regress ER wait tone or hazard unavailable

**Independent Test**: Existing timely tone < 75 when wait ≥ national still passes

### Tests for User Story 3

- [X] T110 [P] [US3] Confirm wait `tone_score` < 75 when local ≥ national still passes in `workers/tests/test_score_detail.py` / `apps/api/tests/test_score_hazard_timely.py`

### Implementation for User Story 3

- [X] T111 [US3] Smoke-check ER wait + hazard unavailable paths in `workers/scoring/detail.py` after property/school edits (fix only if regressions)

**Checkpoint**: SC-005 / SC-009 still hold



---



## Phase 24: User Story 4 — Operator re-score + Bentonville verify (Priority: P2)

**Goal**: Force re-score smoke and verify Bentonville property/schools/UI against quickstart V2

**Independent Test**: Follow `quickstart.md` V1–V2; Bentonville SC-011–SC-013

### Tests for User Story 4

- [X] T112 [P] [US4] Confirm national refuse tests still pass in `workers/tests/test_scope_refuse_national.py`

### Implementation for User Story 4

- [X] T113 [US4] Align `specs/004-report-subscores/quickstart.md` with property limited-data + 30 mi + web rebuild checklist (if any drift after implement)
- [X] T114 [US4] Run Compose `worker-scoring` with `INGEST_SCOPE=smoke` `INGEST_FORCE=1`; spot-check Bentonville `score_detail` property sub-score + schools copy in DB
- [X] T115 [US4] Manual Bentonville UI checklist on `http://localhost:3000` after web rebuild (`quickstart.md` V2)

**Checkpoint**: Local DB + UI match round-3 contract



---



## Phase 25: Polish & Cross-Cutting Validation

- [X] T116 [P] Run worker pytest for property/school/detail in `workers/tests/`
- [X] T117 [P] Run API pytest for score/subscores/hazard-timely in `apps/api/tests/`
- [X] T118 [P] Run web Vitest for `score-breakdown-expand` (+ `report-score-unavailable`) in `apps/web/src/__tests__/` (Node 20+)
- [X] T119 [P] Confirm `SCORE_UNAVAILABLE` unchanged in `apps/web/src/__tests__/report-score-unavailable.test.tsx`



---



## Dependencies & Execution Order



### Phase Dependencies

- **Phases 1–19**: Complete
- **Phase 20**: Unblocks Schools 30 mi copy (T107); can run parallel with US1 code
- **US1 (Phase 21)**: Property fix — no dependency on 30 mi constant
- **US2 (Phase 22)**: After T099 for school tests/copy; UI rebuild after T108
- **US3 (Phase 23)**: After detail edits
- **US4 (Phase 24)**: After US1+US2 code; scoring + web rebuild
- **Phase 25**: After desired stories



### User Story Dependencies (round 3)

- **US1**: Property limited-data when benches missing (P1)
- **US2**: 30 mi schools + full-box on localhost (P1 MVP with US1)
- **US3**: Regression only
- **US4**: Operator refresh + manual verify



### Parallel Opportunities

- T099 // T100–T101 (constant vs property tests)
- T104 / T105 / T106 parallel US2 tests
- T107 and T108 parallel (different files) after T099
- T116–T119 parallel in Phase 25



---



## Parallel Example: Round 3 MVP

```bash
# Parallel:
Task: "detail.py _property_safety benches required"
Task: "constants.py SCHOOL_MAX_EXPAND_MILES = 30"
Task: "ScoreBreakdown.tsx full-box verify"

# Then:
Task: "worker-scoring smoke force"
Task: "docker compose build web && up -d web"
Task: "Bentonville checklist"
```

---



## Implementation Strategy



### Round-3 MVP

1. Phase 21 US1 — property unavailable (not 0)
2. Phase 20 + Phase 22 US2 — 30 mi + full-box + **rebuild web**
3. **STOP** — smoke re-score + Bentonville UI checklist



### Suggested MVP scope

**US1 + US2** — stops false property zero, distant-school cutoff at 30 mi, and makes localhost expand match the intended whole-box control.



---



## Notes

- Never synthesize `state = local` under population normalization for property
- Never fall back to absolute county÷state share for user-facing violent crime
- Never list schools beyond **30** miles
- Fair Housing–neutral Safety wording only
- Compose `web` has no source bind-mount — **rebuild required** to verify UI
- Refuse `INGEST_SCOPE=national` unchanged
- Plan + this `tasks.md` stay **uncommitted** until `/speckit-implement` Commit #2
