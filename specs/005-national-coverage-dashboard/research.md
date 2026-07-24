# Research: National Coverage Dashboard

## R1 — Denominators

**Decision**: Reuse national ingest status / coverage display semantics from `003-national-ingest` / `workers/ingest/status.py` and `coverage_service.py`:

- Ordinary county jobs vs `|geo_counties|`
- EPA vs `|epa_aqs_monitor_counties|` (per state: monitor counties only, or `0/0` if none — never fall back to all counties)
- Urban vs NCES-complete counties
- CMS vs included state count (0/1)
- CMS Timely vs **hospital share** (hospitals with timely ÷ hospitals) — not the ingest ≥80% state pass/fail checkpoint
- Scoring = counties fully scored with fbi_cde + non-empty `score_detail` vs `|geo_counties|`

**Overall ↔ By state**: for every job, sum of per-state done/total MUST equal national done/total.

**Rationale**: Spec requires correct expected values; Timely state pass/fail misread as “addresses without scores”; EPA all-county fallback in by-state broke parity with national monitor denominator.

**Alternatives**: Read only `ingest_status_snapshot` (no by-state); rejected — snapshot is national aggregates only. Timely as state 0/1; rejected after product review.

## R2 — By-state derivation

**Decision**: Live SQL grouped by `state_fips` (or state abbr for CMS) against `geo_counties` universe.

**Rationale**: Inventory builds by-state ephemerally; product needs a stable API read model.

## R3 — Overall metric

**Decision**: Overall = mean of per-source national percentages (equal weight across the 11 jobs), plus expose each source for clarity on the Overall tab.

**Rationale**: Single headline number without privileging one source; visitors still see by-source detail.

## R3b — Two-tab UX (Overall + By state)

**Decision**: Exactly two tabs. Overall = national source table. By state = former “by source” geographic drill-down (source dropdown + per-state rows), with an additional **Overall** filter option (mean-of-sources % per state, **excluding sources with `total_count = 0`**). No third “by source” tab and no separate mean/scoring-only state summary table.

**Rationale**: By-source national detail already lives on Overall; by-source already broke down by state — collapsing to two tabs avoids duplicate navigation.

**Alternatives**: Three tabs (overall / by source / by state) — rejected after product review.

## R4 — Route `/coverage`

**Decision**: Public page at `/coverage`; leave authenticated `/dashboard` unchanged.

**Rationale**: Avoid breaking saved-lookups UX.

## R5 — Auth

**Decision**: No auth on page or `GET /api/v1/coverage`.

**Rationale**: Explicit product requirement.
