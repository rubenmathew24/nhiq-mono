# Research: 008-discover-mode

## 1. Place search → bbox lock

**Decision**: Browser Mapbox Places Geocoding autocomplete with `country=US` and place-oriented `types` (at minimum `place`; allow `locality` if needed for coverage). On selection, read the feature’s `bbox` (`[minLng, minLat, maxLng, maxLat]`). If `bbox` is missing, derive a padded box from the feature center (`center`) using a fixed small delta (documented constant). Navigate to the Discover map route with place label + bbox in the query string (or equivalent serializable state). Pass the same bbox into the tracts API. Map lock uses **city framing** after `fitBounds(place bbox, padding)` — see §15 for how `minZoom` / `maxBounds` are derived so scroll, nav −, and un-focus stay aligned.

**Rationale**: Matches clarify (search-result bbox); constitution allows Mapbox Places from the browser; no new city-boundary ingest for POC.

**Alternatives considered**:
- Census place polygons — accurate city limits but new ingest + matching logic
- County-only lock — simpler SQL but wrong UX for many cities
- Server-side geocode only — extra hop; Places already client-allowed
- Constructor `maxBounds = place bbox ± 2%` only — rejected after runtime (blocked scroll short of padded city framing; see §15)

## 2. Tracts + scores API shape

**Decision**: Public `GET /api/v1/discover/tracts?min_lng=&min_lat=&max_lng=&max_lat=&place_name=` (place_name optional, for logging/echo). Response: FeatureCollection-like payload with each feature’s `geoid`, `overall_score` (`number | null`), and Polygon/MultiPolygon geometry (WGS84). Server joins `census_tracts` ⟷ `neighborhood_scores` for `SCORE_DATA_VINTAGE`. Spatial filter: tracts whose geometry intersects `ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)`.

**Rationale**: Fat API / precomputed path; one round-trip for the choropleth; public POC (no auth).

**Alternatives considered**:
- Tile server / MVT — better at national scale; overkill for city POC
- Client fetches all county tracts — too heavy and wrong ownership of spatial query
- Per-tract score N+1 — chatty

## 3. Geometry size & limits

**Decision**: Simplify geometries in SQL (`ST_SimplifyPreserveTopology` or `ST_Simplify` on `geometry` before `ST_AsGeoJSON`) with a small tolerance suitable for city zoom. Enforce a maximum bbox span (e.g. reject or soft-fail if width/height exceeds a configured threshold such as ~2–3 degrees) with a clear user-facing message. Cap returned features (e.g. 2,500) with a response flag `truncated: true` + message if hit — UI shows partial/empty messaging appropriately.

**Rationale**: Dense metros can produce large GeoJSON; POC must stay interactive (SC-005).

**Alternatives considered**:
- No simplify — risk multi‑MB payloads
- Vector tiles — deferred
- Hard-fail on any large city — too brittle for demos

## 4. Relative coloring

**Decision**: Compute relative colors **on the client** from scored tracts in the API response: map `overall_score` to a continuous color ramp using min/max among non-null scores in the current FeatureCollection (if only one scored tract, use a mid-ramp color). Exclude null scores from min/max; render them gray. Legend explains “relative to neighborhoods shown.” Optionally echo `score_min` / `score_max` from API for convenience, but client remains source of truth for the visible set.

**Rationale**: Clarify chose relative-within-map; client already owns Mapbox fill paint expressions.

**Alternatives considered**:
- Absolute 0–100 bands — rejected in clarify
- Server-only color hex — couples presentation to API

## 5. Map UX (popup, banners, empty)

**Decision**: Extend Mapbox GL usage (existing `mapbox-gl` + `MapView` patterns) with a GeoJSON source + fill/line layers, `queryRenderedFeatures` on click/hover for popup (`overall_score` or “Score unavailable”). Soft banner when `scored_count > 0 && unscored_count > 0`. Empty state when `scored_count === 0`: basemap + lock + clear copy, no fill layer (or empty source).

**Rationale**: Matches FR-008–FR-010; reuses token/`NEXT_PUBLIC_MAPBOX_TOKEN` already required for report maps.

**Alternatives considered**:
- Leaflet — would violate locked stack preference / duplicate map stack
- Report deep-link from popup — deferred (clarify)

## 6. Routing & header

**Decision**: Add `Discover` to `navLinks`. Routes: `/discover` (search entry) and `/discover/map` (map + overlays; query params for `place`, `min_lng`, `min_lat`, `max_lng`, `max_lat`). Public pages (not middleware-protected).

**Rationale**: Spec requires header tab + webpage; shareable map URLs aid demos.

**Alternatives considered**:
- Single page with client-only state — harder to refresh/share
- Dashboard-only entry — conflicts with public POC

## 7. Persistence & auth

**Decision**: Discover endpoints and pages never call lookup/save/touch user APIs. Signed-in session may exist but is ignored for Discover side effects.

**Rationale**: Explicit clarify for POC.

**Alternatives considered**:
- Save place searches to `saved_lookups` — rejected

## 8. Caching

**Decision**: POC default = no Redis. Optional later: cache-aside key `discover:tracts:{vintage}:{rounded_bbox}` with short TTL; invalidate not required on score writes for POC (TTL expiry sufficient).

**Rationale**: Correctness over premature cache; Constitution III allows Redis as cache-aside when added.

**Alternatives considered**:
- Mandatory Redis for v1 — unnecessary for POC traffic

## 9. Testing strategy

**Decision**: API tests with a small fixture of tracts/scores + bbox queries (hit, miss, partial scores, invalid bbox). Web tests for relative-color helper, empty/partial banner copy branches, and place→map query param construction (mock Mapbox/network). Manual quickstart for full Mapbox GL interaction.

**Rationale**: Constitution VI; GL hard to fully e2e in Vitest without heavy mocks.

**Alternatives considered**:
- Playwright e2e in this POC — deferred unless CI already has it ready

## 10. City scope for snapshot stats (vs map bbox)

**Decision**: Map overlay continues to use bbox intersection. Snapshot stats use a **city scope** subset:
1. **Preferred (when available later)**: tracts whose centroids lie inside a place polygon (Census incorporated place / Mapbox Boundaries) — deferred as optional ingest.
2. **v1 default**: **tighter core** — tracts whose centroids fall inside an axis-aligned box shrunk toward the center of the geocoder bbox (e.g. keep central 70% of width/height, configurable `CITY_CORE_SHRINK=0.7`). Tag each feature with `in_city_scope: bool`. Compute summary only from city-scoped tracts (`overall_score` required for average/high/low; totals include unscored in-scope).

**Rationale**: Clarify B (polygon when available, else tighter core); avoids suburb pollution from raw bbox without blocking on new national place ingest.

**Alternatives considered**:
- Stats = all rendered tracts — rejected (clarify)
- Mandatory Census place ingest now — accurate but expands scope beyond this increment
- County FIPS filter — wrong for multi-county cities / partial counties

## 11. Snapshot payload shape

**Decision**: Extend `GET /api/v1/discover/tracts` with a `summary` object:

- `scope_mode`: `"inner_bbox"` | `"place_polygon"`
- `average_overall`, `score_min`, `score_max` (city-scoped scored only)
- `scored_count`, `total_count` (city-scoped)
- `highest` / `lowest`: `{ geoid, overall_score, label }` or null if fewer than 2 scored city tracts
- `insufficient_data`: true when highs/lows cannot be formed

Map `meta` remains overlay-oriented (full FeatureCollection). Client does not recompute city averages from all features.

**Rationale**: One round-trip; server owns scope filter; matches FR-014–017.

**Alternatives considered**:
- Separate `/discover/summary` — extra request; easy to drift from map
- Client-only filter — risks inconsistent shrink logic

## 12. Friendly labels for high/low

**Decision**: `label` = short place context from `place_name` + `Tract {geoid suffix}`. Optional later: Mapbox reverse geocode of tract centroid — not required for acceptance.

**Rationale**: Clarify B without new tables.

**Alternatives considered**:
- GEOID-only — rejected
- Always reverse-geocode every tract — latency/cost for POC

## 13. Summary ↔ map focus UX

**Decision**: `DiscoverCitySummary` places average/coverage headline, then **highest**, then **lowest**, then remaining stats (FR-019). **Click/tap** sets `focusedGeoid` (toggle: click active again → `null`); map dims non-focused fills and `fitBounds` to that feature within lock. Clear restores city framing via `fitCityAndLockMinZoom` (see §15). Call `map.stop()` before each focus/`fitBounds` so in-flight cameras do not race. **Hover MUST NOT** set or clear focus (FR-016 amend 2026-07-23). Active row shows selected styling + short “Focused · click to clear” hint (FR-020).

**Pointer clear (superseded):** List-level `mouseLeave` clear and hover-to-focus are **removed** — they caused races and no longer match product (click-only).

**What went wrong (historical hover path)**: Each row had `onMouseLeave → null`. The gap between Highest and Lowest sits outside both buttons, so moving between them fired leave→`null` (start ~600ms city restore `fitBounds`) then enter→other geoid (tract `fitBounds`). Competing Mapbox camera animations left the map on the wrong tract or mid-city framing intermittently.

**How it was fixed (interim)**: List-level clear only; then product amended to **click-only** toggle/switch — no hover handlers.

**Rationale**: Click is intentional; avoids hover races; same UX on desktop and touch; selected hint teaches clear affordance.

**Alternatives considered**:
- Highlight only without fit — rejected
- Always pin both high and low — rejected
- Per-row `mouseLeave` clear — rejected after runtime race
- List-level leave clear — superseded by click-only
- Debounce null ~50ms — obsolete under click-only
- Keyboard Enter/Space map-focus requirement — OUT OF SCOPE for POC (clarify B)

## 14. Local CORS / host alignment

**Decision**: Allow `http://127.0.0.1:3000` and `http://localhost:3000` in API `CORS_ORIGINS`. Browser `getApiBase()` rewrites loopback hostnames to match the page host.

**Rationale**: Runtime: `127.0.0.1` page → `localhost:8000` caused `Load failed` despite API 200.

**Alternatives considered**:
- Document “only use localhost” — brittle for Next bound to `127.0.0.1`

## 15. City framing zoom lock (scroll / nav − / un-focus)

**Decision** (`DiscoverMap.tsx` → `fitCityAndLockMinZoom`):

1. `fitBounds(place bbox, { padding: 40 })` for city framing (initial load + summary un-focus).
2. `setMinZoom(map.getZoom())` so neither scroll nor Mapbox nav **−** can zoom out past that framing.
3. `setMaxBounds` from the **actual framed `getBounds()`** (small ~2% expand for float/pan slack), not from the raw place bbox alone.
4. `map.scrollZoom.enable({ around: "center" })` so wheel zoom is not biased to the cursor.

**What went wrong**: Three different zoom-out floors:

| Control | Symptom (example Bentonville) |
| --- | --- |
| Un-focus city `fitBounds` | ~zoom **10.28** (desired) |
| Scroll wheel max-out | Stuck ~**11.62** (too zoomed in) |
| Nav **−** | Could go to hard `minZoom: 8` (too zoomed out), then later matched un-focus after minZoom lock but scroll still stuck |

Root cause: place-only `maxBounds` (±2% on the search bbox) is **tighter** than the visible area after `fitBounds` + 40px padding. Scroll zoom respects that tight `maxBounds` and refuses to open to the padded framing; programmatic `fitBounds` / nav could still reach `minZoom`. Hard-coded `minZoom: 8` also let the **−** button zoom past city framing before the lock existed.

**How it was fixed**: Derive lock from the framed view after fit (`minZoom` + matching `maxBounds`); remove hard `minZoom: 8`; scroll around center. Post-fix: wheel, nav −, and un-focus share ~the same floor (~10.28 in the Bentonville run).

**Rationale**: Product wants one “city home” framing for lock, un-focus, and zoom-out.

**Alternatives considered**:
- Keep place `maxBounds` + only `setMinZoom` — insufficient (scroll still blocked ~11.62)
- `around: "center"` alone — insufficient without expanding `maxBounds`
- Document “use − not scroll” — rejected

## 16. Map page Server shell (related hardening)

**Decision**: `/discover/map` is a Server Component (`Header` / `Footer`) with client island `DiscoverMapClient` for map + summary.

**Rationale**: Async Header using `headers()` / auth must not live under `"use client"` (runtime: async Client Component / request-scope errors).

**Alternatives considered**: Make Header sync-only on Discover — wider layout change; island is local.

## 17. Water-only tract exclusion (Lake Michigan / coastal)

**Decision**: Discover MUST NOT color or summarize tracts with `census_tracts.aland = 0`. Prefer filtering in `discover_service` (omit from FeatureCollection **or** set a non-display flag and skip in relative min/max + summary). Depends on 002/003 schema + census upsert of TIGER `ALAND`/`AWATER`.

**Rationale**: Cook County includes water-only TIGER tracts over Lake Michigan. They can still hold scores and paint as “lowest” neighborhoods though nobody lives there. Census already marks land area; we were dropping it on ingest.

**Alternatives considered**:
- Building footprints — rejected (heavy, unnecessary)
- Tract codes 9900–9998 only — heuristic, incomplete as sole rule
- ACS `total_population = 0` — deferred (needs ACS join; secondary signal)
- Delete water tracts from warehouse — rejected (breaks national coverage / FEMA joins; 003 keeps rows)
