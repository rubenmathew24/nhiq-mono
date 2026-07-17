# Tasks: Report Sub-Scores & Category Detail

**Input**: Design documents from `/specs/004-report-subscores/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Scope lock**: Local Compose only; `INGEST_SCOPE` ∈ {`smoke`, `metro_10`} — not national.

**Status**: T001–T119 complete (through round 3). Open work is **UX polish round 4** (T120+) — text selection inside category boxes (research.md §13).

**Tests**: Vitest in `apps/web/src/__tests__/`.

**Organization**: Single US2 polish (expand affordance).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable
- **[Story]**: US2 from spec.md
- Exact file paths in every task



## Path Conventions

- Web: `apps/web/src/`



---



## Phase 1–25: Prior work (COMPLETE)

Completed task IDs (T001–T119)



---



## Phase 26: User Story 2 — Text selection in category boxes (Priority: P1) 🎯 MVP

**Goal**: Users can drag-select text inside a category box without toggling expand; a clean click still expands/collapses (SC-014)

**Independent Test**: Vitest click expands; pointer moved beyond threshold does not toggle; manual Bentonville drag-select on summary works after web rebuild

### Tests for User Story 2

- [X] T120 [P] [US2] Vitest: simple click still expands; mousedown→mouseup with large pointer delta does not expand in `apps/web/src/__tests__/score-breakdown-expand.test.tsx`

### Implementation for User Story 2

- [X] T121 [US2] Update `apps/web/src/components/report/ScoreBreakdown.tsx`: allow text selection; toggle only on click without drag/selection; keep whole-box hover + keyboard toggle
- [X] T122 [US2] Rebuild Compose web: `docker compose build web && docker compose up -d web`

**Checkpoint**: Localhost allows copy-select and click-to-expand



---



## Phase 27: Polish

- [X] T123 [P] Confirm `SCORE_UNAVAILABLE` unchanged in `apps/web/src/__tests__/report-score-unavailable.test.tsx`
- [X] T124 Align `specs/004-report-subscores/quickstart.md` V2 drag-select note if needed after implement



---



## Dependencies & Execution Order

- T120 before or with T121 (TDD preferred: write failing/updated tests then implement)
- T122 after T121
- T123–T124 after UI done



### Suggested MVP

**T120–T122** only.



## Notes

- Rebuild `web` required (no bind-mount)
- Plan + tasks uncommitted until `/speckit-implement` Commit #2 (this lean round commits plan+tasks then implementation in the same session)



---



## Phase 28: Convergence

- [X] T125 Align published Schools category score with Access sub-score (by-level proximity ≤ `SCHOOL_MAX_EXPAND_MILES`) and exclude PTR/locale staffing from the category while Staffing is limited-data — update `workers/scoring/compute.py` / `workers/scoring/education.py` (and re-score path) so sub-scores explain the category per US1/AC2, Key Entities (Schools), research.md §10.5 (contradicts)
- [X] T126 Rewrite Schools category summary when staffing is limited-data so it does not claim “staffing signals” / Urban CCD staffing — `apps/api/app/services/score_service.py` `_education_summary` (and mock copy if needed) per FR-007 / research.md §10.5 (contradicts)



---



## Phase 29: Convergence

- [X] T127 CRITICAL: When personal-crime (people) offenses exist but state benchmarks are missing, mark Crimes against people / personal safety unavailable (do not synthesize `state = local` under population normalization) — update `workers/scoring/safety.py` `_weighted_local_state` / `safety_from_cde` and wire detail limited-data the same way as property (`workers/scoring/detail.py` `_property_safety` pattern); add regression test in `workers/tests/` per FR-011 (and FR-021 failure mode) (contradicts)
- [X] T128 Allow expand-panel chrome clicks to collapse the category (remove or replace `stopPropagation` on the expanded panel in `apps/web/src/components/report/ScoreBreakdown.tsx`) while keeping SC-014 text-selection / drag-without-toggle behavior; extend Vitest if needed per FR-004 / US2/AC3 (partial)
