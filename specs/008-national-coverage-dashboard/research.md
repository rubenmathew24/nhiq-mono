# Research: National Coverage Dashboard

## R1 — Denominators

**Decision**: Reuse national ingest status semantics from 007 / `workers/ingest/status.py`: county jobs vs `|geo_counties|`; CMS/Timely vs included state count; scoring = counties fully scored with fbi_cde + non-empty `score_detail` vs `|geo_counties|`.

**Rationale**: Spec requires correct expected values; duplicating inventing math would drift from ops Workbook.

**Alternatives**: Read only `ingest_status_snapshot` (no by-state); rejected — snapshot is national aggregates only.

## R2 — By-state derivation

**Decision**: Live SQL grouped by `state_fips` (or state abbr for CMS) against `geo_counties` universe.

**Rationale**: Inventory builds by-state ephemerally; product needs a stable API read model.

## R3 — Overall metric

**Decision**: Overall = mean of per-source national percentages (equal weight across the 11 jobs), plus expose each source for clarity.

**Rationale**: Single headline number without privileging one source; visitors still see by-source detail.

## R4 — Route `/coverage`

**Decision**: Public page at `/coverage`; leave authenticated `/dashboard` unchanged.

**Rationale**: Avoid breaking saved-lookups UX.

## R5 — Auth

**Decision**: No auth on page or `GET /api/v1/coverage`.

**Rationale**: Explicit product requirement.
