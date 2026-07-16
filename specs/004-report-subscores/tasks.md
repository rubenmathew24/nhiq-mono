# Tasks: Report Sub-Scores & Category Detail

**Input**: Design documents from `/specs/004-report-subscores/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Scope lock**: Local Compose only; `INGEST_SCOPE` ∈ {`smoke`, `metro_10`} — not national.

**Status**: First implement (T001–T044) **complete**. Open work is **UX polish** (T045+) per plan revision 2026-07-16.

**Tests**: Constitution VI — pytest in `workers/tests/` and `apps/api/tests/`; Vitest in `apps/web/src/__tests__/`.

**Organization**: By user story. Polish build order: `tone_score` contract → plain-English detail rewrite (US2-heavy) → wait tone with timely data (US3) → operator re-score (US4).

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

## Phase 1–7: First implement (COMPLETE)

All tasks T001–T044 from the original plan are done (`[x]`). Schema, FEMA/Timely workers, `score_detail`, API `sub_scores`, and initial accordion UI shipped. Do not re-open unless converge finds gaps.

<details>
<summary>Completed task IDs (T001–T044)</summary>

- T001–T010 Setup + Foundational (SQL, SubScore types, `detail.py`, score_service)
- T011–T018 US1 sub-scores
- T019–T025 US2 expand + accordion
- T026–T034 US3 FEMA + CMS Timely
- T035–T039 US4 Compose operator path
- T040–T044 First-wave polish / quickstart

</details>

---

## Phase 8: UX Polish — Foundational (Blocking)

**Purpose**: Additive `tone_score` on expand factors so web can use ScoreBar tiers without client-side wait math

**⚠️ CRITICAL**: Complete before polishing expand value colors (US2/US3)

- [x] T045 [P] Add optional `tone_score: float | None` to Pydantic `Factor` in `apps/api/app/schemas/score.py`
- [x] T046 [P] Add optional `tone_score?: number` to `Factor` in `apps/web/src/types/api.ts`
- [x] T047 Pass through `tone_score` from `score_detail.stats` → API `factors` in `apps/api/app/services/score_service.py` (omit or null when absent; never invent)
- [x] T048 [P] Extend mock report factors with sample `tone_score` where useful in `apps/api/app/data/mock_report.py`

**Checkpoint**: Contract supports ScoreBar-aligned factor coloring

---

## Phase 9: User Story 1 — Sub-score labels & staffing limited (Priority: P1)

**Goal**: Sub-score labels match plain-English Key Entities; Schools staffing is limited-data without PTR proxy

**Independent Test**: Bentonville report after re-score shows “Crimes against people/property”; Schools staffing shows limited data (not a fake PTR-driven staffing score)

### Tests for User Story 1

- [x] T049 [P] [US1] Update/extend unit tests for safety sub-score labels + staffing `available: false` in `workers/tests/test_score_detail.py`

### Implementation for User Story 1

- [x] T050 [US1] Rename safety sub-score user labels to “Crimes against people” / “Crimes against property” in `workers/scoring/detail.py` (keep ids `personal` / `property`)
- [x] T051 [US1] Mark education staffing sub-score `available: false` (do not use pupil–teacher as staffing) and adjust access blend inputs for schools-by-level when available in `workers/scoring/detail.py`
- [x] T052 [US1] Confirm web still renders limited-data sub-scores correctly in `apps/web/src/components/report/ScoreBreakdown.tsx` (no code change if already correct)

**Checkpoint**: US1 labels honest for non-technical readers

---

## Phase 10: User Story 2 — Interactive boxes + plain-English expand (Priority: P1) 🎯 Polish MVP

**Goal**: Obvious category boxes; glanceable expand stats for all five pillars per revised FR-004…FR-009 / FR-019

**Independent Test**: Bentonville report — boxes look clickable; Healthcare ordinals + wait tone; Safety plain English + condensed meta; Environment no `open_meteo`; Schools by level no PTR/locale; Economy includes employment rate

### Tests for User Story 2

- [x] T053 [P] [US2] Unit tests for ER ordinal labels, safety plain-English names, AQI without source id, schools-by-level stats, employment rate, no PTR/locale in `workers/tests/test_score_detail_stats.py` (extend or sibling)
- [x] T054 [P] [US2] Vitest: category renders as interactive box (no “View details”-only affordance); expand/collapse; factor value uses `scoreTextClass(tone_score)` when present in `apps/web/src/__tests__/score-breakdown-expand.test.tsx`
- [x] T055 [P] [US2] API assertions that factors omit raw offense codes / `open_meteo` / “Also nearby” and may include `tone_score` in `apps/api/tests/test_score_subscores.py`

### Implementation for User Story 2

- [x] T056 [US2] Rewrite Healthcare expand stats in `workers/scoring/detail.py`: labels `Nearest ER` / `2nd nearest ER` / `3rd nearest ER`; set ER wait `tone_score` from timeliness score; tighten `_timeliness_score` / impact so wait ≈/above national (and vs primary bench) is not ScoreBar “good” (≥75)
- [x] T057 [US2] Rewrite Safety expand stats in `workers/scoring/detail.py`: full offense names (Homicide, Robbery, Assault, Burglary, Larceny); user-friendly vs-state line; single condensed geography + agencies line (not many agency rows)
- [x] T058 [US2] Rewrite Environment AQI expand value in `workers/scoring/detail.py` to `"{aqi} · {category}"` only (no `open_meteo` / `epa_aqs`); set `tone_score` from air sub-score when useful
- [x] T059 [US2] Implement schools-by-level nearest stats (Pre-K / Elementary / Middle / Junior High / High when data distinguishes) in `workers/scoring/detail.py` + gather per-level nearests in `workers/scoring/compute.py`; remove PTR and locale expand stats; no zoning claim copy
- [x] T060 [US2] Add Economy “Share of labor force employed” from ACS `employed` / `labor_force` in `workers/scoring/detail.py` + pass fields from `workers/scoring/compute.py`
- [x] T061 [US2] Restyle `ScoreBreakdown` categories as interactive boxes (border/surface, full-control activate, chevron ok) and remove reliance on “View details” microcopy in `apps/web/src/components/report/ScoreBreakdown.tsx`
- [x] T062 [US2] Color expanded factor **values** with `scoreTextClass(tone_score)` when `tone_score` present (else `impact` fallback) in `apps/web/src/components/report/ScoreBreakdown.tsx`

**Checkpoint**: Polish MVP — plain-English expand + obvious boxes on existing smoke data after re-score

---

## Phase 11: User Story 3 — Wait / hazard tone with collected data (Priority: P2)

**Goal**: When CMS Timely / FEMA rows exist, Healthcare wait and Environment hazard expand stay plain English and correctly tier-colored; unavailable when missing

**Independent Test**: Smoke with timely loaded — ER wait shows comparisons + non-green when ≥ national; missing timely → Unavailable; hazard unavailable without inventing flood

### Tests for User Story 3

- [x] T063 [P] [US3] Unit test: local wait ≥ national bench → `tone_score` &lt; 75 in `workers/tests/test_score_detail.py` or `workers/tests/test_cms_timely_transform.py`
- [x] T064 [P] [US3] API/fixture assertions for wait `tone_score` + hazard unavailable copy in `apps/api/tests/test_score_hazard_timely.py` (extend)

### Implementation for User Story 3

- [x] T065 [US3] Finalize ER wait expand copy (minutes + state/national in plain English) and `tone_score` wiring when timely present in `workers/scoring/detail.py`
- [x] T066 [US3] Ensure hazard expand stats remain plain English / unavailable path unchanged (no fabricated flood) in `workers/scoring/detail.py`

**Checkpoint**: SC-005 / SC-009 satisfied when data present or absent

---

## Phase 12: User Story 4 — Operator re-score after polish (Priority: P2)

**Goal**: Documented force re-score refreshes `score_detail` JSON for smoke (then metro_10); no national

**Independent Test**: Follow updated quickstart V1–V2; Bentonville expand matches polish checklist without web calling government APIs

### Tests for User Story 4

- [x] T067 [P] [US4] Confirm national refuse tests still pass in `workers/tests/test_scope_refuse_national.py` (no regression)

### Implementation for User Story 4

- [x] T068 [US4] Align `specs/004-report-subscores/quickstart.md` polish checklist with final labels / `tone_score` behavior after implementation
- [x] T069 [US4] Run `INGEST_SCOPE=smoke INGEST_FORCE=1` scoring (and timely if needed) via Compose `worker-scoring` / `worker-cms-timely` so local DB `score_detail` matches polish; spot-check Bentonville

**Checkpoint**: Operator path refreshes polish JSON on fixture DB

---

## Phase 13: Polish & Cross-Cutting Validation

**Purpose**: End-to-end confidence for UX polish

- [x] T070 [P] Run worker pytest subset for detail/stats/tone/timely in `workers/tests/`
- [x] T071 [P] Run API pytest for score/subscores/hazard-timely in `apps/api/tests/`
- [x] T072 [P] Run web Vitest for `score-breakdown-expand` (+ related report tests) in `apps/web/src/__tests__/`
- [x] T073 Manual Bentonville checklist: boxes, ordinals, wait color, safety English, no `open_meteo`, schools-by-level, employment rate (`quickstart.md` V2)
- [x] T074 [P] Confirm `SCORE_UNAVAILABLE` unchanged in `apps/web/src/__tests__/report-score-unavailable.test.tsx`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phases 1–7**: Complete (do not block polish)
- **Phase 8 Foundational**: Blocks factor coloring (T062) and preferably wait tone tests
- **US1 (Phase 9)**: After Phase 8 optional; can parallel with early US2 detail work on different concerns
- **US2 (Phase 10)**: After Phase 8 for tone coloring; detail label tasks T056–T060 can start once T045–T047 types exist for `tone_score` in stats dict
- **US3 (Phase 11)**: After T056 wait formula; extends US2 healthcare/env
- **US4 (Phase 12)**: After detail rewrite tasks land (needs code before re-score acceptance)
- **Phase 13**: After desired polish stories complete

### User Story Dependencies (polish)

- **US1**: Label/staffing honesty — independent of boxes
- **US2**: Main polish MVP — depends on Phase 8 for web tone; depends on compute school/ACS fields for T059–T060
- **US3**: Wait/hazard with collected data — depends on T056 formula
- **US4**: Re-score operator path — depends on scoring code complete

### Parallel Opportunities

- T045–T046–T048 parallel in Phase 8
- T053–T055 parallel US2 tests
- T057 / T058 / T060 parallel after shared `_stat` helper stable (watch `detail.py` conflicts — prefer sequential if one agent)
- T061–T062 after types; can parallel with worker detail if different owners
- T070–T072–T074 parallel in Phase 13

---

## Parallel Example: User Story 2 (polish)

```bash
# Tests in parallel:
Task: "workers/tests/test_score_detail_stats.py polish assertions"
Task: "apps/web/src/__tests__/score-breakdown-expand.test.tsx boxes + tone"
Task: "apps/api/tests/test_score_subscores.py plain-English factors"

# Then (prefer one agent on detail.py):
Task: "detail.py healthcare/safety/env/schools/economy rewrite"
Task: "compute.py schools-by-level + ACS employment fields"
Task: "ScoreBreakdown.tsx boxes + tone_score coloring"
```

---

## Implementation Strategy

### Polish MVP (recommended)

1. Phase 8 — `tone_score` contract  
2. Phase 10 US2 — boxes + plain-English expand (includes most user-visible wins)  
3. Phase 9 US1 labels if not already done inside T056–T051  
4. **STOP** — Bentonville smoke re-score + V2 checklist  

### Incremental

1. US2 polish MVP → demo  
2. US3 wait tone hardening → SC-009  
3. US4 operator re-score + metro_10 spot-check  
4. Phase 13 automated + manual validation  

### Suggested MVP scope

**Phase 8 + User Story 2 (Phase 10)** — interactive boxes and plain-English expand stats. US1 label tweaks and US3 wait-tone hardening are immediate follow-ons before close.

---

## Notes

- Do not invent flood/wait; do not surface `open_meteo` in factors
- No school zoning ingest; no PTR/locale in expand
- Refuse `INGEST_SCOPE=national` unchanged
- Overall category weights 25/25/20/15/15 unchanged
- Plan + this `tasks.md` stay **uncommitted** until `/speckit-implement` Commit #2
- Avoid NPPES/Zillow/HCAHPS scope creep
