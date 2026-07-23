# Quickstart: 008-discover-mode

## Prerequisites

- Local stack: API + web + Postgres/PostGIS with `census_tracts` + `neighborhood_scores` (aligned `SCORE_DATA_VINTAGE`)
- `NEXT_PUBLIC_MAPBOX_TOKEN` set for web (Places + Mapbox GL)
- Prefer opening web as either `http://127.0.0.1:3000` or `http://localhost:3000` (API CORS allows both; browser API host is aligned automatically)
- Feature code for Discover pages + `/api/v1/discover/tracts` (with `summary`)

## Validate header + search entry

1. Open the site home (signed out).
2. Header shows **Discover**; click it → `/discover`.
3. Type 3+ characters of a U.S. city (e.g. `Bentonville`).
4. Expect place suggestions; select one → `/discover/map` with place + bbox params.

## Validate locked choropleth map

1. Basemap constrained to place bbox.
2. Tract borders; relative overall colors; legend says relative-to-view.
3. Hover/click scored tract → popup score; no `/report/...` navigation.
4. Mixed coverage → gray + soft banner; empty scores → empty message.

## Validate city snapshot summary

1. Below the map, see average / coverage headline, then **highest** and **lowest** near the top, then counts / min–max.
2. High/low labels show friendly text + score (GEOID secondary), not GEOID-only.
3. Hover (desktop) or tap (touch) highest/lowest → map dims others and gently fits to that tract within lock; clear hover/tap restores city framing.
4. On ~laptop viewport, interacting with high/low does not require scrolling the map away.
5. Confirm summary highs/lows are city-scoped: if map shows fringe tracts outside the core, they must not set city high/low when only in the outer bbox.

## Validate empty / error paths

1. No scored tracts → empty map message; summary insufficient/empty (no fake high/low).
2. Inverted/huge bbox API → `400` actionable detail.
3. Mapbox token missing → search/map degrade without crash.

## Automated checks

```bash
cd apps/api && pytest tests/test_discover.py -q
cd apps/web && npm test -- --run src/__tests__/discover
```

See [contracts/discover-api.md](./contracts/discover-api.md), [data-model.md](./data-model.md), [research.md](./research.md).
