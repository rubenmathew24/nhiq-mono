# Tasks: Report Sub-Scores & Category Detail

**Input**: Design documents from `/specs/004-report-subscores/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Scope lock**: Local Compose only; `INGEST_SCOPE` ∈ {`smoke`, `metro_10`} — not national.

**Tests**: Constitution VI — pytest in `workers/tests/` and `apps/api/tests/`; Vitest in `apps/web/src/__tests__/`.

**Organization**: By user story. Build order: schema/API types → sub-scores from existing data (US1) → expand stats + accordion (US2) → FEMA + CMS Timely (US3) → operator Compose path (US4).

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

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Feature scaffolding without changing runtime behavior yet

- [x] T001 Create SQL one-shot `infra/sql/007_report_detail.sql` with comments for `score_detail`, `fema_nri_tracts`, `hospital_timely_measures` per `data-model.md` (tables may be stubbed empty until later tasks fill DDL)
- [x] T002 [P] Mirror `score_detail` + new table DDL essentials into `infra/sql/init.sql` for fresh Compose volumes
- [x] T003 [P] Create package stubs `workers/ingest/fema/__init__.py` and `workers/ingest/cms_timely/__init__.py`
- [x] T004 [P] Add shared detail constants (sub-score ids/labels/weights) in `workers/ingest/fixtures/constants.py` or `workers/scoring/detail_constants.py` per research.md §3

**Checkpoint**: Scaffold + DDL files exist

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Additive schema + typed report contract so US1–US2 can ship on existing raw data

**⚠️ CRITICAL**: No user-story UI/API acceptance until this phase completes

- [x] T005 Apply/complete `ALTER TABLE neighborhood_scores ADD COLUMN IF NOT EXISTS score_detail JSONB NOT NULL DEFAULT '{}'` in `infra/sql/007_report_detail.sql` and `infra/sql/init.sql`
- [x] T006 [P] Add Pydantic `SubScore` and extend `ScoreDimension` with `sub_scores: list[SubScore]` in `apps/api/app/schemas/score.py`
- [x] T007 [P] Add matching `SubScore` / `ScoreDimension.sub_scores` in `apps/web/src/types/api.ts`
- [x] T008 Extend score SELECT + report builder to read `score_detail` in `apps/api/app/services/score_service.py` (map to `sub_scores` + `factors`; empty detail → empty lists, no invented flood/wait)
- [x] T009 [P] Update demo/mock report in `apps/api/app/data/mock_report.py` to include `sub_scores` arrays so existing UI tests do not break shape
- [x] T010 Create `workers/scoring/detail.py` helper API (`build_score_detail(...)` → JSON-serializable dict) with no DB I/O — pure assembly from typed inputs

**Checkpoint**: Schema + types + empty-safe API path ready; scoring can start writing detail

---

## Phase 3: User Story 1 — See dimension scores with sub-scores (Priority: P1) 🎯 MVP

**Goal**: Live reports show labeled sub-scores under each of the five categories from **existing** ingest (no FEMA/Timely required yet)

**Independent Test**: After re-score for `INGEST_SCOPE=smoke`, open Bentonville report; each category shows documented sub-scores (timeliness/hazard may be `available: false`)

### Tests for User Story 1

- [x] T011 [P] [US1] Unit tests for sub-score blends (healthcare access/quality; safety personal/property; education; environment air-only; economic) in `workers/tests/test_score_detail.py`
- [x] T012 [P] [US1] API test that live score response includes `sub_scores` per dimension in `apps/api/tests/test_score_subscores.py`

### Implementation for User Story 1

- [x] T013 [US1] Implement healthcare/safety/education/environment/economic sub-score builders in `workers/scoring/detail.py` (weights per research.md; renormalize when components missing)
- [x] T014 [US1] Extend tract input SQL / loaders in `workers/scoring/compute.py` to gather nearest ER stars/miles, school fields, crime offense map, AQI provenance inputs, ACS/LAUS already used — enough for sub-scores without new tables
- [x] T015 [US1] Persist `score_detail` JSON (sub_scores; stats may be `[]` temporarily) on upsert in `workers/scoring/compute.py`
- [x] T016 [US1] Wire `score_service` summaries to mention limited-data when a sub-score has `available: false` in `apps/api/app/services/score_service.py`
- [x] T017 [US1] Render category score + sub-score mini bars (always visible) in `apps/web/src/components/report/ScoreBreakdown.tsx` matching existing card styling
- [x] T018 [US1] Update web tests that fixture reports in `apps/web/src/__tests__/report-dashboard-link.test.tsx` (and any peers) to include `sub_scores: []` or sample values

**Checkpoint**: MVP — sub-scores visible on live smoke report after re-score

---

## Phase 4: User Story 2 — Expand a category for extra stats (Priority: P1)

**Goal**: Categories are clearly clickable; expand/collapse shows concrete stats (ER, school, crime, AQI, income) from existing tables via `score_detail.stats` → `factors`

**Independent Test**: Affordance visible before click; expand Healthcare/Schools shows name + distance + rating/ratio; collapse works; keyboard/touch usable

### Tests for User Story 2

- [x] T019 [P] [US2] Unit tests that `build_score_detail` emits expected expand `stats` for healthcare/schools fixtures in `workers/tests/test_score_detail_stats.py`
- [x] T020 [P] [US2] Vitest accordion expand/collapse + affordance in `apps/web/src/__tests__/score-breakdown-expand.test.tsx`
- [x] T021 [P] [US2] API test factors populated from `score_detail.stats` in `apps/api/tests/test_score_subscores.py` (extend or sibling)

### Implementation for User Story 2

- [x] T022 [US2] Populate expand `stats` in `workers/scoring/detail.py` / `compute.py` for all five pillars from existing raw tables (nearest ER list ≤3, nearest school, crime vs state + agencies, AQI + source, income + unemployment); Fair Housing–neutral safety wording
- [x] T023 [US2] Ensure Redis report invalidation still runs after score upserts that change `score_detail` in `workers/scoring/compute.py` (or existing invalidation helper)
- [x] T024 [US2] Convert `ScoreBreakdown` into in-place accordion with visible chevron/`View details`, `aria-expanded`, keyboard activation in `apps/web/src/components/report/ScoreBreakdown.tsx`
- [x] T025 [US2] Render expanded `factors` list under the active category in `apps/web/src/components/report/ScoreBreakdown.tsx` (blend with current typography/spacing; no new visual system)

**Checkpoint**: US1 + US2 complete on existing data (P1 product slice)

---

## Phase 5: User Story 3 — Richer environment & healthcare from new data (Priority: P2)

**Goal**: FEMA NRI + CMS Timely ingest for smoke/metro_10; hazard + timeliness sub-scores/stats when present; unavailable when not

**Independent Test**: With FEMA/timely loaded for smoke, Environment expand shows hazard band; Healthcare shows wait vs state; without data, clear unavailable (no fabricated flood/wait)

### Tests for User Story 3

- [x] T026 [P] [US3] FEMA transform / risk→sub-score unit tests in `workers/tests/test_fema_transform.py`
- [x] T027 [P] [US3] CMS Timely transform / wait→sub-score unit tests in `workers/tests/test_cms_timely_transform.py`
- [x] T028 [P] [US3] API/integration assertions for hazard + wait factors when `score_detail` includes them in `apps/api/tests/test_score_hazard_timely.py`

### Implementation for User Story 3

- [x] T029 [US3] Complete `fema_nri_tracts` DDL in `infra/sql/007_report_detail.sql` and `infra/sql/init.sql` per data-model.md
- [x] T030 [US3] Complete `hospital_timely_measures` DDL in `infra/sql/007_report_detail.sql` and `infra/sql/init.sql` per data-model.md
- [x] T031 [US3] Implement FEMA NRI client/transform/load in `workers/ingest/fema/` (ArcGIS tract query; Moderate+ hazards JSONB; upsert by geoid; scope `active_county_fips()`; refuse `INGEST_SCOPE=national`)
- [x] T032 [US3] Implement CMS Timely client/transform/load in `workers/ingest/cms_timely/` (hospital-level ED measures + state/national benchmarks; upsert; scope fixture states/counties; refuse national)
- [x] T033 [US3] Join FEMA + timely into scoring inputs and update blends in `workers/scoring/detail.py` + `workers/scoring/compute.py` (environment air+hazard; healthcare access+quality+timeliness; provenance `fema_nri` / `cms_timely_effective_care` in `score_sources`)
- [x] T034 [US3] Surface hazard/wait unavailable copy in expand stats when components missing in `workers/scoring/detail.py` and API summaries in `apps/api/app/services/score_service.py`

**Checkpoint**: P2 data richness works for smoke when workers run

---

## Phase 6: User Story 4 — Operator prepares data (Priority: P2)

**Goal**: Documented Compose one-offs for FEMA/Timely/scoring under smoke and metro_10; idempotent re-runs

**Independent Test**: Follow `quickstart.md` V1–V3; Bentonville + second metro show populated `score_detail` without web calling government APIs

### Tests for User Story 4

- [x] T035 [P] [US4] Unit test that FEMA/Timely runners raise/refuse on `INGEST_SCOPE=national` in `workers/tests/test_scope_refuse_national.py`

### Implementation for User Story 4

- [x] T036 [US4] Wire `worker-fema` and `worker-cms-timely` Compose profiles in `docker-compose.yml` (`python -m ingest.fema.run` / `ingest.cms_timely.run`, `INGEST_SCOPE` passthrough)
- [x] T037 [P] [US4] Sync `.env.example` notes for smoke/metro_10 report-detail workers (no new secrets required) 
- [x] T038 [US4] Align `specs/004-report-subscores/quickstart.md` commands with final service names / SQL filename after implementation
- [x] T039 [US4] Verify idempotent upserts (second FEMA/Timely/score run) via worker logs + optional assert in `workers/tests/` or documented manual check in quickstart

**Checkpoint**: Operator path matches contracts/worker-cli.md

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end confidence on smoke → metro_10

- [x] T040 [P] Run worker formula/API pytest subset for detail/fema/timely/subscores
- [x] T041 [P] Run web Vitest for report/score-breakdown
- [x] T042 Manual quickstart V1–V3 (`INGEST_SCOPE=smoke` then `metro_10`) and spot-check Bentonville + one other fixture address
- [x] T043 [P] Confirm `SCORE_UNAVAILABLE` path unchanged in `apps/web/src/__tests__/report-score-unavailable.test.tsx`
- [x] T044 Neutral safety copy review (no safe/unsafe steering) in generated safety stats strings in `workers/scoring/detail.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Start immediately
- **Foundational (Phase 2)**: After Setup — **blocks** all stories
- **US1 (Phase 3)**: After Foundational — **MVP**
- **US2 (Phase 4)**: After US1 scoring writes detail (needs T015); UI can start once T008 types exist but acceptance needs stats from T022
- **US3 (Phase 5)**: After Foundational; ideally after US1 detail builder exists (extends `detail.py`)
- **US4 (Phase 6)**: After US3 workers exist (Compose wiring)
- **Polish (Phase 7)**: After desired stories complete

### User Story Dependencies

- **US1**: No dependency on US3/US4 — uses existing hospitals/schools/crime/ACS/EPA
- **US2**: Builds on US1 `score_detail` persistence
- **US3**: Independent ingest; depends on US1 detail module to plug hazard/timely
- **US4**: Depends on US3 entrypoints + Compose

### Parallel Opportunities

- T002–T004 parallel in Setup
- T006–T007–T009 parallel in Foundational
- T011–T012 parallel tests before/during US1 impl
- T019–T021 parallel US2 tests
- T026–T028 parallel US3 tests; T031 and T032 workers in parallel after DDL T029–T030
- T040–T041–T043 parallel in Polish

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Unit tests in workers/tests/test_score_detail.py"
Task: "API test in apps/api/tests/test_score_subscores.py"

# Then implementation:
Task: "detail.py sub-score builders"
Task: "compute.py persist score_detail"
Task: "ScoreBreakdown.tsx sub-score UI"
```

## Parallel Example: User Story 3

```bash
Task: "workers/ingest/fema/ client+load"
Task: "workers/ingest/cms_timely/ client+load"
# after both + DDL:
Task: "scoring detail blends hazard + timeliness"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 Setup  
2. Phase 2 Foundational  
3. Phase 3 US1 — sub-scores on report  
4. **STOP** — validate Bentonville smoke re-score  

### Incremental Delivery

1. US1 → sub-scores visible  
2. US2 → expand stats + accordion (complete P1)  
3. US3 → FEMA + Timely richness  
4. US4 → Compose operator path  
5. Polish quickstart smoke → metro_10  

### Suggested MVP scope

**User Story 1 only** (sub-scores from existing data). US2 is the natural immediate follow-on for the clickable expand experience promised in the product ask.

---

## Notes

- Refuse `INGEST_SCOPE=national` in new workers (feature lock)
- Never invent flood/wait when tables empty
- Keep overall category weights 25/25/20/15/15; only within-category blends change
- Plan + this `tasks.md` stay **uncommitted** until `/speckit-implement` Commit #2
- Avoid NPPES/Zillow/HCAHPS scope creep
