# Quickstart: Report Sub-Scores (smoke + metro_10)

**Feature**: `004-report-subscores` | **Date**: 2026-07-16 (UX polish round 3)

Validate expanded report UI against **local Compose** with `INGEST_SCOPE=smoke` then `metro_10`. Not for national.

## Prerequisites

- Docker Compose stack healthy (`db`, `api`, `web`, Redis).
- `.env` with existing keys (`DATABASE_URL`, Mapbox, EPA, FBI, Census, etc. as needed).
- Feature SQL applied (`infra/sql/007_report_detail.sql` or init on fresh volume).
- After round-3 code lands: **rebuild `web`** (Compose does not bind-mount `apps/web`) and **re-run scoring** so property sub-scores and school copy refresh.

## V1 — Schema + smoke detail

```bash
export INGEST_SCOPE=smoke
export INGEST_FORCE=1
# ACS population (B01003) if not already loaded for Safety rates
docker compose --profile workers run --rm worker-acs
docker compose --profile workers run --rm worker-scoring
# Ship UI changes to localhost:3000
docker compose build web && docker compose up -d web
```

**Expect**: Benton County tracts have `score_detail` with healthcare/schools/… sub_scores; personal Safety per resident; **property sub-score limited-data (not 0)** when CDE property benches are null; schools-by-level within **30 mi**; ER `★-` when unrated.

## V2 — Smoke report UI checklist

1. Open `http://localhost:3000`; search `609 SE Jamaica Dr, Bentonville, AR`.
2. Confirm each category is one box; **hover anywhere** highlights the whole box; **click** expands; **drag-select** on summary/labels copies text without toggling.
3. Click a **sub-score** (e.g. Access) → expand stats open; click the **summary** text → toggles; click title/bar → toggles.
4. Expand Safety → Crimes against property is **limited data / —**, not a scored **0**; violent crime line is % vs state **per resident**.
5. Expand Schools → nearest by level within **30 mi**; no ~457 mi Pre-K; no PTR / locale.
6. Expand Healthcare → ordinal ERs; missing stars show `★-`.

## V3 — metro_10

```bash
export INGEST_SCOPE=metro_10
export INGEST_FORCE=1
docker compose --profile workers run --rm worker-scoring
```

Spot-check at least two other fixture metros for property availability honesty and school cutoff.

## V4 — Automated checks

```bash
# workers (use project venv; prefer PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 if pytest hangs)
cd workers && PYTHONPATH=. .venv/bin/python -m pytest tests/test_score_detail.py tests/test_safety_formula.py -q

# API (in api container with pytest-asyncio if needed)
docker compose exec -T -u root api sh -c "pip install -q pytest pytest-asyncio && python -m pytest tests/test_score_subscores.py -q"

# Web Vitest needs Node 20+
docker run --rm -v "$PWD/apps/web:/app" -w /app node:20-alpine npm test -- --run src/__tests__/score-breakdown-expand.test.tsx
```

## Contracts

- Report JSON: [contracts/score-api.md](./contracts/score-api.md)
- Workers: [contracts/worker-cli.md](./contracts/worker-cli.md)

## Failure signals

| Symptom | Likely cause |
|---------|----------------|
| Property score shows **0** | Synthetic `state=local` + pop still in scoring — re-score after FR-021 fix |
| Property “limited data” forever after benches land | CDE ingest still null benches — separate backfill |
| Header-only expand / faint hover on :3000 | **Stale `web` image** — `docker compose build web && up -d web` |
| Pre-K hundreds of miles away | School 30 mi cutoff not applied / scoring not re-run |
| `0.03× the state` violent crime | Absolute-share formula / missing ACS pop |
| National worker run | Out of scope — use smoke/metro_10 only |
| `SCORE_UNAVAILABLE` | Tract not scored for active vintage |
