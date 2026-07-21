# Tasks: Dashboard Lookups UX

**Input**: Design documents from `/specs/009-dashboard-lookups-ux/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Constitution VI — API tests in `apps/api/tests/`; web tests in `apps/web/src/__tests__/`.

**Organization**: By user story (US1 suggestions → US2 dedupe/score → US3 favorites/menu).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallel-safe (different files)
- **[Story]**: US1 / US2 / US3

## Phase 1: Setup

- [ ] T001 Confirm feature docs present under `specs/009-dashboard-lookups-ux/` (plan, research, data-model, contracts, quickstart)
- [ ] T002 [P] Document `NEXT_PUBLIC_MAPBOX_TOKEN` requirement for Places autocomplete in `apps/web` env usage / `.env.example` if missing

---

## Phase 2: Foundational (blocking)

**⚠️ Complete before user stories**

- [ ] T003 Add `is_favorite`, `last_activity_at` to `SavedLookup` in `apps/api/app/models/__init__.py` and SQL migration / `init` delta under `apps/api` or `infra` as used by the repo
- [ ] T004 [P] Add optional `users.lookups_deduped_at` (or equivalent merge flag) in `apps/api/app/models/__init__.py`
- [ ] T005 Extend `SavedLookup` / `LookupListResponse` schemas in `apps/api/app/schemas/auth.py` with `last_activity_at`, `is_favorite`, `overall_score`
- [ ] T006 [P] Mirror types in `apps/web/src/types/api.ts`
- [ ] T007 Refactor `PostgresLookupStore` in `apps/api/app/services/lookup_store.py` to reuse `address_lookups` by geoid/normalized address and upsert saved rows with activity bumps

**Checkpoint**: Schema + store foundation ready

---

## Phase 3: User Story 1 — Address suggestions (P1) 🎯 MVP

**Goal**: Lookahead suggestions while typing; select or free-type to score

**Independent Test**: Dashboard search shows suggestions; select → score works; token failure still allows free-type

### Tests

- [ ] T008 [P] [US1] Web test: suggestion select fills input / submit path in `apps/web/src/__tests__/address-search-suggest.test.tsx`

### Implementation

- [ ] T009 [US1] Add Mapbox Places suggestion fetch + debounce UI to `apps/web/src/components/search/AddressSearch.tsx` (min 3 chars, US addresses)
- [ ] T010 [P] [US1] Keyboard/a11y for suggestion list (arrow keys, Escape, aria) in `AddressSearch.tsx`
- [ ] T011 [US1] Graceful empty/error state when Places fails (search still submittable)

**Checkpoint**: US1 demonstrable on dashboard (and shared landing search if same component)

---

## Phase 4: User Story 2 — Dedupe + score preview (P1)

**Goal**: One saved identity per place; overall score preview with report color scaling; merge legacy duplicates

**Independent Test**: Score same address twice → one identity; score color matches report; seeded duplicates collapse on list

### Tests

- [ ] T012 [P] [US2] API tests: reuse address_lookup, no duplicate saved rows, merge duplicates in `apps/api/tests/test_user_lookups.py`
- [ ] T013 [P] [US2] API test: list includes `overall_score` null vs number in `apps/api/tests/test_user_lookups.py`

### Implementation

- [ ] T014 [US2] Implement `merge_duplicate_saved_lookups` + gate via `lookups_deduped_at` in `apps/api/app/services/lookup_store.py`
- [ ] T015 [US2] Enrich `GET /users/me/lookups` with scores from `neighborhood_scores` in `apps/api/app/api/v1/endpoints/users.py` / service helper
- [ ] T016 [US2] Update `LookupList` / dashboard rows to show overall score using `scoreTextClass` in `apps/web/src/components/dashboard/` and `apps/web/src/lib/utils.ts`
- [ ] T017 [P] [US2] Unavailable score preview UI (no fake number)

**Checkpoint**: US2 list is de-duplicated with score chips

---

## Phase 5: User Story 3 — Favorites, Recent, menu (P2)

**Goal**: Dual columns; ⋯ menu favorite/unfavorite; confirm delete; activity on open/search

**Independent Test**: Favorite appears in both columns; delete confirm; open report bumps Recent

### Tests

- [ ] T018 [P] [US3] API tests for PATCH favorite, DELETE, POST touch in `apps/api/tests/test_user_lookups.py`
- [ ] T019 [P] [US3] Web tests for Favorites/Recent split + confirm delete in `apps/web/src/__tests__/dashboard-lookups.test.tsx`

### Implementation

- [ ] T020 [US3] Add `PATCH /users/me/lookups/{address_id}`, `DELETE ...`, `POST .../touch` in `apps/api/app/api/v1/endpoints/users.py` (thin) + store methods
- [ ] T021 [US3] Dashboard two-column layout (Favorites + Recent) in `apps/web/src/app/dashboard/page.tsx` + components under `apps/web/src/components/dashboard/`
- [ ] T022 [US3] Row overflow menu (favorite / unfavorite / delete) with confirm dialog
- [ ] T023 [US3] Call touch on report open from `apps/web/src/app/report/[addressId]/page.tsx` (authenticated)
- [ ] T024 [US3] Ensure re-search path bumps `last_activity_at` via lookup attach (T007)

**Checkpoint**: Full dashboard UX per spec

---

## Phase 6: Polish

- [ ] T025 [P] Empty states for Favorites and Recent in dashboard components
- [ ] T026 Run API + web tests; fix regressions
- [ ] T027 Manual pass against `specs/009-dashboard-lookups-ux/quickstart.md`

---

## Dependencies

```text
Phase 1 → Phase 2 → US1 (Phase 3) ∥ US2 (Phase 4 after T007)
                └→ US3 (Phase 5) after US2 list enrichment preferred
Polish after US1–US3
```

- US1 can ship with existing list UI
- US2 needs T003–T007
- US3 needs US2 list fields + new mutate routes

## Parallel examples

```bash
# After foundation:
T008, T009  # web suggest
T012, T014  # api dedupe
# After routes:
T018, T021, T022
```

## Implementation strategy

1. Foundation schema + store reuse/dedupe
2. US1 autocomplete (quick user-visible win)
3. US2 merge + score preview
4. US3 columns/menu/touch
5. Polish + quickstart validation
