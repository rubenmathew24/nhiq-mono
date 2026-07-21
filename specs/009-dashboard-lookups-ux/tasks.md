# Tasks: Dashboard Lookups UX

**Input**: Design documents from `/specs/009-dashboard-lookups-ux/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Constitution VI — API tests in `apps/api/tests/`; web tests in `apps/web/src/__tests__/`.

**Organization**: Setup → Foundation → US1 (suggestions) → US2 (dedupe/score) → US3 (favorites/menu) → Post-test polish → Final polish.

**Note**: Core US1–US3 implementation landed earlier on this branch; checkboxes below reflect current repo state. Open tasks are the remaining gaps (tests + post-test clarify UX + Delete/`apiFetch` bug).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallel-safe (different files)
- **[Story]**: US1 / US2 / US3

---

## Phase 1: Setup

- [x] T001 Confirm feature docs present under `specs/009-dashboard-lookups-ux/` (plan, research, data-model, contracts, quickstart)
- [x] T002 [P] Document `NEXT_PUBLIC_MAPBOX_TOKEN` for Places autocomplete in `.env.example`

---

## Phase 2: Foundational (blocking)

- [x] T003 Add `is_favorite`, `last_activity_at` to `SavedLookup` in `apps/api/app/models/__init__.py` + `infra/sql/009_dashboard_lookups_ux.sql` / `infra/sql/init.sql`
- [x] T004 [P] Add `users.lookups_deduped_at` in `apps/api/app/models/__init__.py` + SQL
- [x] T005 Extend schemas in `apps/api/app/schemas/auth.py` with `last_activity_at`, `is_favorite`, `overall_score`
- [x] T006 [P] Mirror types in `apps/web/src/types/api.ts`
- [x] T007 Refactor `PostgresLookupStore` in `apps/api/app/services/lookup_store.py` for place reuse, upsert, merge, score enrich, favorite/delete/touch

**Checkpoint**: Schema + store foundation ready

---

## Phase 3: User Story 1 — Address suggestions (P1) 🎯 MVP

**Goal**: Lookahead suggestions; select or free-type to score; dashboard search full-width (post-test FR-013)

**Independent Test**: Type 3+ chars → suggestions; select → report; free-type still works; search width matches two columns

### Tests

- [x] T008 [P] [US1] Web test for suggestion select / submit in `apps/web/src/__tests__/address-search-suggest.test.tsx`

### Implementation

- [x] T009 [US1] Mapbox Places debounce + suggestion UI in `apps/web/src/components/search/AddressSearch.tsx`
- [x] T010 [P] [US1] Keyboard/a11y for suggestion list in `AddressSearch.tsx`
- [x] T011 [US1] Graceful Places failure (search still submittable) in `AddressSearch.tsx`
- [x] T012 [US1] Make dashboard search span full Favorites+Recent width in `apps/web/src/app/dashboard/page.tsx` (remove narrower `max-w-3xl` wrapper around `AddressSearch`)

**Checkpoint**: US1 suggestions + full-width search

---

## Phase 4: User Story 2 — Dedupe + leading score preview (P1)

**Goal**: One saved identity per place; leading color-scaled score (replaces pin); favorite indicator when favorited

**Independent Test**: Score twice → one identity; leading glyph is score not pin; favorited shows indicator + score

### Tests

- [x] T013 [P] [US2] API tests: reuse place, merge duplicates, list `overall_score` in `apps/api/tests/test_user_lookups.py`
- [x] T014 [P] [US2] Web test: leading score + favorite indicator rendering in `apps/web/src/__tests__/dashboard.test.tsx`

### Implementation

- [x] T015 [US2] `merge_duplicate_saved_lookups` + list enrichment in `apps/api/app/services/lookup_store.py` / `users.py`
- [x] T016 [US2] Replace map-pin leading glyph with prominent `scoreTextClass` score in `apps/web/src/components/dashboard/LookupList.tsx`
- [x] T017 [US2] Show distinct favorite indicator on favorited rows (keep leading score) in `LookupList.tsx`
- [x] T018 [P] [US2] Unavailable score leading preview (no fake number) in `LookupList.tsx`

**Checkpoint**: US2 leading score UX

---

## Phase 5: User Story 3 — Favorites, Recent, menu gates (P2)

**Goal**: Dual columns; ⋯ menu; confirm delete; unfavorite-before-delete; full menu dismiss; activity touch

**Independent Test**: Favorite dual-lists; delete blocked while favorited; cancel/outside closes entire menu; delete after unfavorite works once

### Tests

- [x] T019 [P] [US3] API tests: PATCH favorite, DELETE 204, DELETE 409 when favorited, POST touch in `apps/api/tests/test_user_lookups.py`
- [x] T020 [P] [US3] Web tests: unfavorite-before-delete, cancel closes menu, outside click closes menu in `apps/web/src/__tests__/dashboard-lookups.test.tsx`

### Implementation

- [x] T021 [US3] `PATCH` / `DELETE` / `POST .../touch` routes in `apps/api/app/api/v1/endpoints/users.py`
- [x] T022 [US3] Reject delete while favorited with **409** + clear detail in `apps/api/app/services/lookup_store.py` and `users.py` (per `contracts/dashboard-lookups-api.md`)
- [x] T023 [US3] Favorites + Recent two-column layout in `apps/web/src/components/dashboard/LookupList.tsx` / `dashboard/page.tsx`
- [x] T024 [US3] Block or disable Delete in UI while `is_favorite` with unfavorite-first guidance in `LookupList.tsx`
- [x] T025 [US3] Cancel on delete confirm closes **entire** overflow menu (not back to Favorite/Delete) in `LookupList.tsx`
- [x] T026 [US3] Click-outside + Escape dismiss open menu or confirm completely in `LookupList.tsx`
- [x] T027 [US3] Report open → touch via `apps/web/src/components/report/LookupActivityTouch.tsx` + report page
- [x] T028 [US3] Re-search bumps `last_activity_at` via lookup attach in `lookup_store.py`

**Checkpoint**: US3 menu + delete gate behavior

---

## Phase 6: Post-test bugfix (tasks-only)

- [x] T029 Fix `apiFetch` handling of empty/`204` responses so DELETE Remove succeeds on first click (no “string did not match the expected pattern”) in `apps/web/src/lib/api.ts`
- [x] T030 [P] Add/adjust unit coverage for `apiFetch` 204/empty body in `apps/web/src/__tests__/` (or existing api helper test file)

---

## Phase 7: Final polish

- [x] T031 [P] Empty Favorites / Recent states in `LookupList.tsx`
- [x] T032 Run API tests `apps/api/tests/test_user_lookups.py` and web dashboard tests; fix regressions
- [x] T033 Manual pass against `specs/009-dashboard-lookups-ux/quickstart.md`
- [x] T034 Rebuild/restart Docker web+api so local testing picks up UI changes (`docker compose up -d --build api web`)

---

## Dependencies

```text
Phase 1–2 (done) → US1 (T012 open) → US2 (T016–T017 open)
                 → US3 (T022, T024–T026 open)
T029–T030 can run with US3 delete work
T032–T034 after open implementation tasks
```

## Parallel examples

```bash
# UI polish in parallel:
T012, T016, T017, T024, T025, T026
# API gate + client bug:
T022, T029
# Tests in parallel once UI stable:
T008, T013, T014, T019, T020, T030
```

## Implementation strategy

1. **MVP remaining**: T012 full-width search + T016/T017 leading score/favorite mark (highest visible polish)
2. **Menu correctness**: T022/T024–T026 + T029 (delete gate + dismiss + first-click Remove)
3. **Tests + quickstart**: T008/T013–T014/T019–T020/T030–T033
4. **Ship**: T034 rebuild for verification

## MVP scope (original)

User Story 1 suggestions alone were MVP; remaining MVP for this iteration = **Phase 6 bugfix + leading score + menu dismiss/gate** so dashboard testing matches clarify.
