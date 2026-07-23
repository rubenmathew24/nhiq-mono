# Data Model: 008-discover-mode

Discover is a **read-only presentation** over existing spatial/score tables. No new durable entities for the POC.

## Existing entities (reused)

### Census tract (`census_tracts`)

| Field | Role for Discover |
| --- | --- |
| `geoid` | Tract identity in overlays + popups |
| `geometry` | Border polygon(s), WGS84; intersected with request bbox |
| `state_fips` / `county_fips` | Not required in API response for POC |

### Neighborhood score (`neighborhood_scores`)

| Field | Role for Discover |
| --- | --- |
| `geoid` | Join key to tract |
| `overall_score` | Choropleth + popup (nullable if row missing) |
| `data_vintage` | Filter to active `SCORE_DATA_VINTAGE` |
| Dimension scores | **Out of scope** for POC response |

## Request / view models (not persisted)

### Discover place selection (client → map route)

| Field | Rules |
| --- | --- |
| `place_name` | Non-empty display string from Places suggestion |
| `min_lng`, `min_lat`, `max_lng`, `max_lat` | Valid WGS84; `min_*` < `max_*`; within world bounds; span under configured max |

### Discover tracts query (API)

Same bbox fields as above. Optional `place_name` for echo/logging only.

### Discover tracts response (API → web)

| Field | Rules |
| --- | --- |
| `place_name` | Echo if provided |
| `bbox` | Echo of request bbox |
| `type` | `"FeatureCollection"` |
| `features[]` | Zero or more tract features |
| `features[].properties.geoid` | Required string |
| `features[].properties.overall_score` | `number` or `null` |
| `features[].geometry` | GeoJSON Polygon or MultiPolygon |
| `meta.scored_count` | Count where score non-null |
| `meta.unscored_count` | Count where score null |
| `meta.truncated` | `true` if feature cap applied |
| `meta.score_min` / `meta.score_max` | Optional; among non-null scores in this response |

## Validation rules

- Reject inverted or empty bbox (`400` + clear detail).
- Reject bbox exceeding max span (`400` with actionable message, e.g. choose a smaller place).
- Missing score row for a tract ⇒ `overall_score: null` (still include geometry when tract exists).
- No tracts intersecting bbox ⇒ empty `features`, counts zero (HTTP 200 — expected empty state).

## State transitions

None durable. UI-only states: searching → loading map → ready / partial / empty / error.

## Out of scope

- Persisting Discover searches
- City boundary tables
- Dimension-specific score overlays
- Mutations to scores or tracts
