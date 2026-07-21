# Contract: GET /api/v1/coverage

Public, no auth.

## Response 200

```json
{
  "captured_at": "2026-07-17T12:00:00Z",
  "overall_pct": 42.5,
  "county_universe_count": 3143,
  "state_universe_count": 51,
  "sources": [
    {
      "job_name": "scoring",
      "grain": "county",
      "done_count": 400,
      "total_count": 3143,
      "pct_complete": 12.7
    }
  ],
  "states": [
    {
      "state_fips": "44",
      "state_abbr": "RI",
      "county_total": 5,
      "sources": [
        {
          "job_name": "census",
          "grain": "county",
          "done_count": 5,
          "total_count": 5,
          "pct_complete": 100.0
        }
      ]
    }
  ]
}
```

## Response 503 / empty universe

When `geo_counties` is empty for included FIPS: return a structured empty payload with `county_universe_count: 0`, `overall_pct: 0`, and/or HTTP 503 with message to bootstrap registry — prefer **200 with empty universe flags** so the page can render the empty state without treating it as an outage. Document `empty_universe: true` on the response.

## Jobs

Same order as national status: census, epa, cms, fbi, nces, urban, acs, bls, fema, cms_timely, scoring.

### Grain notes

| `job_name` | `grain` | Notes |
|------------|---------|--------|
| cms | `state` | 0/1 presence of hospitals in the state |
| cms_timely | `hospital` | Continuous hospital share (not state pass/fail) |
| epa | `county` | Denominator = AQS monitor counties; by-state `0/0` if none |
| urban | `county` | Denominator = NCES-complete counties |
| others (incl. scoring) | `county` | Full registry / scoring done-ness |

Parity: for every job, sum over `states[].sources[job].done_count` (and `total_count`) MUST equal national `sources[job]`.

## UI mapping (non-contract)

| Tab | Uses |
|-----|------|
| Overall | `overall_pct`, `sources[]` |
| By state | `states[]` + filter Overall (mean of state sources with `total_count > 0`) or one `job_name` from `sources[]` |

The API does not need an `overall` job entry; Overall is a UI filter over existing fields.
