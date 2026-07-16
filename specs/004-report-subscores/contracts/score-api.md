# Contract: Score API (sub-scores + expand stats)

**Feature**: `004-report-subscores` | **Date**: 2026-07-16

Extends `GET /api/v1/score/{address_id}` success body. Lookup route unchanged. Active vintage: `SCORE_DATA_VINTAGE` (default `2026-Q3`).

Geography expectation: reports with full detail are verified for **smoke** and **metro_10** prepared data. National coverage is out of scope for this feature.

## Additive types

```ts
interface SubScore {
  id: string;          // access | quality | timeliness | personal | property | ...
  label: string;       // User-facing
  score: number;       // 0–100
  available?: boolean; // default true; false = limited data
}

interface ScoreDimension {
  score: number;
  label: string;
  summary: string;
  sub_scores: SubScore[];  // NEW — may be [] if score_detail missing
  factors: Factor[];       // Expand stats (name, value, impact)
}
```

`Factor` unchanged: `{ name, value, impact: "positive"|"negative"|"neutral" }`.

`sources` map may include:

| Dimension | New `source_id` values |
|-----------|-------------------------|
| environment | `fema_nri` (alongside `epa_aqs` / `open_meteo`) |
| healthcare | `cms_timely_effective_care` (alongside `cms_hospital_general_info`) |

## Success (200)

- Category `score` values MUST match DB `*_score` columns (same rounding).
- When `score_detail` is populated for a dimension:
  - `sub_scores` MUST match stored detail for that dimension.
  - `factors` MUST match stored `stats` (order preserved; nearest-first for facilities).
- When `score_detail` is `{}` or missing a dimension (pre-migration rows):
  - API MUST NOT invent flood/wait facts.
  - MAY return empty `sub_scores` / minimal factors and a summary that data is limited — operator re-score is the fix for acceptance.

## Errors

Unchanged: `LOOKUP_NOT_FOUND`, `SCORE_UNAVAILABLE`. Never serve mock detail as live for real address IDs.

## Cache

After scoring upserts `score_detail`, invalidate report Redis keys for affected geoids (same pattern as today).

## Web

- Report breakdown renders `sub_scores` always visible per category.
- `factors` shown only when category expanded.
- Affordance required before expand (button/chevron + accessible name).
