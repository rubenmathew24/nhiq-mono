# Tasks: Discover Mode (City Score Map)

**Input**: Design documents from `/specs/008-discover-mode/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Constitution VI — API tests in `apps/api/tests/`; web tests in `apps/web/src/__tests__/`.

**Organization**: Setup → Foundation → US1 (search → map) → US2 (choropleth) → US3 (popup) → Polish (base) → **US4 foundation** → **US4 city summary** → Polish (expansion)

**Note**: T001–T033 delivered the base Discover POC and remain `[x]`. Open tasks start at **T034** for the city-summary expansion (US4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete work)
- **[Story]**: US1 / US2 / US3 / US4
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

## Phase 6: Polish & Cross-Cutting Concerns (base POC)

**Purpose**: Hardening and validation across US1–US3

- [x] T030 [P] Confirm Discover never calls lookup/save/touch user APIs (code review + grep) across `apps/web/src/components/discover/` and `apps/web/src/app/discover/`
- [x] T031 [P] Verify `/discover` and `/discover/map` are public (not gated in `apps/web/src/middleware.ts`)
- [x] T032 Run quickstart scenarios in `specs/008-discover-mode/quickstart.md` and fix gaps found
- [x] T033 [P] Run `cd apps/api && pytest tests/test_discover.py -q` and `cd apps/web && npm test -- --run src/__tests__/discover*.test.*` — ensure green

**Checkpoint**: Base Discover POC complete

---

## Phase 7: Foundational — City summary contracts (blocks US4)

**Purpose**: Extend API/web contracts and map shell so US4 can render summary + focus without reworking Header/Footer

**⚠️ CRITICAL**: Complete before US4 implementation tasks (tests may be written first and fail)

- [x] T034 Extend Pydantic models with `in_city_scope`, `summary` (`scope_mode`, averages, high/low, `insufficient_data`) in `apps/api/app/schemas/discover.py` per `specs/008-discover-mode/contracts/discover-api.md`
- [x] T035 [P] Extend Zod/TS types for `summary` + `in_city_scope` in `apps/web/src/types/discover.ts`
- [x] T036 Ensure `/discover/map` is a Server Component shell (Header/Footer) with client island `apps/web/src/components/discover/DiscoverMapClient.tsx` and thin `apps/web/src/app/discover/map/page.tsx` (fixes async Header-in-client bug)
- [x] T037 [P] Allow `http://127.0.0.1:3000` (and localhost) in `CORS_ORIGINS` in `apps/api/app/core/config.py`; align loopback host in `getApiBase()` in `apps/web/src/lib/api.ts`

**Checkpoint**: Summary contracts + map shell ready for US4

---

## Phase 8: User Story 4 — City summary under the map (Priority: P2)

**Goal**: Below-map city snapshot (average, highest/lowest, scored/total, min–max) using **city scope** (inner-bbox core v1), not full map-bbox overlay; high/low near top; hover/tap focuses tract (dim + gentle fit within lock)

**Independent Test**: Open a city whose map bbox includes fringe tracts; summary high/low/average match city-scoped tracts only; hover/tap highest/lowest → dim + gentle fit; high/low rows visible without scrolling the map away on a typical laptop viewport; &lt;2 scored city tracts → honest insufficient/empty summary (no fake high/low)

### Tests for User Story 4

- [x] T038 [P] [US4] API tests: `summary` aggregates city-scoped only; `in_city_scope` flags; `insufficient_data` when &lt;2 scored city tracts; high/low null vs populated in `apps/api/tests/test_discover.py` (or `apps/api/tests/test_discover_summary.py`)
- [x] T039 [P] [US4] Web test: summary layout order (headline → highest → lowest → rest) and empty/insufficient state in `apps/web/src/__tests__/discover-city-summary.test.tsx`
- [x] T040 [P] [US4] Web test: hover/tap handlers set/clear `focusedGeoid` (no report navigation) in `apps/web/src/__tests__/discover-summary-focus.test.tsx`

### Implementation for User Story 4

- [x] T041 [US4] Implement inner-bbox city-core membership (`CITY_CORE_SHRINK`) + tag `in_city_scope` on features in `apps/api/app/services/discover_service.py`
- [x] T042 [US4] Compute `summary` (average, min/max, counts, highest/lowest labels, `scope_mode=inner_bbox`, `insufficient_data`) over city-scoped tracts only in `apps/api/app/services/discover_service.py`
- [x] T043 [US4] Return extended response from thin handler in `apps/api/app/api/v1/endpoints/discover.py` (no summary logic in the route); log `scope_mode`
- [x] T044 [P] [US4] Build `DiscoverCitySummary` (headline, highest/lowest near top, friendly label + score, GEOID secondary, empty state) in `apps/web/src/components/discover/DiscoverCitySummary.tsx`
- [x] T045 [US4] Add `focusedGeoid` prop: dim non-focused fills + gentle `fitBounds` within `maxBounds`; clear restores city framing in `apps/web/src/components/discover/DiscoverMap.tsx`
- [x] T046 [US4] Wire fetch → parse `summary` → render `DiscoverCitySummary` under map; hover/tap focus + clear in `apps/web/src/components/discover/DiscoverMapClient.tsx`

**Checkpoint**: US4 — city snapshot + focus UX complete

---

## Phase 9: Polish & Cross-Cutting Concerns (city summary expansion)

**Purpose**: Validation and hardening for US4

- [x] T047 [P] Re-confirm Discover still never calls lookup/save/touch user APIs across `apps/web/src/components/discover/` and `apps/web/src/app/discover/`
- [x] T048 Run city-summary scenarios in `specs/008-discover-mode/quickstart.md` (summary section) and fix gaps
- [x] T049 [P] Run `cd apps/api && pytest tests/test_discover.py tests/test_discover_summary.py -q` (adjust paths to files that exist) and `cd apps/web && npm test -- --run src/__tests__/discover` — ensure green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: None — **done**
- **Foundational (Phase 2)**: Done — blocks US1–US3
- **US1–US3 + base Polish (Phases 3–6)**: **done**
- **US4 Foundation (Phase 7)**: Blocks US4 implementation (T041+)
- **US4 (Phase 8)**: After Phase 7; depends on existing map/choropleth (US2)
- **Expansion Polish (Phase 9)**: After US4

### User Story Dependencies

- **US1 (P1)**: Done
- **US2 (P1)**: Done
- **US3 (P2)**: Done
- **US4 (P2)**: After Phase 7; needs US2 FeatureCollection/map layers for focus/dim; summary is independently testable via API + summary component tests

### Within US4

- Tests T038–T040 written first (fail until service/UI land)
- T041 → T042 → T043 (service then thin route)
- T044 can parallel T041–T043 (different files)
- T045 after map exists; T046 after T044 + T045 + types/fetch path

### Parallel Opportunities

- T034 || T035 || T037 (Phase 7 files)
- T038 || T039 || T040 (US4 tests)
- T044 || T041 (summary UI vs service, different files)
- T047 || T049 (polish)

---

## Parallel Example: User Story 4

```bash
# Tests in parallel:
Task: "API summary/city-scope tests in apps/api/tests/test_discover.py"
Task: "Summary layout tests in apps/web/src/__tests__/discover-city-summary.test.tsx"
Task: "Focus handler tests in apps/web/src/__tests__/discover-summary-focus.test.tsx"

# After Phase 7 contracts:
Task: "DiscoverCitySummary.tsx"
Task: "discover_service.py city-core + summary"  # sequential with route wire
```

---

## Implementation Strategy

### Already delivered (MVP + choropleth)

Phases 1–6 complete: Discover search → locked map → relative choropleth → tract popup.

### Next increment (this task list)

1. Phase 7 — extend contracts + Server/client map shell + CORS/host alignment
2. Phase 8 US4 — city-scoped summary + focus UX
3. Phase 9 — quickstart + tests green
4. **STOP and VALIDATE** US4 independent test before `/speckit-close`

### Suggested MVP scope (historical)

**US1+US2** was the base demo. **US4** is the next shippable increment on this branch.

---

## Notes

- No new SQL migrations/tables for v1 city-core (`inner_bbox`); place polygons deferred
- Overall score only — no dimension toggles
- Do not persist Discover searches
- Keep city-scope + summary aggregates in `discover_service.py`; Next.js stays thin
- Commit rhythm: plan+tasks = Commit #2 at start of `/speckit-implement` (this file stays uncommitted until then)
