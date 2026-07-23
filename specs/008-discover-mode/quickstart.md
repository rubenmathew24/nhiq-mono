# Quickstart: 008-discover-mode

## Prerequisites

- Local stack: API + web + Postgres/PostGIS with `census_tracts` + `neighborhood_scores` for at least one metro (aligned `SCORE_DATA_VINTAGE`)
- `NEXT_PUBLIC_MAPBOX_TOKEN` set for web (Places + Mapbox GL)
- Feature branch code for Discover pages + `/api/v1/discover/tracts`

## Validate header + search entry

1. Open the site home (signed out).
2. Header shows **Discover**; click it → `/discover`.
3. Type 3+ characters of a U.S. city (e.g. `Boston`).
4. Expect place suggestions (not street-address-only). Select one → navigate to `/discover/map` with place label + bbox params.

## Validate locked choropleth map

1. On the map page, confirm basemap is constrained (cannot pan/zoom far outside the place bbox).
2. Tract borders appear; colors differ by **relative** overall score among scored tracts; legend states relative-to-view.
3. Hover/click a scored tract → popup with overall score; no navigation to `/report/...`.
4. If mixed coverage: gray unscored tracts + soft partial-coverage banner.
5. Signed in vs signed out: same map behavior; dashboard Favorites/Recent unchanged after Discover use.

## Validate empty / error paths

1. Pick or craft a bbox with no scored tracts (or mock empty API) → locked basemap + clear “no scored neighborhoods” message.
2. Clear/block Mapbox token → search degrades gracefully (no crash); map shows existing “Map unavailable” style guidance if GL cannot start.
3. Call API with inverted or huge bbox → `400` with actionable `detail` (see [contracts/discover-api.md](./contracts/discover-api.md)).

## Automated checks

```bash
# API
cd apps/api && pytest tests/test_discover.py -q

# Web
cd apps/web && npm test -- --run src/__tests__/
```

See [data-model.md](./data-model.md) and [research.md](./research.md).
