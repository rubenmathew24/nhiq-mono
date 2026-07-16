# Implementation Plan: Report Sub-Scores & Category Detail

**Branch**: `004-report-subscores` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-report-subscores/spec.md`. User lock: **dev/local only** with **`smoke` + `metro_10`** geography (not national).

**Revision**: UX polish round 3 — fix property sub-score false `0`, raise school cutoff to **30 mi**, ship full-box expand to the running Compose web image.

## Summary

Local/dev report: five categories with sub-scores and in-place expand from an obvious interactive box.

**Already delivered (through round 2)**: `score_detail`; FEMA/Timely; per-resident Safety personal score + copy; ER `★-`; school cutoff constant; source-level full-box `ScoreBreakdown`.

**Round-3 delta** (user-reported regressions / incompleteness):

1. **Safety property**: Bentonville shows Crimes against property = **0** with `available: true`. Root cause: property CDE rows lack `state_benchmark_12mo`; `_property_safety` set `state = local` then divided by different county vs state populations → ratio ≈ `state_pop/county_pop` → score clamped to **0**. Fix: no property benches → **`available: false`** (limited data), never that synthetic path.
2. **Schools**: Change `SCHOOL_MAX_EXPAND_MILES` from **25 → 30**; update no-schools-found copy and tests.
3. **Web full-box**: Repo already uses one `<button>` for the whole category, but Compose `web` has **no bind-mount** and serves a **stale runner image**, so localhost still only feels like header-click. Fix: confirm control covers title + **sub-scores** + **summary** with whole-box hover; **rebuild/restart `web`**; harden Vitest; optional Compose bind-mount only if we choose it as the operator path (prefer rebuild + checklist).

## Technical Context

**Language/Version**: Python 3.12 (workers + FastAPI); TypeScript / Next.js 14 (report UI)

**Primary Dependencies**: Existing worker/scoring stack; Next.js + Tailwind; Compose PostGIS + Redis

**Storage**: No new tables. Re-score rewrites `score_detail` / sub_scores after property fix

**Testing**: Unit test for property missing-bench → unavailable (not 0); school 30 mi cutoff tests; Vitest click on Access / summary; manual Bentonville after `docker compose build web` + scoring

**Target Platform**: Local Docker Compose only

**Project Type**: Monorepo — `workers/`, `apps/api`, `apps/web`

**Performance Goals**: Smoke re-score only (minutes)

**Constraints**: `INGEST_SCOPE` smoke|metro_10; Fair Housing–neutral; thin client; no inventing property intensity without benches

**Scale/Scope**: Round-3 bugfix polish; smoke verify Bentonville

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodIQ Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**
- [x] **II. Thin Client, Fat API**: Property availability decided in scoring/detail; web only renders
- [x] **III. Precomputed Data Path**: Re-score writes corrected sub_scores; no browser CDE calls
- [x] **IV. API Contracts & Versioning**: Additive availability semantics only
- [x] **V. Security & Secrets**: Unchanged
- [x] **VI. Test Alongside Features**
- [x] **VII. Observability & Graceful Degradation**: Missing benches → limited-data (not fake 0)
- [x] **VIII. Clear User-Facing Errors**

**Post-design re-check (round 3)**: Gates pass. Synthetic `state = local` under per-resident pops violated VII; corrected design matches FR-021.

## Project Structure

### Documentation (this feature)

```text
specs/004-report-subscores/
├── plan.md              # this file
├── research.md          # §12 round 3
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md             # /speckit-tasks
```

### Source Code (touch list)

```text
workers/scoring/detail.py                 # _property_safety: require benches
workers/ingest/fixtures/constants.py      # SCHOOL_MAX_EXPAND_MILES = 30
workers/scoring/detail.py                 # 30 mi copy / access filter (uses constant)
apps/web/.../ScoreBreakdown.tsx           # verify full-box; tighten if needed
docker-compose.yml                        # only if we add web bind-mount for local UX
workers/tests/test_score_detail.py
apps/web/src/__tests__/score-breakdown-expand.test.tsx
```

## Complexity Tracking

> No constitution violations requiring justification.
