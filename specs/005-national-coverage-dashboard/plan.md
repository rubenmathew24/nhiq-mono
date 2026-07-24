# Implementation Plan: National Coverage Dashboard

**Branch**: `005-national-coverage-dashboard` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-national-coverage-dashboard/spec.md`

## Summary

Add a public `/coverage` page and a public FastAPI read endpoint that report national data coverage using the same denominators as national ingest status (`003-national-ingest`), with Overall ↔ By state parity: `geo_counties` for ordinary county-grain jobs; EPA ÷ AQS monitor counties; Urban ÷ NCES counties; state grain for CMS; **hospital grain** (continuous share) for CMS Timely; scoring done at county grain with fbi_cde + non-empty `score_detail`. The web UI has two tabs — **Overall** (national per-source table) and **By state** (per-state table with a source filter that includes **Overall** plus each job; Overall mean skips sources with `total_count = 0`).

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js App Router (web)

**Primary Dependencies**: FastAPI, SQLAlchemy/asyncpg (existing API DB), Next.js `apiFetch`

**Storage**: PostgreSQL — read `geo_counties` + raw ingest / `neighborhood_scores` (no new tables required)

**Testing**: pytest under `apps/api/tests/`; optional light web typecheck

**Target Platform**: Existing API + web deploy

**Project Type**: Monorepo apps/api + apps/web

**Performance Goals**: Single coverage request completes in a few seconds for ~3k counties; acceptable for public informational page

**Constraints**: Thin client (no DB math in browser); no auth; do not break `/dashboard`; territories out of scope

**Scale/Scope**: 50+DC, 11 status jobs

## Constitution Check

- [x] **I. Locked Stack & Monorepo**: FastAPI + Next.js only
- [x] **II. Thin Client, Fat API**: Coverage computed in API service; web displays
- [x] **III. Precomputed Data Path**: Reads batch-loaded tables; no live gov APIs
- [x] **IV. API Contracts & Versioning**: New `/api/v1/coverage` public GET
- [x] **V. Security & Secrets**: Public read-only; no secrets on page
- [x] **VI. Test Alongside Features**: API unit/service tests for denominator semantics
- [x] **VII. Observability**: Standard API errors for empty registry / DB failure
- [x] **VIII. Clear User-Facing Errors**: Empty/error states on `/coverage`

## Project Structure

### Documentation (this feature)

```text
specs/005-national-coverage-dashboard/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/coverage-api.md
└── tasks.md
```

### Source Code

```text
apps/api/app/schemas/coverage.py
apps/api/app/services/coverage_service.py
apps/api/app/api/v1/endpoints/coverage.py
apps/api/app/api/v1/router.py
apps/api/tests/test_coverage*.py
apps/web/src/app/coverage/page.tsx
apps/web/src/types/api.ts (coverage types)
apps/web/src/components/layout/Header.tsx (optional nav link)
```

**Structure Decision**: Mirror existing score/lookup endpoint + service pattern.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
