# Contract: Score API (sub-scores + expand stats)

**Feature**: `004-report-subscores` | **Date**: 2026-07-16 (UX polish revision)

Extends `GET /api/v1/score/{address_id}` success body. Lookup route unchanged. Active vintage: `SCORE_DATA_VINTAGE` (default `2026-Q3`).

Geography expectation: reports with full detail are verified for **smoke** and **metro_10** prepared data. National coverage is out of scope for this feature.

## Additive types

```ts
interface SubScore {
  id: string;          // access | quality | timeliness | personal | property | ...
  label: string;       // User-facing plain English
  score: number;       // 0–100
  available?: boolean; // default true; false = limited data
}

interface Factor {
  name: string;        // Plain English label (e.g. "2nd nearest ER", "Assault")
  value: string;       // Plain English value (no raw source ids)
  impact: "positive" | "negative" | "neutral";
  tone_score?: number; // Optional 0–100; web uses ScoreBar tiers for value color
}

interface ScoreDimension {
  score: number;
  label: string;
  summary: string;
  sub_scores: SubScore[];
  factors: Factor[];
}
```

`sources` map may include:

| Dimension | New `source_id` values |
|-----------|-------------------------|
| environment | `fema_nri` (alongside `epa_aqs` / `open_meteo`) |
| healthcare | `cms_timely_effective_care` (alongside `cms_hospital_general_info`) |

`sources` may expose internal ids; **`factors` MUST NOT** echo those ids to end users.

## Success (200)

- Category `score` values MUST match DB `*_score` columns (same rounding).
- When `score_detail` is populated for a dimension:
  - `sub_scores` MUST match stored detail for that dimension (labels plain English).
  - `factors` MUST match stored `stats` (order preserved; nearest-first for facilities).
  - Healthcare ER rows after the first MUST use ordinal names (`2nd nearest ER`, `3rd nearest ER`).
  - ER wait factor SHOULD include `tone_score` aligned with timeliness sub-score (or equivalent) so UI can match ScoreBar coloring.
  - Environment AQI factor value MUST NOT include `open_meteo` / `epa_aqs` substrings.
  - Education factors MUST NOT include pupil–teacher ratio or locale codes.
  - Safety factor names MUST NOT be raw CDE codes (`HOM`, `ASS`, etc.).
- When `score_detail` is `{}` or missing a dimension (pre-migration rows):
  - API MUST NOT invent flood/wait facts.
  - MAY return empty `sub_scores` / minimal factors and a summary that data is limited — operator re-score is the fix for acceptance.

## Errors

Unchanged: `LOOKUP_NOT_FOUND`, `SCORE_UNAVAILABLE`. Never serve mock detail as live for real address IDs.

## Cache

After scoring upserts `score_detail`, invalidate report Redis keys for affected geoids (same pattern as today).

## Web

- Report breakdown renders each category as an **interactive box**; `sub_scores` always visible per category.
- `factors` shown only when category expanded.
- Affordance: full-box activate + accessible name (not text-only “View details”).
- When `tone_score` is present, color factor **values** with the same good/mid/poor classes as ScoreBar (`≥75` / `≥50` / else). When absent, fall back to `impact`.
