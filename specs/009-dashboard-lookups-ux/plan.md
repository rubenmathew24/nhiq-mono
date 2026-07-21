# Implementation Plan: Dashboard Lookups UX

**Branch**: `009-dashboard-lookups-ux` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-dashboard-lookups-ux/spec.md`

## Summary

Enhance the signed-in dashboard with Mapbox Places address lookahead (browser-allowed), overall score previews on saved rows (reuse `scoreTextClass` / report color bands), per-user dedupe of the same resolved place (reuse `address_lookups` by geoid + one-time merge of existing duplicates), Favorites/Recent dual listing with `is_favorite` + `last_activity_at`, and a three-dot menu for favorite/unfavorite and confirm-before-delete. Persistence and list enrichment stay in FastAPI; Next.js remains a thin client.

### Post-test UX refinements (clarify session)

- **Leading score**: Row leading visual is the color-scaled overall score (replaces map-pin). Favorited rows also show a distinct favorite indicator.
- **Search width**: Dashboard `AddressSearch` spans the full width of the two-column Favorites/Recent layout (`apps/web/src/app/dashboard/page.tsx` — remove narrower `max-w-3xl` wrapper).
- **Menu dismiss**: Cancel on delete confirmation closes the entire overflow menu; click-outside / Escape dismisses menu or confirm fully (`LookupList` row menu).
- **Unfavorite before delete**: UI disables/blocks Delete while `is_favorite`; API `DELETE /users/me/lookups/{id}` returns **409** (or clear 400) with a stable message if still favorited.
- **Known bug (tasks only, not a product FR)**: First click of confirm Remove can surface “The string did not match the expected pattern.” then succeed on retry — fix in `/speckit-tasks` / implement (likely `apiFetch` + `204` DELETE / body parsing). Do not encode as a user-facing requirement.

## Technical Context

**Language/Version**: TypeScript (Next.js 14 App Router), Python 3.12 (FastAPI)

**Primary Dependencies**: Next.js, Tailwind, Mapbox GL/Places (browser autocomplete only), FastAPI, SQLAlchemy async, Pydantic, PostgreSQL

**Storage**: PostgreSQL (`saved_lookups`, `address_lookups`, `neighborhood_scores`); Redis unchanged for lookup/report cache

**Testing**: pytest (`apps/api/tests/`), Vitest/RTL (`apps/web/src/__tests__/`)

**Target Platform**: Web (nh-iq.com) + Azure Container Apps API

**Project Type**: Monorepo web + API feature

**Performance Goals**: Suggestion dropdown feels interactive (<300ms perceived after debounce); dashboard list loads with score previews in one authenticated request when possible

**Constraints**: Constitution II — only Mapbox Places from browser; no client DB/scoring; clear user-facing errors (VIII)

**Scale/Scope**: Per-user saved lists (tens–hundreds of rows); one dashboard page + shared `AddressSearch`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodInsight Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Next.js / FastAPI / Postgres / Redis only; code under `apps/web`, `apps/api`
- [x] **II. Thin Client, Fat API**: Dedup, favorite, delete, score enrichment in API services; Mapbox Places autocomplete is the only browser external call
- [x] **III. Precomputed Data Path**: Score preview reads `neighborhood_scores` (no live government scoring)
- [x] **IV. API Contracts & Versioning**: Extend `/api/v1/users/me/lookups*` under existing v1; Pydantic schemas
- [x] **V. Security & Secrets**: `NEXT_PUBLIC_MAPBOX_TOKEN` (pk) for Places; Mapbox secret token stays server-side for geocode; auth required for mutate endpoints
- [x] **VI. Test Alongside Features**: API tests for dedupe/merge/favorite/delete/list shape; web tests for columns/menu/confirm
- [x] **VII. Observability & Graceful Degradation**: Suggestion provider failure → search still works; missing score → unavailable preview
- [x] **VIII. Clear User-Facing Errors**: Delete/favorite failures surface specific messages; geocode 422 copy unchanged

## Project Structure

### Documentation (this feature)

```text
specs/009-dashboard-lookups-ux/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── dashboard-lookups-api.md
└── tasks.md              # /speckit-tasks (not this command)
```

### Source Code (repository root)

```text
apps/web/src/
  components/search/AddressSearch.tsx      # + Places lookahead
  components/dashboard/                    # LookupList → Favorites/Recent, row menu
  lib/utils.ts                             # reuse scoreTextClass
  app/dashboard/page.tsx
  app/report/[addressId]/page.tsx          # touch activity on open
  types/api.ts
apps/api/app/
  models/__init__.py                       # saved_lookups columns
  services/lookup_store.py                 # dedupe, merge, activity, favorite
  api/v1/endpoints/users.py                # list + mutate routes
  schemas/auth.py                          # enriched SavedLookup
  tests/test_user_lookups.py
```

**Structure Decision**: Extend existing dashboard + lookup store; no new top-level apps.

## Complexity Tracking

> No constitution violations requiring justification.
