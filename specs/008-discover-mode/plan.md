# Implementation Plan: Discover Mode (City Score Map)

**Branch**: `008-discover-mode` | **Date**: 2026-07-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-discover-mode/spec.md`

**Note**: Updated after city-summary clarify expansion (US4). Base map POC already implemented on this branch.

## Summary

Public **Discover** map (place autocomplete → locked Mapbox choropleth of census tracts by relative overall score) plus a **city snapshot summary** under the map: average, highest/lowest tracts, scored/total counts, min–max — scoped to the **searched city** (place polygon when available, else tighter core), not the full map-bbox overlay. Summary high/low rows sit near the top; hover/tap focuses that tract (dim others + gentle fit within lock). No auth, no saved searches, overall score only.

## Technical Context

**Language/Version**: TypeScript (Next.js App Router) + Python 3.12 (FastAPI)

**Primary Dependencies**: Next.js, Tailwind, Mapbox GL JS, Mapbox Places (browser `pk`), FastAPI, PostGIS/SQLAlchemy, Pydantic, Vitest, pytest; optional Mapbox Geocoding (`sk`) server-side for place context / labels

**Storage**: PostgreSQL 16 + PostGIS — `census_tracts` + `neighborhood_scores`. No new durable tables required for v1 city-scope (inner-bbox core). Optional later: Census place polygons table if product wants true boundaries.

**Testing**: `apps/api/tests/test_discover*.py` (bbox, city-scope summary, focus payload); `apps/web/src/__tests__/discover*.test.*` (summary layout, focus handlers, colors)

**Target Platform**: Web (desktop primary; touch tap-to-focus required)

**Project Type**: Monorepo web + API (`apps/web`, `apps/api`)

**Performance Goals**: City map + summary in ~1–2s for typical demo cities; gentle fit without unlock; no multi-second freezes

**Constraints**: Thin client / fat API; browser Mapbox Places (+ GL); public endpoints; city snapshot ≠ map bbox membership; clear empty/insufficient-data summary states; CORS must allow both `localhost` and `127.0.0.1` web origins for local browser fetches

**Scale/Scope**: Extend existing Discover POC with summary + focus UX; no dimension toggles; no report deep-links; no mandatory national place-polygon ingest for this increment (fallback core is acceptable)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodInsight Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**: Next.js + FastAPI + PostGIS + Mapbox only
- [x] **II. Thin Client, Fat API**: City-scope filter + summary aggregates in FastAPI `services/`; web renders + map focus only; Places autocomplete from browser
- [x] **III. Precomputed Data Path**: Uses stored scores/geometries; no inline government scoring; optional reverse-geocode for labels is presentation-only
- [x] **IV. API Contracts & Versioning**: Extend `/api/v1/discover/tracts` (or sibling) with versioned Pydantic + zod
- [x] **V. Security & Secrets**: Parameterized SQL; `MAPBOX_TOKEN` server-only if reverse-geocode used; public `pk` on web
- [x] **VI. Test Alongside Features**: API + web tests for summary + focus
- [x] **VII. Observability & Graceful Degradation**: Log scope mode (`inner_bbox` vs `place_polygon`); missing polygon → core fallback, not 500
- [x] **VIII. Clear User-Facing Errors**: Insufficient city scores → honest summary empty state

## Project Structure

### Documentation (this feature)

```text
specs/008-discover-mode/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/discover-api.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/web/src/
├── app/discover/                      # Server shells + client islands
├── components/discover/
│   ├── DiscoverMapClient.tsx
│   ├── DiscoverMap.tsx                # focus/dim + fitBounds
│   ├── DiscoverCitySummary.tsx        # snapshot UI (high/low near top)
│   └── ...
├── lib/discoverColors.ts
└── types/discover.ts
apps/api/app/
├── services/discover_service.py       # city_scope + summary aggregates
├── schemas/discover.py
├── api/v1/endpoints/discover.py
└── tests/test_discover*.py
```

**Structure Decision**: Extend existing Discover service/response; keep Header/Footer on Server pages; map+summary in client island.

## Complexity Tracking

> No constitution violations requiring justification.
