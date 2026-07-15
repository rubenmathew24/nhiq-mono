# Contract: Lookup + Score API (live path)

**Feature**: `002-data-ingestion-workers` | **Date**: 2026-07-14 (reopened)

Extends existing `/api/v1` routes. Web continues to use `apiFetch` → report page. No request-shape break for successful reports.

Active vintage: `SCORE_DATA_VINTAGE` (default `2026-Q3`).

**Dimension sources (phased):**

| Dimension | When phase done | Example `sources.*.source_id` |
|-----------|-----------------|-------------------------------|
| environment | MVP | `epa_aqs` \| `open_meteo` \| `default` |
| healthcare | MVP | `cms_hospital_general_info` |
| safety | R1 | `fbi_cde` \| `default` |
| education | R2 | `nces_urban` (may include `contributors[]`) |
| economic | R3 | `acs_bls_laus` (may include `contributors[]`) |

Placeholders (`source_id=placeholder`) allowed only for dimensions **not yet delivered**. Source-showcase UI still out of scope — API field only.

## `GET /api/v1/lookup?address=`

Unchanged happy path:

```json
{
  "address_id": "<uuid>",
  "status": "ready",
  "address_normalized": "string",
  "geoid": "11-digit-or-null"
}
```

| Status | When | Body / detail |
|--------|------|----------------|
| 200 | Geocode succeeds | `LookupResponse`; `geoid` set when tract resolution succeeds (prefer local `census_tracts` PIP when data present) |
| 422 | Address not found / not U.S. | Specific message: could not find that U.S. address… |

## `GET /api/v1/score/{address_id}`

### Success — live scores (200)

Response model remains `NeighborhoodReport` (existing Pydantic / web types):

| Field | Source |
|-------|--------|
| address / address_normalized / lat / lng / geoid | Lookup payload |
| overall_score + five dimensions | `neighborhood_scores` for `geoid` + active vintage |
| narrative | Deterministic template this feature (Claude later) |
| data_vintage / computed_at | From score row |

**Rule**: When a score row exists, dimension numeric values **MUST** match DB (same rounding as stored `NUMERIC(4,1)`). Undelivered dimensions may still be placeholder constants from the scoring worker — reports must not invent a second mock set. After R1/R2/R3, the corresponding dimensions MUST reflect non-placeholder DB values and non-placeholder `sources` entries.

### Missing lookup (404)

```json
{
  "detail": "Address lookup not found",
  "code": "LOOKUP_NOT_FOUND"
}
```

(Or keep plain `detail` if framework default; prefer adding `code` when touching handler.)

### Missing score (404) — not mock

When lookup exists but no `neighborhood_scores` row for geoid/vintage:

```json
{
  "detail": "Neighborhood score is not available for this address yet.",
  "code": "SCORE_UNAVAILABLE"
}
```

**MUST NOT** return `build_mock_report` for this case.

### Demo exception (optional)

`address_id == "demo-address-001"` MAY continue to serve a mock report for existing UI tests only. Fixture geocoded IDs never use this path.

## Cache

- Reads may use Redis cache-aside for report payloads.
- After scoring worker completes, invalidate score/report keys for affected geoids (or flush score namespace in local `ENVIRONMENT=development` if simpler).

## Web contract

- Report page already calls `/api/v1/score/{addressId}`.
- On `SCORE_UNAVAILABLE`, show clear empty/unavailable UI copy (specific message), not a fake 82 overall.
- No Next.js score computation.
