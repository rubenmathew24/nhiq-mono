# Contract: Discover API

Base: `/api/v1` · Auth: **none** (public POC).

## `GET /discover/tracts`

Returns census tract geometries intersecting a WGS84 bounding box, joined to overall neighborhood scores for the active score vintage.

### Query parameters

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `min_lng` | number | yes | West edge |
| `min_lat` | number | yes | South edge |
| `max_lng` | number | yes | East edge |
| `max_lat` | number | yes | North edge |
| `place_name` | string | no | Echoed for UI/logging; max length ~200 |

### Success `200`

```json
{
  "place_name": "Boston, Massachusetts, United States",
  "bbox": {
    "min_lng": -71.2,
    "min_lat": 42.2,
    "max_lng": -70.9,
    "max_lat": 42.4
  },
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-71.1, 42.3], [-71.09, 42.3], [-71.09, 42.31], [-71.1, 42.31], [-71.1, 42.3]]]
      },
      "properties": {
        "geoid": "25025000100",
        "overall_score": 72.5
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "MultiPolygon",
        "coordinates": []
      },
      "properties": {
        "geoid": "25025000200",
        "overall_score": null
      }
    }
  ],
  "meta": {
    "scored_count": 1,
    "unscored_count": 1,
    "truncated": false,
    "score_min": 72.5,
    "score_max": 72.5,
    "data_vintage": "2026-Q3"
  }
}
```

### Behavior

- Spatial filter: tract `geometry` intersects envelope `(min_lng, min_lat, max_lng, max_lat)` SRID 4326.
- Score join: left join active `SCORE_DATA_VINTAGE` overall score (null if missing).
- Geometry may be simplified server-side for payload size.
- If feature cap exceeded: return first N features, `meta.truncated: true` (stable order by `geoid` recommended).
- Empty intersection: `features: []`, counts `0`, still `200`.
- **Must not** write `address_lookups`, `saved_lookups`, or any user history.

### Errors

| Status | When | Example `detail` |
| --- | --- | --- |
| `400` | Missing/non-numeric coords, inverted bbox, bbox too large | `"Choose a smaller area — this place bounding box is too large to map."` |
| `503` / `500` | Unexpected DB failure | Prefer unexpected-failure copy per constitution VIII |

Error shape: `{ "detail": "<human message>", "code": "<optional machine code>" }`  
Suggested codes: `INVALID_BBOX`, `BBOX_TOO_LARGE`.

## Web consumption notes

- Map page calls this once per place selection (and on retry).
- Relative colors computed client-side from non-null `overall_score` values.
- Partial coverage UI when `scored_count > 0 && unscored_count > 0`.
- Empty coverage UI when `scored_count === 0` (including zero features).

## Non-goals (this contract)

- Dimension scores
- Report / address_id linkage
- Auth or rate-limit tiers specific to Discover (platform defaults may still apply)
