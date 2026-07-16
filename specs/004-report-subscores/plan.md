# Implementation Plan: Report Sub-Scores & Category Detail

**Branch**: `004-report-subscores` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-report-subscores/spec.md`. User lock: **dev/local only** with **`smoke` + `metro_10`** geography (not national).

**Revision**: UX polish round 2 — per-resident safety comparison, ER `★-`, 25 mi school cutoff, full-box click + stronger hover. Prior polish (ordinals, plain English, tone_score) already shipped.

## Summary

Local/dev report: five categories with sub-scores and in-place expand from an obvious interactive box.

**Already delivered**: `score_detail`; FEMA/Timely workers; API `sub_scores`/`tone_score`; plain-English expand; category boxes (header-only click).

**Round-2 delta**:

1. **Safety**: Population-normalized local/state intensity; user copy = vs state average **per resident** (not absolute share). ACS B01003 for county/state pop.
2. **Healthcare**: Missing ER stars → `★-`.
3. **Schools**: `SCHOOL_MAX_EXPAND_MILES = 25`; beyond → no schools found for that level.
4. **Web**: Entire category box is the toggle; stronger hover highlight.
5. Tests + smoke re-score (ACS population + scoring).

## Technical Context

**Language/Version**: Python 3.12 (workers + FastAPI); TypeScript / Next.js 14 (report UI)

**Primary Dependencies**: Existing worker stack; FastAPI + Pydantic; Next.js + Tailwind; Compose PostGIS 16 + Redis; Census ACS for B01003

**Storage**: Existing tables + ACS column/payload for `total_population` (tract and/or state geo_level). No new hazard/timely tables. `score_detail` JSON rewrite on re-score

**Testing**: `workers/tests/` safety rate formula + school cutoff + ER star placeholder; `apps/api/tests/`; `apps/web` Vitest full-box click + hover class; manual Bentonville checklist

**Target Platform**: Local Docker Compose only

**Project Type**: Monorepo — `workers/`, `apps/api`, `apps/web`

**Performance Goals**: Single precomputed report read; smoke re-score after ACS pop + scoring minutes

**Constraints**: `INGEST_SCOPE` smoke|metro_10; Fair Housing–neutral safety copy; thin client; no school zoning

**Scale/Scope**: Round-2 polish; smoke then metro_10 verification

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodIQ Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**
- [x] **II. Thin Client, Fat API**: Rate math + copy in scoring/detail; web renders only
- [x] **III. Precomputed Data Path**: ACS pop via workers → score_detail; no browser Census calls
- [x] **IV. API Contracts & Versioning**: Additive factor text/tone only
- [x] **V. Security & Secrets**: Existing `CENSUS_API_KEY` if ACS extended
- [x] **VI. Test Alongside Features**
- [x] **VII. Observability & Graceful Degradation**: Missing pop → unavailable comparison (not absolute-share fallback)
- [x] **VIII. Clear User-Facing Errors**

**Post-design re-check (round 2)**: Gates pass. Population normalization keeps request path free of government calls.

## Project Structure

### Documentation (this feature)

```text
specs/004-report-subscores/
├── plan.md
├── research.md          # §10 + §11
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md             # /speckit-tasks
```

### Source Code (touch list)

```text
workers/ingest/acs/              # B01003 total_population
workers/scoring/safety.py        # per-resident ratio
workers/scoring/detail.py        # copy, ★-, school cutoff
workers/scoring/compute.py       # pass county/state pop; filter schools
workers/ingest/fixtures/constants.py  # SCHOOL_MAX_EXPAND_MILES
apps/web/.../ScoreBreakdown.tsx  # full-box + hover
workers/tests/, apps/api/tests/, apps/web/src/__tests__/
```

## Complexity Tracking

> No constitution violations requiring justification.
