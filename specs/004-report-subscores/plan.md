# Implementation Plan: Report Sub-Scores & Category Detail

**Branch**: `004-report-subscores` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-report-subscores/spec.md`. User lock: **dev/local only** with **`smoke` + `metro_10`** geography (not national).

**Revision**: UX polish round 4 — category boxes stay click-to-expand but allow press-and-drag **text selection** without toggling (FR-004 / SC-014). Round 3 (property limited-data, 30 mi, full-box + web rebuild) already shipped.

## Summary

Local/dev report: five categories with sub-scores and in-place expand from an obvious interactive box.

**Already delivered (through round 3)**: `score_detail`; FEMA/Timely; per-resident Safety; property limited-data when benches missing; ER `★-`; school cutoff 30 mi; full-box `ScoreBreakdown` on rebuilt Compose web.

**Round-4 delta**:

1. **Text selection**: Remove `select-none` / `pointer-events-none` that block selecting copy. Toggle expand only on a true click (small pointer movement, no non-empty `window.getSelection()` after the gesture). Rebuild Compose `web` after UI change.
2. Vitest: click still expands; drag (moved pointer) does not toggle.

## Technical Context

**Language/Version**: TypeScript / Next.js 14 (report UI only for this delta)

**Primary Dependencies**: Existing `ScoreBreakdown.tsx`; Vitest

**Storage**: Unchanged

**Testing**: `apps/web/src/__tests__/score-breakdown-expand.test.tsx`; rebuild `web`

**Target Platform**: Local Docker Compose only

**Project Type**: Monorepo — `apps/web`

**Performance Goals**: N/A

**Constraints**: Keep whole-box activate + hover; do not break keyboard Enter/Space toggle

**Scale/Scope**: Round-4 UI micro-polish

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (NeighborhoodIQ Constitution v1.1.0)*

- [x] **I. Locked Stack & Monorepo**
- [x] **II. Thin Client, Fat API**: UI-only gesture handling
- [x] **III. Precomputed Data Path**: Unchanged
- [x] **IV. API Contracts & Versioning**: Unchanged
- [x] **V. Security & Secrets**: Unchanged
- [x] **VI. Test Alongside Features**
- [x] **VII. Observability & Graceful Degradation**: Unchanged
- [x] **VIII. Clear User-Facing Errors**: Unchanged

**Post-design re-check (round 4)**: Gates pass.

## Project Structure

### Documentation (this feature)

```text
specs/004-report-subscores/
├── plan.md
├── research.md          # §13 round 4
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (touch list)

```text
apps/web/src/components/report/ScoreBreakdown.tsx
apps/web/src/__tests__/score-breakdown-expand.test.tsx
```

## Complexity Tracking

> No constitution violations requiring justification.
