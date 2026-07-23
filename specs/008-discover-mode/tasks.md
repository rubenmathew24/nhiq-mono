# Tasks: Discover Mode (City Score Map)

**Input**: Design documents from `/specs/008-discover-mode/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Constitution VI — API tests in `apps/api/tests/`; web tests in `apps/web/src/__tests__/`.

**Organization**: Setup → Foundation → US1 (header + place search → map) → US2 (tracts API + choropleth) → US3 (tract popup) → Polish

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete work)
- **[Story]**: US1 / US2 / US3
- Include exact file paths in descriptions

## Path Conventions

- **Web**: `apps/web/src/`
- **API**: `apps/api/app/` (thin routes; logic in `services/`), tests in `apps/api/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm docs and scaffolding touch-points for Discover

- [x] T001 Confirm feature docs present under `specs/008-discover-mode/` (plan, research, data-model, contracts/discover-api.md, quickstart)
- [x] T002 [P] Add Discover env notes (Places + Mapbox GL via `NEXT_PUBLIC_MAPBOX_TOKEN`) to `.env.example` if missing

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared API/web contracts and router wiring required before story UI/data work

**⚠️ CRITICAL**: No user story implementation until this phase completes

- [x] T003 Add Pydantic request/response models for discover tracts in `apps/api/app/schemas/discover.py` per `specs/008-discover-mode/contracts/discover-api.md`
- [x] T004 [P] Add Zod/TS types for discover tracts response in `apps/web/src/types/discover.ts` (or `apps/web/src/types/api.ts`)
- [x] T005 Create `discover_service` skeleton with bbox validation helpers (inverted/empty/too-large) in `apps/api/app/services/discover_service.py`
- [x] T006 Add thin `GET /discover/tracts` route stub in `apps/api/app/api/v1/endpoints/discover.py` and register in `apps/api/app/api/v1/router.py`
- [x] T007 [P] Add relative-score color helper stub in `apps/web/src/lib/discoverColors.ts` (min/max → ramp; gray for null)

**Checkpoint**: Foundation ready — user stories can proceed

---

## Phase 3: User Story 1 — Open Discover and search a city (Priority: P1) 🎯 MVP

**Goal**: Header **Discover** tab → public `/discover` place autocomplete → `/discover/map` with place label and locked basemap (bbox from Places)

**Independent Test**: Signed-out: header → Discover → type city → select suggestion → map page shows place name and a Mapbox map focused/locked to that bbox (tract overlay not required yet)

### Tests for User Story 1

- [x] T008 [P] [US1] Web test: place suggestion select builds map URL/query params in `apps/web/src/__tests__/discover-place-search.test.tsx`
- [x] T009 [P] [US1] Web test: Discover appears in nav links / header config in `apps/web/src/__tests__/discover-nav.test.tsx` (or extend an existing nav test)

### Implementation for User Story 1

- [x] T010 [P] [US1] Add `{ href: "/discover", label: "Discover" }` to `navLinks` in `apps/web/src/content/landing.ts`
- [x] T011 [P] [US1] Create Discover entry page with place search shell in `apps/web/src/app/discover/page.tsx`
- [x] T012 [US1] Implement place autocomplete (Mapbox Places, US, `types` place/locality, debounce) in `apps/web/src/components/discover/DiscoverPlaceSearch.tsx` — extract bbox (or padded center fallback) and navigate to map; do **not** call `/lookup` or save user history
- [x] T013 [US1] Create map route reading `place` + bbox query params in `apps/web/src/app/discover/map/page.tsx` with clear errors for missing/invalid params
- [x] T014 [US1] Implement locked basemap (`maxBounds` from bbox) in `apps/web/src/components/discover/DiscoverMap.tsx` reusing Mapbox GL patterns from `apps/web/src/components/report/MapView.tsx`
- [x] T015 [US1] Show selected place title/label on map page and user-facing empty-suggestion / no-token messaging in Discover components under `apps/web/src/components/discover/`

**Checkpoint**: US1 — search → locked basemap works without tracts API

---

## Phase 4: User Story 2 — Explore scored census tracts on a locked map (Priority: P1)

**Goal**: Fetch tracts-in-bbox from API; choropleth by relative overall score; gray unscored; partial/empty banners; geometry simplify + caps

**Independent Test**: Open a place with mixed coverage → colored + gray tracts, relative legend, partial banner; empty-score place → basemap + clear empty message; pan/zoom still locked

### Tests for User Story 2

- [x] T016 [P] [US2] API contract tests: valid bbox hit/miss, partial scores, invalid/too-large bbox, no writes to lookups in `apps/api/tests/test_discover.py`
- [x] T017 [P] [US2] Unit tests for relative color helper (min/max/single/null) in `apps/web/src/__tests__/discover-colors.test.ts`
- [x] T018 [P] [US2] Web tests for partial vs empty coverage banner branches in `apps/web/src/__tests__/discover-coverage.test.tsx`

### Implementation for User Story 2

- [x] T019 [US2] Implement PostGIS intersect + score join + simplify + feature cap + meta counts in `apps/api/app/services/discover_service.py` (active `SCORE_DATA_VINTAGE`; left join `overall_score`)
- [x] T020 [US2] Wire full response + `400`/`INVALID_BBOX`/`BBOX_TOO_LARGE` + structured logging in `apps/api/app/api/v1/endpoints/discover.py` (thin handler calling service only)
- [x] T021 [US2] Fetch tracts via `apiFetch` on map page/load in `apps/web/src/app/discover/map/page.tsx` (or loader component) with zod parse from `apps/web/src/types/discover.ts`
- [x] T022 [US2] Add GeoJSON fill/line layers + relative fill colors + gray null scores in `apps/web/src/components/discover/DiscoverMap.tsx`
- [x] T023 [P] [US2] Add relative legend component in `apps/web/src/components/discover/DiscoverLegend.tsx`
- [x] T024 [P] [US2] Add partial-coverage and empty-coverage banners in `apps/web/src/components/discover/DiscoverCoverageBanner.tsx`
- [x] T025 [US2] Handle `meta.truncated` and API/user-correctable errors with clear copy (Constitution VIII) in Discover map UI under `apps/web/src/components/discover/`

**Checkpoint**: US2 — choropleth + coverage messaging complete

---

## Phase 5: User Story 3 — Inspect a tract’s overall score (Priority: P2)

**Goal**: Hover/click popup with overall score or unavailable; stay on Discover (no report navigation)

**Independent Test**: Click scored tract → score popup; unscored → unavailable; dismiss/switch tract → still on `/discover/map` (no `/report/...`)

### Tests for User Story 3

- [x] T026 [P] [US3] Web test: popup copy for scored vs unscored (and no report href) in `apps/web/src/__tests__/discover-popup.test.tsx`

### Implementation for User Story 3

- [x] T027 [US3] Add click/hover `queryRenderedFeatures` + Mapbox Popup for score/unavailable in `apps/web/src/components/discover/DiscoverMap.tsx`
- [x] T028 [US3] Ensure popup shows `geoid` (optional) + overall score only — no link/navigation to report routes in `apps/web/src/components/discover/DiscoverMap.tsx`
- [x] T029 [US3] Dismiss/replace popup on map click-away or new selection without leaving the page in `apps/web/src/components/discover/DiscoverMap.tsx`

**Checkpoint**: US3 — inspect scores via popup

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening and validation across stories

- [x] T030 [P] Confirm Discover never calls lookup/save/touch user APIs (code review + grep) across `apps/web/src/components/discover/` and `apps/web/src/app/discover/`
- [x] T031 [P] Verify `/discover` and `/discover/map` are public (not gated in `apps/web/src/middleware.ts`)
- [x] T032 Run quickstart scenarios in `specs/008-discover-mode/quickstart.md` and fix gaps found
- [x] T033 [P] Run `cd apps/api && pytest tests/test_discover.py -q` and `cd apps/web && npm test -- --run src/__tests__/discover*.test.*` — ensure green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: None
- **Foundational (Phase 2)**: Depends on Setup — **blocks** all user stories
- **US1 (Phase 3)**: After Foundation — MVP (search + locked basemap)
- **US2 (Phase 4)**: After Foundation; practically after US1 map shell exists for integration, but API work (T019–T020) can start in parallel with US1 UI
- **US3 (Phase 5)**: After US2 map layers exist (needs GeoJSON source for hit-testing)
- **Polish (Phase 6)**: After desired stories complete

### User Story Dependencies

- **US1 (P1)**: No dependency on US2/US3
- **US2 (P1)**: Uses US1 map page/route; API can be built in parallel
- **US3 (P2)**: Depends on US2 overlay layers

### Parallel Opportunities

- T002 || T001 (setup)
- T003 || T004 || T007 (foundation files)
- T008 || T009 (US1 tests)
- T010 || T011 (US1 nav + page shell)
- T016 || T017 || T018 (US2 tests)
- T023 || T024 (US2 legend + banners)
- T030 || T031 || T033 (polish)

---

## Parallel Example: User Story 1

```bash
# Tests in parallel:
Task: "Web test place→map URL in apps/web/src/__tests__/discover-place-search.test.tsx"
Task: "Web test Discover nav in apps/web/src/__tests__/discover-nav.test.tsx"

# Early UI in parallel:
Task: "Add Discover to navLinks in apps/web/src/content/landing.ts"
Task: "Create apps/web/src/app/discover/page.tsx"
```

## Parallel Example: User Story 2

```bash
# After foundation:
Task: "API tests in apps/api/tests/test_discover.py"
Task: "Color helper tests in apps/web/src/__tests__/discover-colors.test.ts"
Task: "Coverage banner tests in apps/web/src/__tests__/discover-coverage.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundation
3. Phase 3 US1 — header → search → locked basemap
4. **STOP and VALIDATE** US1 independent test
5. Demo if useful, then continue to US2 (core choropleth value)

### Incremental Delivery

1. Setup + Foundation
2. US1 → demo navigation POC
3. US2 → full Discover value (choropleth)
4. US3 → score inspection popups
5. Polish + quickstart

### Suggested MVP scope

**US1 only** for a clickable shell; **US1+US2** for a meaningful product demo (recommended stop before polish if time-boxed).

---

## Notes

- No new SQL migrations/tables for this POC
- Overall score only — no dimension toggles
- Do not persist Discover searches
- Keep business logic in `discover_service.py`; Next.js stays thin
- Commit rhythm: plan+tasks = Commit #2 at start of `/speckit-implement` (this file stays uncommitted until then)
