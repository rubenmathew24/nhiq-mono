# Quickstart: Report Sub-Scores (smoke + metro_10)

**Feature**: `004-report-subscores` | **Date**: 2026-07-16

Validate expanded report UI against **local Compose** with `INGEST_SCOPE=smoke` then `metro_10`. Not for national.

## Prerequisites

- Docker Compose stack healthy (`db`, `api`, `web`, Redis).
- `.env` with existing keys (`DATABASE_URL`, Mapbox, EPA, FBI, etc. as needed for base scores).
- Feature SQL applied (see [data-model.md](./data-model.md) migration notes).
- Base fixture data already loaded for the scope you test (tracts, hospitals, scores from 002 workers)—or run the full worker chain once.

## V1 — Schema + smoke detail

```bash
export INGEST_SCOPE=smoke
# apply 007_report_detail.sql (filename per implementation)
docker compose --profile workers run --rm worker-fema
docker compose --profile workers run --rm worker-cms-timely
docker compose --profile workers run --rm worker-scoring
```

**Expect**: Benton County tracts have `score_detail` with healthcare/schools/… sub_scores; FEMA row for Bentonville tract when ArcGIS returns data; timely rows for nearby hospitals when CMS returns measures.

## V2 — Smoke report UI

1. Open local web; search `609 SE Jamaica Dr, Bentonville, AR`.
2. Confirm score breakdown shows **sub-scores** under each category.
3. Confirm visible expand affordance; expand Healthcare → nearest ER name, miles, stars; wait stat if timely data present.
4. Expand Environment → AQI stats; hazard/flood if FEMA present; else clear unavailable (no fake flood).
5. Expand Safety / Schools / Economy → stats per [spec.md](./spec.md).

## V3 — metro_10

```bash
export INGEST_SCOPE=metro_10
docker compose --profile workers run --rm worker-fema
docker compose --profile workers run --rm worker-cms-timely
docker compose --profile workers run --rm worker-scoring
```

Spot-check at least **two** other fixture metros (e.g. Austin, Chicago) for expand content.

## V4 — Automated checks

```bash
# from repo conventions
pytest workers/tests/ -q -k "detail or fema or timely or sub_score"
pytest apps/api/tests/ -q -k "score"
cd apps/web && npm test -- --run report
```

## Contracts

- Report JSON: [contracts/score-api.md](./contracts/score-api.md)
- Workers: [contracts/worker-cli.md](./contracts/worker-cli.md)

## Failure signals

| Symptom | Likely cause |
|---------|----------------|
| Empty sub_scores | Scoring not re-run after migration |
| Fake flood/wait | Bug — must show unavailable |
| National worker run | Out of scope — use smoke/metro_10 only |
| `SCORE_UNAVAILABLE` | Tract not scored for active vintage |
