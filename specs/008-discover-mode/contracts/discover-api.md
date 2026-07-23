# Contract: Discover API

Base: `/api/v1` · Auth: **none** (public POC).

## `GET /discover/tracts`

Returns census tract geometries intersecting a WGS84 bounding box, joined to overall neighborhood scores for the active score vintage, plus a **city-scoped snapshot summary**.

### Query parameters

| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| `min_lng` | number | yes | West edge (map lock) |
| `min_lat` | number | yes | South edge |
| `max_lng` | number | yes | East edge |
| `max_lat` | number | yes | North edge |
| `place_name` | string | no | Echoed for UI/logging/labels; max ~200 |

### Success `200`

```json
{
  "place_name": "Bentonville, Arkansas, United States",
  "bbox": {
    "min_lng": -94.37,
    "min_lat": 36.22,
    "max_lng": -94.13,
    "max_lat": 36.47
  },
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-94.2, 36.3], [-94.19, 36.3], [-94.19, 36.31], [-94.2, 36.31], [-94.2, 36.3]]]
      },
      "properties": {
        "geoid": "05007020101",
        "overall_score": 72.5,
        "in_city_scope": true
      }
    }
  ],
  "meta": {
    "scored_count": 1,
    "unscored_count": 0,
    "truncated": false,
    "score_min": 72.5,
    "score_max": 72.5,
    "data_vintage": "2026-Q3"
  },
  "summary": {
    "scope_mode": "inner_bbox",
    "average_overall": 72.5,
    "score_min": 72.5,
    "score_max": 72.5,
    "scored_count": 1,
    "total_count": 1,
    "highest": null,
    "lowest": null,
    "insufficient_data": true
  }
}
```

Example high/low when ≥ 2 city-scoped scored tracts:

```json
"highest": {
  "geoid": "05007020102",
  "overall_score": 91.0,
  "label": "Bentonville · Tract 020102"
},
"lowest": {
  "geoid": "05007020101",
  "overall_score": 54.2,
  "label": "Bentonville · Tract 020101"
},
"insufficient_data": false
```

### Behavior

- **Map features**: tracts whose geometry intersects envelope `(min_lng, min_lat, max_lng, max_lat)` SRID 4326.
- **City scope (`in_city_scope`)**: v1 default — tract centroid inside shrunk inner bbox (configurable shrink factor). Future — centroid in place polygon when ingested/`scope_mode=place_polygon`.
- **Score join**: left join active `SCORE_DATA_VINTAGE` overall score.
- **Summary**: aggregates over city-scoped tracts only (not full FeatureCollection). `highest`/`lowest` null + `insufficient_data: true` when fewer than two scored city-scoped tracts.
- Geometry may be simplified; feature cap → `meta.truncated: true`.
- **Must not** write `address_lookups`, `saved_lookups`, or any user history.

### Errors

| Status | When | Example `detail` |
| --- | --- | --- |
| `400` | Missing/non-numeric coords, inverted bbox, bbox too large | `"Choose a smaller area — this place bounding box is too large to map."` |
| `503` / `500` | Unexpected DB failure | Unexpected-failure copy per constitution VIII |

Error shape: `{ "detail": "<human message>", "code": "<optional machine code>" }`  
Suggested codes: `INVALID_BBOX`, `BBOX_TOO_LARGE`.

## Web consumption notes

- Map page: one `apiFetch` per place; render choropleth from `features`; render `DiscoverCitySummary` from `summary`.
- Relative colors: client min/max among **rendered scored** features (map view), unchanged.
- Focus UX: client-only; pass `focusedGeoid` into map for dim + `fitBounds`.
- Layout: highest/lowest rows immediately under average/coverage headline.

## Non-goals (this contract)

- Dimension scores
- Report / address_id linkage
- Auth or Discover-specific rate-limit tiers
- Required place-polygon ingest for this increment
