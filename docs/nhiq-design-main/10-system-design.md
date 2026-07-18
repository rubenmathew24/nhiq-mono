# 10 — System Design

> Authoritative technical design document for NeighborhoodInsight. Covers architecture decisions, data flows, service interactions, scaling strategy, failure modes, and security model. Read this before making any structural changes to the system.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Service Responsibilities](#3-service-responsibilities)
4. [Data Flow: Address Lookup](#4-data-flow-address-lookup)
5. [Data Flow: Score Computation](#5-data-flow-score-computation)
6. [Data Flow: AI Narrative Generation](#6-data-flow-ai-narrative-generation)
7. [Data Flow: Data Ingestion](#7-data-flow-data-ingestion)
8. [Caching Strategy](#8-caching-strategy)
9. [Authentication & Authorization](#9-authentication--authorization)
10. [Freemium Enforcement](#10-freemium-enforcement)
11. [API Design](#11-api-design)
12. [Database Design Decisions](#12-database-design-decisions)
13. [Scoring Model Design](#13-scoring-model-design)
14. [Scaling Strategy](#14-scaling-strategy)
15. [Failure Modes & Resilience](#15-failure-modes--resilience)
16. [Security Model](#16-security-model)
17. [Observability](#17-observability)
18. [Build Sequence](#18-build-sequence)
19. [Future Architecture Considerations](#19-future-architecture-considerations)

---

## 1. System Overview

NeighborhoodInsight aggregates public government data across six federal sources, runs a geospatial scoring pipeline, and surfaces results through an AI-generated narrative layer. The system has four distinct subsystems:

```
┌─────────────────────────────────────────────────────────┐
│  SUBSYSTEM 1: User-facing product                       │
│  Next.js web app → FastAPI → PostgreSQL/Redis           │
├─────────────────────────────────────────────────────────┤
│  SUBSYSTEM 2: Data ingestion                            │
│  Scheduled workers → Government APIs → PostgreSQL       │
├─────────────────────────────────────────────────────────┤
│  SUBSYSTEM 3: Scoring pipeline                          │
│  Scoring worker → Raw tables → neighborhood_scores      │
├─────────────────────────────────────────────────────────┤
│  SUBSYSTEM 4: AI narrative layer                        │
│  FastAPI → Claude API → Redis narrative cache           │
└─────────────────────────────────────────────────────────┘
```

The critical design principle: **user requests never trigger raw data fetches from government APIs**. All government data is pre-ingested. User requests read from PostgreSQL (pre-scored) and Redis (cached).

---

## 2. Architecture Diagram

```
═══════════════════════════════════════════════════════════════════════
                            CLIENTS
═══════════════════════════════════════════════════════════════════════

  Browser / Mobile Web          API Consumers (B2B)
       │                              │
       │ HTTPS                        │ HTTPS + API Key
       ▼                              ▼
═══════════════════════════════════════════════════════════════════════
                        AZURE FRONT DOOR + WAF
              (CDN, TLS termination, DDoS protection, routing)
═══════════════════════════════════════════════════════════════════════
       │                              │
       │ /* (web routes)              │ /api/v1/* (API routes)
       ▼                              ▼
┌──────────────────┐       ┌──────────────────────────────────────┐
│  NEXT.JS         │       │  FASTAPI                             │
│  Container App   │       │  Container App                       │
│                  │       │                                      │
│  App Router      │       │  /api/v1/lookup    → geocoding svc  │
│  Server Comps    │ ──────│  /api/v1/score     → score svc      │
│  Auth.js         │       │  /api/v1/compare   → compare svc    │
│  Mapbox GL       │       │  /api/v1/narrative → Claude svc     │
│  Recharts        │       │  /api/v1/auth      → user svc       │
│                  │       │  /api/v1/users     → user svc       │
└──────────────────┘       └────────────┬─────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
          ┌──────────────────┐ ┌────────────────┐ ┌──────────────────┐
          │  POSTGRESQL 16   │ │  REDIS 7       │ │  AZURE BLOB      │
          │  + PostGIS 3.4   │ │                │ │  STORAGE         │
          │                  │ │  Score cache   │ │                  │
          │  census_tracts   │ │  Narrative     │ │  PDF reports     │
          │  neighborhood_   │ │  cache         │ │  (Buyer Pro)     │
          │  scores          │ │  Session store │ │                  │
          │  hospitals       │ │  Rate limiting │ └──────────────────┘
          │  epa_aqi_*       │ │  counters      │
          │  crime_stats     │ └────────────────┘
          │  fema_risk       │
          │  schools         │
          │  zillow_*        │
          │  users           │
          │  address_lookups │
          └──────────────────┘
                    ▲
                    │ Write (INSERT / UPSERT)
                    │
═══════════════════════════════════════════════════════════════════════
                     DATA INGESTION LAYER
           (Azure Container Apps Jobs — scheduled, not user-triggered)
═══════════════════════════════════════════════════════════════════════

  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ worker   │ │ worker   │ │ worker   │ │ worker   │ │ worker   │
  │ epa      │ │ census   │ │ cms      │ │ fbi      │ │ fema     │
  │ (daily)  │ │(monthly) │ │(monthly) │ │(monthly) │ │(monthly) │
  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
       │             │            │             │            │
       ▼             ▼            ▼             ▼            ▼
  EPA AQS API   Census TIGER  CMS Provider  FBI CDE API  FEMA NRI
                 Shapefiles    Data Catalog             CSV Download

                              ┌──────────────┐
                              │ worker       │
                              │ scoring      │
                              │ (after any   │
                              │  ingestion)  │
                              └──────┬───────┘
                                     │ Reads raw tables,
                                     │ writes neighborhood_scores
                                     ▼
                              PostgreSQL

═══════════════════════════════════════════════════════════════════════
                     EXTERNAL AI LAYER
═══════════════════════════════════════════════════════════════════════

  FastAPI narrative service ──────────────────► Claude API
                                                (claude-sonnet-4-20250514)
                              ◄────────────────
                              narrative text (cached in Redis 6h)

═══════════════════════════════════════════════════════════════════════
                     AZURE INFRASTRUCTURE
═══════════════════════════════════════════════════════════════════════

  Azure Container Registry    ← Docker images pushed by GitHub Actions
  Azure Key Vault             ← Runtime secrets (DB, Redis, API keys)
  Azure Monitor + App Insights← Logs, metrics, traces
  GitHub Actions              ← CI/CD pipeline
```

---

## 3. Service Responsibilities

### Next.js Frontend

**What it owns:**
- All user-facing UI (pages, components, maps)
- Session management via Auth.js (JWT stored in httpOnly cookie)
- Client-side address autocomplete (Mapbox Places API — called from browser)
- Report rendering, score visualization, trend charts
- Freemium upgrade prompts

**What it does NOT own:**
- Business logic — zero computation happens in Next.js
- Database access — all data comes through FastAPI
- Government API calls — these only happen in ingestion workers

**Rendering strategy:**
- Homepage, pricing, marketing pages → Static (SSG)
- `/report/[addressId]` → Server-side rendered (SSR) for SEO; initial data fetched server-side
- Interactive components (map, compare, live search) → Client Components with SWR

### FastAPI Backend

**What it owns:**
- All business logic
- Authentication / JWT issuance
- Freemium enforcement (lookup counting, tier gating)
- Geocoding orchestration (Mapbox API calls happen here, not in browser)
- Score assembly from PostgreSQL
- Claude API calls for narrative generation
- PDF generation and upload to Blob Storage
- Rate limiting for API customers

**Route structure:**
```
/api/v1/
├── auth/
│   ├── POST /register
│   ├── POST /login
│   └── POST /refresh
├── users/
│   ├── GET  /me
│   └── PUT  /me
├── lookup/
│   └── GET  /?address={raw_address}     → returns address_id + status
├── score/
│   ├── GET  /{address_id}               → full report (reads cache first)
│   └── GET  /{address_id}/trends        → historical score series (Buyer Pro)
├── compare/
│   └── GET  /?a={address_id}&b={address_id}  → side-by-side (Buyer+)
├── narrative/
│   └── POST /                           → generate/retrieve AI narrative
└── reports/
    └── GET  /{address_id}/pdf           → generate and return PDF URL (Buyer Pro)
```

### PostgreSQL + PostGIS

**What it owns:**
- All persistent state
- Geospatial queries (census tract lookup, hospital proximity)
- Historical score data for trend charts
- User accounts and billing state

**PostGIS usage:**
- `ST_Contains(geometry, point)` — find census tract for a coordinate
- `ST_Distance(geometry, point)` — find nearest hospitals/schools
- `geometry <-> point` — KNN index operator for fast nearest-neighbor

### Redis

**What it owns:**
- Score cache (24h TTL, keyed by `score:{geoid}`)
- Narrative cache (6h TTL, keyed by `narrative:{geoid}:{profile}`)
- Free-tier lookup counter (keyed by `lookups:{user_id}:{month}`)
- API rate limiter (keyed by `ratelimit:{api_key}:{minute}`)

**What it does NOT own:**
- Session storage — Auth.js JWTs are stateless; no server sessions
- Durable data — Redis is cache-only; PostgreSQL is truth

### Ingestion Workers

**What they own:**
- Fetching from external government APIs on a schedule
- Data cleaning and normalization
- Writing to raw ingestion tables in PostgreSQL
- Triggering scoring worker after successful ingestion

**What they do NOT own:**
- Serving any user requests
- Modifying `neighborhood_scores` directly (that's the scoring worker's job)

---

## 4. Data Flow: Address Lookup

This is the critical path. Target: < 500ms for cached addresses, < 5s for fresh computation.

```
User types address → clicks "Analyze"
        │
        ▼
[Next.js — browser]
  AddressSearch component calls apiFetch("/api/v1/lookup?address=...")
        │
        │ HTTP GET /api/v1/lookup?address=123+Main+St+Los+Angeles+CA
        ▼
[FastAPI — /api/v1/lookup]
  1. Check auth token (optional — anonymous allowed up to limit)
  2. If authenticated free user: check lookup_count_this_month in DB
     └─ If >= 3: return HTTP 402 Payment Required
  3. Call geocoding service:
     └─ POST Mapbox Geocoding API → returns {lat, lng, address_normalized}
  4. Call Census Geocoder API → returns geoid (census tract FIPS)
  5. Check Redis for cached score: GET score:{geoid}
     ├─ Cache HIT:  return {address_id, status: "cached", report: <score>}
     └─ Cache MISS: 
         a. Check PostgreSQL neighborhood_scores for this geoid
            ├─ DB HIT:  populate Redis, return {status: "cached", report}
            └─ DB MISS: return {address_id, status: "computing"}
                        (scoring worker runs async — client polls)
  6. If user authenticated: increment lookup_count_this_month in DB
  7. Upsert address_lookups table (for dedup and analytics)
        │
        ▼
[Next.js — browser]
  If status == "cached" or "ready": router.push("/report/{address_id}")
  If status == "computing": poll GET /api/v1/score/{address_id} every 2s
```

**Why Mapbox for geocoding?**
- High accuracy for U.S. addresses
- Returns structured address components
- Autocomplete API available for the search input typeahead
- $5/1000 requests — negligible at our scale

**Why Census Geocoder for tract lookup?**
- Free, no rate limits for batch requests
- Authoritative source for census tract assignment
- Returns full FIPS hierarchy (state + county + tract)

---

## 5. Data Flow: Score Computation

Score computation is asynchronous — it is never done in real-time on a user request. All scores are pre-computed by the scoring worker.

```
Trigger: ingestion worker completes OR new geoid requested with no score
        │
        ▼
[Scoring Worker — Python]
  Input: geoid (e.g., "06037201400")

  1. HEALTHCARE SCORE (weight: 25%)
     ├─ Query hospitals table via PostGIS:
     │   SELECT * FROM hospitals WHERE emergency_services = true
     │   ORDER BY geometry <-> tract_centroid LIMIT 5
     ├─ Compute: avg star rating of nearest 3 ERs (normalized 1-5 → 0-100)
     ├─ Compute: distance penalty for nearest ER (< 2mi = 100, > 20mi = 0)
     └─ Healthcare score = star_score * 0.6 + distance_score * 0.4

  2. SAFETY SCORE (weight: 25%)
     ├─ Join census tract → county FIPS
     ├─ Query crime_stats for county, most recent year
     ├─ Compute: violent crime rate percentile across all U.S. counties
     ├─ Compute: property crime rate percentile
     └─ Safety score = (100 - violent_pct) * 0.6 + (100 - property_pct) * 0.4

  3. ENVIRONMENT SCORE (weight: 15%)
     ├─ Query epa_aqi_readings for county, last 30 days
     ├─ Query fema_risk for county
     ├─ Compute: AQI score (AQI 0-50 = 100, AQI 300 = 0, linear)
     ├─ Compute: disaster risk score (invert FEMA risk rating)
     └─ Environment score = aqi_score * 0.5 + disaster_score * 0.5

  4. EDUCATION SCORE (weight: 20%)
     ├─ Query schools table within 2 miles of tract centroid
     ├─ Count public schools by type (elementary/middle/high)
     └─ Education score = availability score (placeholder — enhance with
        state assessment data when available)

  5. ECONOMIC SCORE (weight: 15%)
     ├─ Query zillow_home_values for tract's ZIP, last 12 months
     ├─ Compute: YoY appreciation rate percentile
     └─ Economic score = appreciation_percentile * 0.7 +
                         business_formation_score * 0.3 (when BLS data loaded)

  6. OVERALL SCORE
     = healthcare*0.25 + safety*0.25 + education*0.20 +
       environment*0.15 + economic*0.15

  7. Write to neighborhood_scores table (upsert on geoid + data_vintage)
  8. Invalidate Redis cache: DEL score:{geoid}
        │
        ▼
  Score is now available for the next user request to read
```

**Normalization approach:**
Raw metrics (e.g., "violent crime rate = 4.2 per 100k") are meaningless without context. We normalize using **percentile ranking** across all U.S. census tracts loaded in our system. Tract in the 85th percentile for low crime → safety component = 85. This is recalculated whenever new data is ingested.

---

## 6. Data Flow: AI Narrative Generation

Narrative generation is the differentiator — but it's expensive (Claude API call). We generate lazily and cache aggressively.

```
User requests full report (Buyer tier or higher)
        │
        ▼
[FastAPI — /api/v1/score/{address_id}]
  1. Assemble NeighborhoodReport from DB + cache (scores always available)
  2. Check user tier:
     └─ Free tier: return report WITHOUT narrative field
  3. Check Redis: GET narrative:{geoid}:{user_profile}
     ├─ Cache HIT (< 6h old): attach cached narrative to report, return
     └─ Cache MISS:
         a. Build prompt from NeighborhoodReport scores + user_profile
         b. Call Claude API:
            model: claude-sonnet-4-20250514
            max_tokens: 600
            system: neighborhood analyst persona
            user: structured score data + profile + formatting rules
         c. Store result: SET narrative:{geoid}:{user_profile} EX 21600
         d. Attach narrative to report, return
        │
        ▼
[Next.js — browser]
  NarrativePanel component renders the narrative text
```

**Narrative cache key design:**
`narrative:{geoid}:{profile}` — e.g., `narrative:06037201400:family`

Profiles: `general`, `family`, `retiree`, `young_professional`

This means up to 4 narrative variants per census tract are cached. A tract with 100 lookups per month generates at most 4 Claude calls per 6 hours — not 100.

**Cost control:**
- 600 token max output ≈ $0.003 per narrative (Sonnet pricing)
- With 6h cache and 74k census tracts in top 50 metros, worst case ≈ $0.003 × 4 profiles × 4 refreshes/day × 74,000 tracts = not viable at scale → shift to pre-generation for popular tracts

**Pre-generation strategy (Phase 2):**
- Track lookup frequency per geoid in `address_lookups.lookup_count`
- Daily job: pre-generate narratives for all tracts with > 5 lookups/month
- Extends cache TTL to 24h for pre-generated narratives

---

## 7. Data Flow: Data Ingestion

```
GitHub Actions cron (or Azure Container Apps Job scheduler)
        │
        ▼
[Worker Container — e.g., worker-epa]
  Environment: DATABASE_URL, EPA_AQS_EMAIL, EPA_AQS_KEY

  1. fetch()  — HTTP requests to government API with retry logic
               (tenacity: 3 retries, exponential backoff)
  2. transform() — pandas DataFrame cleanup:
     - Drop records with null geographies
     - Normalize FIPS codes to consistent length (zero-pad)
     - Convert dates to ISO format
     - Cast numerics, handle "Not Available" strings
  3. load()   — asyncpg executemany() with ON CONFLICT DO UPDATE
               (idempotent — safe to re-run)

  On success:
  4. Log completion + record count to stdout (captured by Azure Monitor)
  5. (Optional) Send completion webhook to FastAPI to trigger scoring

  On failure:
  4. Log error with full traceback
  5. Exit code 1 → Azure Container Apps Job marks execution as failed
  6. GitHub Actions / Azure alerts fire (see observability section)
```

**Ingestion schedule:**

| Worker | Schedule | Approx Data Size | Notes |
|---|---|---|---|
| `worker-epa` | Daily 2am UTC | ~50k rows/day | 50 states × parameters |
| `worker-census` | Monthly 1st | ~85k tracts | Geometry is large — ~2GB download |
| `worker-cms` | Monthly 3rd | ~7k hospitals | Stable dataset |
| `worker-fbi` | Monthly 5th | ~18k agencies | Annual data, released quarterly |
| `worker-fema` | Monthly 7th | ~3k counties | Static FEMA NRI dataset |
| `worker-zillow` | Weekly Sunday | ~900 metro CSVs | Public CSV download |
| `worker-scoring` | After each ingestion | Reads all tables | Runs after any worker completes |

**Why not streaming / real-time ingestion?**
Government APIs are batch-oriented — most publish data daily, weekly, or monthly. Real-time ingestion infrastructure (Kafka, Kinesis) would add complexity and cost with no benefit. Scheduled batch workers match the data freshness of the source.

---

## 8. Caching Strategy

### Redis Cache Keys

| Key Pattern | TTL | Content | Eviction |
|---|---|---|---|
| `score:{geoid}` | 24h | JSON-serialized `NeighborhoodReport` | On scoring worker update |
| `narrative:{geoid}:{profile}` | 6h | Plain text narrative string | Time-based only |
| `lookups:{user_id}:{YYYY-MM}` | 32 days | Integer count | Time-based |
| `ratelimit:{api_key}:{epoch_minute}` | 2 min | Integer count | Time-based |
| `geocode:{address_hash}` | 7 days | JSON `{lat, lng, geoid, normalized}` | Time-based |

### Cache-Aside Pattern

All caching follows cache-aside (lazy population):

```
read(key):
  val = redis.get(key)
  if val: return val
  val = db.query(...)
  redis.set(key, val, ttl)
  return val

write(key, val):
  db.upsert(val)
  redis.delete(key)   ← Invalidate, don't update
```

Never write to Redis directly from workers — workers write to PostgreSQL and invalidate the Redis key. The next read populates the cache from the fresh DB data.

### What We Don't Cache

- User profile data (changes on upgrade, must be fresh)
- Stripe billing state (always read from Stripe / DB)
- Authentication tokens (stateless JWT — no server state needed)

---

## 9. Authentication & Authorization

### Mechanism: JWT Bearer Tokens

```
Client                FastAPI               PostgreSQL
  │                      │                      │
  │  POST /auth/login     │                      │
  │  {email, password}    │                      │
  │ ─────────────────►   │                      │
  │                       │  SELECT user WHERE   │
  │                       │  email = ?           │
  │                       │ ────────────────►    │
  │                       │  {id, hashed_pw,     │
  │                       │   tier, ...}         │
  │                       │ ◄────────────────    │
  │                       │                      │
  │                       │  verify_password()   │
  │                       │  create_access_token(user.id)
  │                       │                      │
  │  {access_token,       │                      │
  │   token_type: bearer} │                      │
  │ ◄─────────────────    │                      │
  │                       │                      │
  │  GET /api/v1/score/.. │                      │
  │  Authorization:       │                      │
  │  Bearer <token>       │                      │
  │ ─────────────────►   │                      │
  │                       │  decode_token()      │
  │                       │  → user_id           │
  │                       │  get_user_by_id()    │
  │                       │ ────────────────►    │
  │                       │  User object         │
  │                       │ ◄────────────────    │
  │                       │                      │
  │  response             │                      │
  │ ◄─────────────────    │                      │
```

**Token design:**
- Algorithm: HS256
- Payload: `{sub: user_id, exp: now + 7 days}`
- Secret: 256-bit random string from Azure Key Vault
- No refresh tokens in v1 (re-login after 7 days)

**Next.js session:**
Auth.js stores the JWT in an httpOnly, Secure, SameSite=Strict cookie. The access token is extracted from the session and forwarded in `Authorization: Bearer` headers on server-side API calls.

### Anonymous Access

Some endpoints work without authentication:
- `GET /health` — always public
- `GET /api/v1/lookup` — allowed anonymously (tracked by IP, limited)
- `GET /api/v1/score/{id}` — returns basic scores without narrative for anonymous users

Anonymous rate limiting uses Redis with IP-based keys: `ratelimit:anon:{ip}:{day}` — max 3 lookups/day per IP.

---

## 10. Freemium Enforcement

Enforcement happens in FastAPI middleware / dependencies — never in the frontend (frontend can be bypassed).

```
Tier Gate Logic (checked on every protected request):

get_current_user()           → User object (or None for anonymous)
require_paid_tier()          → raises 402 if tier == "free"
require_tier("buyer_pro")    → raises 402 if tier not in ["buyer_pro", "agent", "brokerage"]
check_lookup_limit()         → raises 402 if free user >= 3 lookups/month
```

**Monthly counter reset:**

Free tier users have `lookup_count_this_month` in the `users` table. A daily worker (or DB trigger) resets this at the start of each billing month:

```sql
UPDATE users
SET lookup_count_this_month = 0
WHERE billing_cycle_start <= NOW() - INTERVAL '1 month'
  AND tier = 'free';
```

**Tier capabilities matrix:**

| Capability | Anonymous | Free | Buyer | Buyer Pro | Agent | Brokerage |
|---|---|---|---|---|---|---|
| Address lookup | 3/day IP | 3/month | Unlimited | Unlimited | Unlimited | Unlimited |
| Basic scores | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AI narratives | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
| Compare (2 addresses) | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |
| Trend forecasting | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| PDF export | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| White-label reports | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ |
| API access | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |

---

## 11. API Design

### Conventions

- **Versioning:** URI prefix `/api/v1/`. Breaking changes → `/api/v2/`
- **Response format:** JSON always
- **Error format:** `{"detail": "human-readable message", "code": "machine-readable-code"}`
- **HTTP status codes:** Standard — 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 402 Payment Required, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests, 500 Internal Server Error
- **Pagination:** `?limit=20&offset=0` for list endpoints
- **Filtering:** Query params on list endpoints

### Key Endpoints (Full Specification)

#### `GET /api/v1/lookup`

```
Query params:
  address (required): Raw address string

Auth: Optional (anonymous allowed with IP rate limit)

Response 200:
{
  "address_id": "uuid",
  "status": "cached" | "computing" | "ready",
  "address_normalized": "123 Main St, Los Angeles, CA 90012",
  "geoid": "06037201400",
  "report": <NeighborhoodReport> | null   // null if status == "computing"
}

Response 402:
{ "detail": "Free tier limit reached. Upgrade for unlimited lookups.", "code": "LIMIT_REACHED" }

Response 422:
{ "detail": "Could not geocode address: zzz not a real place", "code": "GEOCODE_FAILED" }
```

#### `GET /api/v1/score/{address_id}`

```
Auth: Optional

Response 200:
{
  "address": "123 Main St",
  "address_normalized": "123 Main St, Los Angeles, CA 90012",
  "geoid": "06037201400",
  "latitude": 34.0522,
  "longitude": -118.2437,
  "overall_score": 72.5,
  "healthcare": {
    "score": 81.0,
    "label": "Healthcare Access",
    "summary": "Strong hospital access with 2 ERs within 3 miles",
    "factors": [
      {"name": "Nearest ER distance", "value": "1.4 miles", "impact": "positive"},
      {"name": "Hospital star rating", "value": "4.2 avg stars", "impact": "positive"}
    ]
  },
  "safety": { ... },
  "environment": { ... },
  "education": { ... },
  "economic": { ... },
  "narrative": "string | null",   // null for free/anonymous tier
  "data_vintage": "2024-Q4",
  "computed_at": "2024-10-15T08:23:11Z"
}
```

#### `GET /api/v1/compare`

```
Auth: Required, Buyer tier+
Query params:
  a (required): address_id of first address
  b (required): address_id of second address

Response 200:
{
  "address_a": <NeighborhoodReport>,
  "address_b": <NeighborhoodReport>,
  "ai_commentary": "string"   // Claude-generated trade-off analysis
}
```

#### `GET /api/v1/score/{address_id}/trends`

```
Auth: Required, Buyer Pro tier+

Response 200:
{
  "geoid": "06037201400",
  "periods": [
    {
      "period": "2020-Q1",
      "overall_score": 65.2,
      "healthcare_score": 74.0,
      "safety_score": 60.1,
      "environment_score": 71.3,
      "education_score": 58.0,
      "economic_score": 62.5
    },
    ...  // up to 16 quarters
  ]
}
```

### B2B API Authentication

API customers (brokerage tier) authenticate via API key, not JWT:

```
Header: X-API-Key: niq_live_abc123...

Rate limits:
  Standard:   100 requests/minute
  Enterprise: 1000 requests/minute (negotiated)

Per-lookup billing tracked in api_usage_log table.
```

---

## 12. Database Design Decisions

### Why PostGIS?

Three core operations require geospatial capabilities:

1. **Point-in-polygon:** Given a lat/lng, which census tract does it fall in?
   - `ST_Contains(tract.geometry, ST_MakePoint(lng, lat))` with GIST index
   - Alternative: store pre-computed tract-to-ZIP mapping table (simpler, but loses precision)

2. **Nearest neighbor:** Find the 5 closest hospitals to this address.
   - `ORDER BY hospital.geometry <-> point LIMIT 5` (KNN with GIST index)
   - Without PostGIS, this requires fetching all hospitals and computing distances in Python

3. **Proximity counting:** How many schools within 2 miles?
   - `ST_DWithin(school.geometry::geography, point::geography, 3218.69)` (3218.69m = 2mi)

Without PostGIS, these queries would be either: (a) extremely slow full-table scans, or (b) approximated with bounding box queries that are inaccurate near boundaries.

### Why UUID Primary Keys?

- Distributed-safe: no coordination needed for ID generation across workers
- No information leakage: sequential IDs reveal record count and creation order
- Safe to expose in URLs: `/report/abc123...` vs `/report/42`

### Why PostgreSQL over SQLite / MongoDB?

- PostGIS requires PostgreSQL
- ACID transactions critical for billing state (lookup counts, tier upgrades)
- JSON columns available when schema-less storage is useful (factor details)
- Complex analytical queries (percentile ranking for score normalization)

### Schema Denormalization Decisions

`county_fips` is stored on multiple raw tables (crime_stats, epa_aqi_readings, fema_risk) rather than normalized through a counties table. This is intentional: government APIs all return FIPS codes natively, and joining through a counties lookup table would add a join to every score computation query with no benefit.

---

## 13. Scoring Model Design

### Philosophy

Scores are **percentile-based, not absolute**. A tract in the 80th percentile for hospital access gets an 80, regardless of the raw distance. This means:

- Scores are comparable across all U.S. locations
- Scores are relative to the national distribution
- Rural areas don't get unfairly penalized on an absolute scale — they're compared to other rural areas

### Weighting

Default weights reflect first-time buyer priorities (research-driven):

```
Healthcare:  25%  — most buyers cite healthcare access as top concern
Safety:      25%  — crime and disaster risk are top concerns
Education:   20%  — especially critical for families
Environment: 15%  — air quality, disaster risk
Economic:    15%  — investment trajectory
```

**Personalization (Phase 2):**
User profile questionnaire adjusts weights:

```python
PROFILE_WEIGHTS = {
    "family": {
        "healthcare": 0.20, "safety": 0.25, "education": 0.35,
        "environment": 0.10, "economic": 0.10
    },
    "retiree": {
        "healthcare": 0.35, "safety": 0.25, "education": 0.05,
        "environment": 0.20, "economic": 0.15
    },
    "young_professional": {
        "healthcare": 0.15, "safety": 0.20, "education": 0.10,
        "environment": 0.15, "economic": 0.40
    },
}
```

### Score Recalculation Cadence

Scores are recalculated whenever their underlying data changes:

```
EPA ingestion (daily) → recalculate environment scores for updated counties
FBI ingestion (monthly) → recalculate safety scores nationwide
CMS ingestion (monthly) → recalculate healthcare scores nationwide
FEMA ingestion (monthly) → recalculate environment (disaster) scores
```

Full nationwide recalculation for ~74,000 tracts takes ~15-30 minutes on a single worker (PostGIS queries are fast with proper indexes). This is acceptable for monthly cadence.

---

## 14. Scaling Strategy

### Current (Phase 1: 0–500 users)

- Azure Container Apps scaled to zero (pays only when running)
- Single PostgreSQL Flexible Server instance (Burstable B2ms — 2 vCPU, 8GB RAM)
- Redis Basic tier (C0 — 250MB)
- Estimated cost: $100–120/month

### Phase 2 (500–5,000 users, $5K–$50K MRR)

- Container Apps: min-replicas 1 for API (eliminate cold start), max 10
- PostgreSQL: upgrade to General Purpose (4 vCPU, 16GB) + read replica for scoring workers
- Redis: Standard C1 (1GB, replication)
- Enable Azure Front Door caching for static assets and common score responses
- Estimated cost: $400–600/month

### Phase 3 ($50K+ MRR, Series A)

- PostgreSQL: Separate read replicas for analytics vs. transactional queries
- Score computation: Move to Azure Databricks or Synapse for full-nation recalculation
- Add Azure Service Bus between ingestion workers and scoring worker (decouple, retry)
- Consider read-heavy caching at the Front Door layer for popular tracts
- Redis Cluster mode for horizontal scaling

### Bottleneck Analysis

| Component | Bottleneck | Mitigation |
|---|---|---|
| Geocoding | Mapbox API rate limits (600 req/min) | Geocode cache in Redis (7d TTL) |
| Score reads | DB connection pool exhaustion | PgBouncer connection pooler (Phase 2) |
| Narrative generation | Claude API latency (~2-4s) | Redis cache + pre-generation for popular tracts |
| Ingestion workers | Government API rate limits | Retry with backoff, spread over hours |
| PDF generation | CPU-bound (reportlab) | Async background task, return URL when ready |

---

## 15. Failure Modes & Resilience

### Government API Downtime

**Risk:** EPA, CMS, FBI APIs occasionally go down for maintenance.

**Mitigation:**
- Ingestion workers use `tenacity` for retry with exponential backoff (3 attempts)
- Workers are idempotent — safe to re-run after failure
- Failures are non-blocking: cached scores remain valid; no user impact
- Alert fires if worker hasn't completed in 2× expected time

### Mapbox Geocoding Failure

**Risk:** Address lookup fails if Mapbox is down.

**Mitigation:**
- Geocoding results cached in Redis (7d TTL) — repeat lookups don't hit Mapbox
- Fallback: Census Geocoder API (free, slower, less accurate) as secondary geocoder
- Return 503 with user-friendly message if both fail

### Claude API Failure

**Risk:** Narrative generation fails if Anthropic API is down.

**Mitigation:**
- Narrative is non-blocking: return score report without narrative, show placeholder UI
- Retry on next request (no permanent failure)
- Cached narratives (6h) buffer most outages
- Log as warning (not error) — scores still work

### Database Connection Loss

**Risk:** PostgreSQL connection fails.

**Mitigation:**
- SQLAlchemy connection pool with `pool_pre_ping=True` (validates connections before use)
- Container App health check: if DB unreachable for > 30s, container restarts
- Azure Database for PostgreSQL has 99.99% SLA with automatic failover (General Purpose tier)

### Redis Connection Loss

**Risk:** Cache layer unavailable.

**Mitigation:**
- All Redis calls wrapped in try/except — fall through to PostgreSQL on cache miss
- System degrades gracefully (slower, but functional)
- Log Redis errors as warnings

### Container Crash Loop

**Risk:** FastAPI container crashes repeatedly due to bug.

**Mitigation:**
- Azure Container Apps: exponential backoff on restart (max delay: 5 min)
- Old image not removed from ACR — can roll back in < 2 minutes via:
  ```bash
  az containerapp update --name niq-api --image <previous_image_tag>
  ```
- GitHub Actions deploy only runs after CI passes

---

## 16. Security Model

### Threat Model

Primary threats at our scale:

1. **Credential stuffing / account takeover** — mitigated by bcrypt password hashing + rate-limiting login endpoint
2. **API key theft** — mitigated by short JWT TTL (7 days), httpOnly cookies in browser
3. **Data scraping** — mitigated by rate limiting + freemium gates
4. **SQL injection** — mitigated by SQLAlchemy parameterized queries (no raw SQL with user input)
5. **Secret exposure** — mitigated by Azure Key Vault (no secrets in code or Docker images)

### Network Security

```
Internet → Azure Front Door (WAF) → Container Apps (internal VNet)
                                  → PostgreSQL (private endpoint — no public access)
                                  → Redis (private endpoint — no public access)

Workers → PostgreSQL (private endpoint, same VNet)
FastAPI → Claude API (outbound HTTPS only)
FastAPI → Mapbox (outbound HTTPS only)
```

PostgreSQL and Redis are **never** exposed to the public internet. Only the Container Apps can reach them, through Azure private endpoints within the VNet.

### Input Validation

All API inputs validated by Pydantic before reaching business logic:
- Address strings: max 500 chars, alphanumeric + punctuation only
- UUIDs: validated as proper UUID format
- Numeric ranges: scores must be 0-100, coordinates must be valid lat/lng ranges

### Secret Management

```
Development: .env file (gitignored)
Production:  Azure Key Vault → Container Apps environment variables
             (secrets mounted at runtime, never baked into Docker images)

Secret rotation procedure:
1. Update secret in Azure Key Vault
2. Trigger new Container Apps revision (secrets are read at startup)
3. Old revision drains and shuts down
```

### CORS Policy

```python
CORS_ORIGINS = [
    "http://localhost:3000",           # Local dev
    "https://nh-iq.com",      # Production
    "https://www.nh-iq.com",  # Production www
]
# B2B API consumers: no CORS needed (server-to-server)
```

---

## 17. Observability

### Logging

All services use structured JSON logging to stdout. Azure Container Apps forwards stdout to Log Analytics.

**Log levels:**
- `DEBUG` — local dev only, verbose internal state
- `INFO` — request start/end, ingestion record counts, cache hits/misses
- `WARNING` — Claude API slow response, Redis miss on expected cache hit, 4xx responses
- `ERROR` — DB connection failure, 5xx responses, ingestion worker failures

**Standard log fields (every API request):**
```json
{
  "timestamp": "2024-10-15T08:23:11Z",
  "level": "INFO",
  "service": "api",
  "method": "GET",
  "path": "/api/v1/score/abc123",
  "status_code": 200,
  "duration_ms": 142,
  "user_id": "uuid-or-null",
  "geoid": "06037201400",
  "cache_hit": true
}
```

### Metrics (Azure Monitor)

Key metrics to track:

| Metric | Alert Threshold |
|---|---|
| API p95 response time | > 2000ms |
| Error rate (5xx) | > 1% over 5 min |
| Cache hit rate | < 60% sustained |
| Ingestion worker last success | > 48h ago |
| Active container replicas | > 8 (scaling pressure) |
| PostgreSQL connection pool usage | > 80% |
| Redis memory usage | > 80% |

### Tracing

Azure Application Insights distributed tracing connects:
- Front Door request → Next.js render → FastAPI handler → DB query → Redis → Claude API

This allows tracing a slow request end-to-end across all services.

---

## 18. Build Sequence

Execute in this order to stand up the system from scratch:

```
Week 1-2: Foundation
  1. Monorepo scaffold (docs/01-monorepo-setup.md)
  2. Dockerfiles + docker-compose (docs/04-dockerfiles.md)
  3. FastAPI skeleton + health check (docs/03-fastapi-backend.md — Steps 1-4)
  4. Database schema + init.sql (docs/08-database-schema.md)
  5. Verify: docker compose up → all services green

Week 3-4: Core Data Pipeline
  6. Census tract ingestion worker (docs/07-data-ingestion-workers.md — Priority 2)
  7. EPA AQI ingestion worker (docs/07-data-ingestion-workers.md — Priority 1)
  8. Scoring worker — healthcare + environment scores
  9. Verify: census_tracts and neighborhood_scores populated for test tracts

Week 5-6: API Layer
  10. Geocoding service (Mapbox + Census Geocoder)
  11. /api/v1/lookup endpoint
  12. /api/v1/score endpoint (reads from DB)
  13. Auth endpoints (register, login)
  14. Redis caching layer
  15. Verify: curl lookup → score → data returns correctly

Week 7-8: Frontend
  16. Next.js scaffold (docs/02-nextjs-frontend.md)
  17. Homepage + AddressSearch component
  18. Report page + ScoreSummary component
  19. Connect to API via apiFetch
  20. Auth pages (login, register)
  21. Verify: full user flow works in browser

Week 9-10: AI + Remaining Data
  22. Claude narrative service
  23. CMS hospital ingestion worker
  24. FBI crime ingestion worker
  25. /api/v1/compare endpoint
  26. Freemium gates (lookup limits, tier checks)
  27. Verify: free vs. paid tier behavior correct

Week 11-12: Production
  28. Azure infrastructure (docs/06-azure-infrastructure.md)
  29. CI/CD pipeline (docs/05-cicd.md)
  30. GitHub secrets configured
  31. First production deploy
  32. Verify: production URLs respond, logs flowing to Azure Monitor
```

---

## 19. Future Architecture Considerations

These are NOT current requirements — document them here to ensure future decisions don't back us into corners.

### Browser Extension (Phase 3)

The Zillow/Redfin overlay extension will call the same `/api/v1/lookup` endpoint with an API key. No new backend needed. The extension will be a Chrome/Firefox extension that:
1. Detects address elements on Zillow/Redfin listing pages
2. Calls our API with the address
3. Renders a score badge inline on the listing

### White-Label Reports (Agent Tier)

Agent-tier reports need custom branding (logo, color scheme, agent contact). Implementation: store branding config in `users` table (JSON column), pass to PDF generation service at report generation time. No architecture change needed — just a new parameter in the PDF worker.

### Webhook / CRM Integration (Brokerage Tier)

Brokerages want NeighborhoodInsight data pushed to their CRM when a new listing is analyzed. Implementation: add `webhooks` table, fire POST requests to registered URLs after score computation. This is a simple async background task — no new infrastructure.

### Multi-Region (Series B+)

If we expand beyond top 50 U.S. metros to full U.S. coverage:
- Census tracts: ~85,000 (currently loading top 50 metros ≈ 30,000 tracts)
- PostgreSQL storage grows ~3× — still manageable on General Purpose tier
- Scoring worker runtime grows ~3× — acceptable or parallelize by state

International expansion would require re-evaluating the entire data layer (no equivalent free government APIs in most countries).

### Real-Time Score Updates

Current design: scores update daily/monthly. If we ever want "live" AQI scores:
- Subscribe to EPA's real-time AirNow API (hourly data)
- Store in a separate `epa_aqi_realtime` table
- Blend real-time AQI with historical baseline for environment score
- Still no need for streaming infrastructure — hourly poll from a worker is sufficient

---

*Last updated: see git log for `docs/10-system-design.md`*
*Owner: Technical Co-founder*
*Review cadence: Update when any architectural decision changes*
