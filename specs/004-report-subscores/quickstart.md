# Quickstart: Report Sub-Scores (smoke + metro_10)

**Feature**: `004-report-subscores` | **Date**: 2026-07-16 (UX polish)

Validate expanded report UI against **local Compose** with `INGEST_SCOPE=smoke` then `metro_10`. Not for national.

## Prerequisites

- Docker Compose stack healthy (`db`, `api`, `web`, Redis).
- `.env` with existing keys (`DATABASE_URL`, Mapbox, EPA, FBI, etc. as needed for base scores).
- Feature SQL applied (`infra/sql/007_report_detail.sql` or init on fresh volume).
- Base fixture data loaded for the scope you test — or run the full worker chain once.
- After UX polish code lands: **re-run scoring** so `score_detail` labels/tone refresh.

## V1 — Schema + smoke detail

```bash
export INGEST_SCOPE=smoke
export INGEST_FORCE=1
# apply 007_report_detail.sql if score_detail column missing
docker compose --profile workers run --rm worker-fema
docker compose --profile workers run --rm worker-cms-timely
docker compose --profile workers run --rm worker-scoring
```

**Expect**: Benton County tracts have `score_detail` with healthcare/schools/… sub_scores; plain-English factor names; ER wait `tone_score` mid/poor when wait ≈/above national; schools-by-level rows; AQI without `open_meteo` text.

## V2 — Smoke report UI (UX polish checklist)

1. Open local web (`http://localhost:3000`); search `609 SE Jamaica Dr, Bentonville, AR`.
2. Confirm each category is an **obvious clickable box** (not subtle “View details” only).
3. Expand Healthcare → Nearest / 2nd / 3rd nearest ER labels; ER wait color not green when wait ≥ national.
4. Expand Safety → full words (Assault, etc.); condensed geography/agencies.
5. Expand Environment → AQI readable; no `open_meteo` in the panel.
6. Expand Schools → nearest by level; no PTR / locale.
7. Expand Economy → income, unemployment, employment-rate style stat.

## V3 — metro_10

```bash
export INGEST_SCOPE=metro_10
export INGEST_FORCE=1
docker compose --profile workers run --rm worker-fema
docker compose --profile workers run --rm worker-cms-timely
docker compose --profile workers run --rm worker-scoring
```

Spot-check at least **two** other fixture metros (e.g. Austin, Chicago) for expand content and plain-English labels.

## V4 — Automated checks

```bash
# from repo conventions
pytest workers/tests/ -q -k "detail or fema or timely or sub_score or tone"
pytest apps/api/tests/ -q -k "score"
cd apps/web && npm test -- --run report
```

## Contracts

- Report JSON: [contracts/score-api.md](./contracts/score-api.md)
- Workers: [contracts/worker-cli.md](./contracts/worker-cli.md)

## Failure signals

| Symptom | Likely cause |
|---------|----------------|
| Empty sub_scores | Scoring not re-run after migration / polish |
| Green ER wait at/above national | Timeliness tone/formula not updated |
| “Also nearby” / `ASS` / `open_meteo` / Locale code | Old `score_detail` — force re-score |
| Fake flood/wait | Bug — must show unavailable |
| National worker run | Out of scope — use smoke/metro_10 only |
| `SCORE_UNAVAILABLE` | Tract not scored for active vintage |
