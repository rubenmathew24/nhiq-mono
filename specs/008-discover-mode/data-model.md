# Data Model: 008-discover-mode

Discover is a **read-only presentation** over existing spatial/score tables. No new durable entities required for the city-summary increment (inner-bbox city core).

## Existing entities (reused)

### Census tract (`census_tracts`)

| Field | Role for Discover |
| --- | --- |
| `geoid` | Tract identity in overlays, popups, summary high/low |
| `geometry` | Border polygon(s), WGS84; map filter = intersects bbox; city scope = centroid in core/polygon |
| `state_fips` / `county_fips` | Not required in API response for POC |

### Neighborhood score (`neighborhood_scores`)

| Field | Role for Discover |
| --- | --- |
| `geoid` | Join key to tract |
| `overall_score` | Choropleth, popup, snapshot aggregates |
| `data_vintage` | Filter to active `SCORE_DATA_VINTAGE` |
| Dimension scores | **Out of scope** for POC response |

## Request / view models (not persisted)

### Discover place selection (client → map route)

| Field | Rules |
| --- | --- |
| `place_name` | Non-empty display string from Places suggestion |
| `min_lng`, `min_lat`, `max_lng`, `max_lat` | Valid WGS84; `min_*` < `max_*`; span under configured max |

### Discover tracts response (API → web)

| Field | Rules |
| --- | --- |
| `place_name` | Echo if provided |
| `bbox` | Echo of request bbox |
| `type` | `"FeatureCollection"` |
| `features[]` | Tracts intersecting map bbox |
| `features[].properties.geoid` | Required |
| `features[].properties.overall_score` | `number` or `null` |
| `features[].properties.in_city_scope` | `bool` — membership for snapshot |
| `features[].geometry` | GeoJSON Polygon or MultiPolygon |
| `meta.*` | Overlay counts / truncate / vintage (bbox feature set) |
| `summary` | City snapshot object or null/insufficient marker |

### City snapshot (`summary`)

| Field | Rules |
| --- | --- |
| `scope_mode` | `"inner_bbox"` or `"place_polygon"` |
| `average_overall` | Mean of city-scoped scored tracts; null if none |
| `score_min` / `score_max` | Among city-scoped scored; null if none |
| `scored_count` / `total_count` | City-scoped |
| `highest` / `lowest` | `{ geoid, overall_score, label }` or null if &lt; 2 scored city tracts |
| `insufficient_data` | `true` when high/low pair cannot be formed |

## Validation rules

- Reject inverted/empty/too-large bbox (`400`).
- Missing score ⇒ `overall_score: null`; still include geometry when present.
- Empty bbox intersection ⇒ empty features, HTTP 200.
- Summary highs/lows only when ≥ 2 city-scoped scored tracts.

## UI state (not persisted)

`focusedGeoid: string | null` — summary hover/tap focus; drives map dim + gentle fit.

## Out of scope

- Persisting Discover searches
- Required Census place-polygon table for this increment
- Dimension overlays / report deep-links
- Mutations to scores or tracts
