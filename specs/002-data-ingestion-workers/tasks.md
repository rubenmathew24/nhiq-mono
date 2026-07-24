# Tasks: Data Ingestion Workers

**Input**: Design documents from `/specs/002-data-ingestion-workers/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Revision (2026-07-14 reopen)**: Regenerated for clarified reopen — **R1 safety (FBI CDE)** → **R2 education (NCES + Urban)** → **R3 economic (ACS + BLS LAUS)** on the same `002` branch. MVP stories US1–US5 remain `[x]`. Prior FBI-skeleton-only close-out superseded by US6 implementation tasks.

**Tests**: Constitution VI — pytest under `workers/tests/` and `apps/api/tests/`; Vitest under `apps/web/src/__tests__/` when UI changes.

**Organization**: By user story. Build order: geometry → EPA → CMS → scoring → live reports → **safety → education → economic**.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no incomplete blockers)
- **[Story]**: US1…US8 from spec.md
- Exact file paths in every task

## Path Conventions

- Workers: `workers/ingest/<source>/`, `workers/scoring/`
- API: `apps/api/app/`, tests `apps/api/tests/`
- Web: `apps/web/src/`
- SQL: `infra/sql/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Worker package layout, fixtures, Compose — MVP complete

- [x] T001 Create `workers/ingest/{epa,census,cms,fbi}/` package layout and `workers/scoring/` per plan.md
- [x] T002 [P] Pin worker deps in `workers/ingest/requirements.txt` (httpx, psycopg2, geopandas, redis, pytest, …)
- [x] T003 [P] Add fixture module `workers/ingest/fixtures/canonical_addresses.py` (10 addresses + county FIPS allowlist)
- [x] T004 [P] Add shared constants in `workers/ingest/fixtures/constants.py` (`DATA_VINTAGE`, weights, EPA lag/lookback, placeholders)
- [x] T005 Verify `.gitignore` / `.dockerignore` for Python workers + Compose (no secrets)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, base worker, Compose — MVP done; reopen DDL + env before US6+

**⚠️ CRITICAL**: Reopen stories US6–US8 need T011–T013 before implementation

- [x] T006 Extend `infra/sql/init.sql` with `epa_aqi_readings`, `hospitals`, `crime_stats` (+ indexes)
- [x] T007 Harden `workers/ingest/base.py` (`DATABASE_URL` fail-fast, fetch→transform→load logging)
- [x] T008 [P] One-shot DDL `infra/sql/002_raw_ingest_tables.sql` for existing Compose volumes
- [x] T009 Wire Compose worker profiles in `docker-compose.yml` (`worker-epa`, `worker-census`, `worker-cms`, `worker-scoring`, `worker-fbi`)
- [x] T010 Slim `docker/worker.Dockerfile` (Python 3.12, `PYTHONPATH=/app`)
- [x] T010a Apply `infra/sql/003_score_sources.sql` / `score_sources` on `neighborhood_scores`
- [x] T011 Add reopen DDL `infra/sql/004_safety_education_economic.sql` for `crime_agency_selection`, `crime_offense_monthly`, `schools_nces`, `schools_urban`, `acs_indicators`, `bls_laus_county` per `data-model.md` (also mirror essentials into `infra/sql/init.sql`)
- [x] T012 [P] Sync `.env.example` with `FBI_CDE_API_KEY`, optional `FBI_CDE_*` knobs, `CENSUS_API_KEY`, BLS notes per `contracts/worker-cli.md`
- [x] T013 [P] Create package stubs `workers/ingest/{nces,urban,acs,bls}/__init__.py` for R2/R3 entrypoints

**Checkpoint**: Reopen schema + env ready; US6 can start

---

## Phase 3: User Story 1 — EPA AQS ingest (Priority: P1) ✅

**Goal**: Fixture-county EPA daily AQI in `epa_aqi_readings`

**Independent Test**: `worker-epa` upserts; second run idempotent; empty counties OK

- [x] T014 [P] [US1] EPA transform/upsert tests in `workers/tests/test_epa_transform.py`
- [x] T015 [US1] Implement EPA client/transform/load in `workers/ingest/epa/`
- [x] T016 [US1] Wire `worker-epa` → `python -m ingest.epa.run` in `docker-compose.yml`

**Checkpoint**: US1 done (MVP)

---

## Phase 4: User Story 2 — Census tracts (Priority: P1) ✅

**Goal**: Fixture-county TIGER tracts in `census_tracts`

**Independent Test**: Tract count per fixture county; PIP for Bentonville

- [x] T017 [P] [US2] Census transform tests in `workers/tests/test_census_transform.py`
- [x] T018 [US2] Implement census ingest in `workers/ingest/census/`
- [x] T019 [US2] Wire `worker-census` in `docker-compose.yml`

**Checkpoint**: US2 done (MVP)

---

## Phase 5: User Story 3 — CMS hospitals (Priority: P2) ✅

**Goal**: Fixture-state hospitals + ZIP geometry

**Independent Test**: Hospital/geometry/ER counts; idempotent upsert

- [x] T020 [P] [US3] CMS transform tests in `workers/tests/test_cms_transform.py`
- [x] T021 [US3] Implement CMS + ZIP geocode in `workers/ingest/cms/`
- [x] T022 [US3] Wire `worker-cms` in `docker-compose.yml`

**Checkpoint**: US3 done (MVP)

---

## Phase 6: User Story 4 — Healthcare + environment scoring (Priority: P2) ✅

**Goal**: County-wide scores; EPA→Open-Meteo env; placeholders for undelivered dims

**Independent Test**: Score rows ≈ tracts; Benton env provenance; placeholders until US6–US8

- [x] T023 [P] [US4] Formula/environment tests in `workers/tests/test_scoring_compute.py` + `workers/tests/test_environment_resolve.py` + `workers/tests/test_open_meteo.py`
- [x] T024 [US4] Implement scoring in `workers/scoring/{compute,formulas,environment,open_meteo}.py`
- [x] T025 [US4] Wire `worker-scoring` + Redis invalidate in `docker-compose.yml`

**Checkpoint**: US4 done (MVP)

---

## Phase 7: User Story 5 — Live reports (Priority: P1) ✅

**Goal**: Lookup/score serve DB scores; `SCORE_UNAVAILABLE`; `sources` on report

**Independent Test**: Bentonville overall matches DB; API `sources.environment`

- [x] T026 [P] [US5] Live score API tests in `apps/api/tests/test_score_live.py`
- [x] T027 [US5] Live `score_service` + endpoint in `apps/api/app/services/score_service.py` and `apps/api/app/api/v1/endpoints/score.py`
- [x] T028 [US5] Unavailable report UI in `apps/web/src/` (no mock-as-live)

**Checkpoint**: US5 done (MVP) — reopen slices extend `sources.{safety,education,economic}`

---

## Phase 8: User Story 6 — Safety (FBI CDE) reopen R1 (Priority: P1) 🎯 reopen MVP

**Goal**: Replace FBI skeleton with fixture-scoped CDE ingest; non-placeholder `safety_score` + `score_sources.safety`

**Independent Test**: quickstart V7 — `worker-fbi` + `worker-scoring`; Bentonville `safety_score` ≠ 65.0 placeholder; `sources.safety.source_id` = `fbi_cde` (or documented `default`); education/economic may stay placeholders

### Tests for User Story 6

- [x] T029 [P] [US6] Unit tests for CDE agency select / offense transform in `workers/tests/test_fbi_cde_transform.py`
- [x] T030 [P] [US6] Unit tests for safety score formula vs state benchmark in `workers/tests/test_safety_formula.py`
- [x] T031 [P] [US6] Extend `apps/api/tests/test_score_live.py` to assert mocked `sources.safety.source_id` ∈ {`fbi_cde`,`default`} (not `placeholder`)

### Implementation for User Story 6

- [x] T032 [US6] Implement FBI CDE client (agency by state, chart fetch, HOM-required) in `workers/ingest/fbi/client.py` using probe path from `research.md` §8
- [x] T033 [US6] Implement transform + upsert into `crime_agency_selection` / `crime_offense_monthly` in `workers/ingest/fbi/transform.py` and load helpers
- [x] T034 [US6] Replace skeleton entrypoint with real runner in `workers/ingest/fbi/run.py` (fail fast if `FBI_CDE_API_KEY` missing; fixture-county loop; progress logs)
- [x] T035 [P] [US6] Implement `safety_from_cde` (or equivalent) in `workers/scoring/safety.py` + export from `workers/scoring/formulas.py` per research.md §8c
- [x] T036 [US6] Integrate safety into `workers/scoring/compute.py` (county ORI aggregate → all tracts; write `score_sources.safety`; keep education/economic placeholders)
- [x] T037 [US6] Confirm `worker-fbi` Compose service still maps to `python -m ingest.fbi.run` in `docker-compose.yml` (rebuild image notes in quickstart if needed)
- [x] T038 [US6] Run Compose V7 smoke per `specs/002-data-ingestion-workers/quickstart.md` (apply `infra/sql/004_safety_education_economic.sql` if needed; `worker-fbi` + `worker-scoring`; Bentonville SQL + `/api/v1/score` check)

**Checkpoint**: Safety dimension live for fixture counties — education/economic still placeholders OK

---

## Phase 9: User Story 7 — Education (NCES + Urban) reopen R2 (Priority: P2)

**Goal**: Dual school ingest; complementary `education_score` + dual provenance

**Independent Test**: quickstart V8 — NCES + Urban + scoring; Bentonville education leaves placeholder; `score_sources.education` lists both contributors

### Tests for User Story 7

- [x] T039 [P] [US7] NCES transform tests in `workers/tests/test_nces_transform.py`
- [x] T040 [P] [US7] Urban transform / `ncessch` join tests in `workers/tests/test_urban_transform.py`
- [x] T041 [P] [US7] Education blend formula tests (access vs staffing; partial-source reasons) in `workers/tests/test_education_formula.py`
- [x] T042 [P] [US7] Extend `apps/api/tests/test_score_live.py` for mocked `sources.education` with dual contributors

### Implementation for User Story 7

- [x] T043 [US7] Implement NCES EDGE fetch/filter/upsert in `workers/ingest/nces/` → `schools_nces`
- [x] T044 [US7] Implement Urban CCD directory fetch/upsert in `workers/ingest/urban/` → `schools_urban` keyed by `ncessch`
- [x] T045 [P] [US7] Wire `worker-nces` and `worker-urban` services in `docker-compose.yml` (`python -m ingest.nces.run` / `ingest.urban.run`)
- [x] T046 [US7] Implement education scoring in `workers/scoring/education.py` and integrate in `workers/scoring/compute.py` (NCES access + Urban staffing; no silent placeholder on dual-success claim)
- [x] T047 [US7] Run Compose V8 per `specs/002-data-ingestion-workers/quickstart.md` (`worker-nces` → `worker-urban` → `worker-scoring`; Bentonville `education_score` + provenance in DB/API)

**Checkpoint**: Education live; economic may still be placeholder

---

## Phase 10: User Story 8 — Economic (ACS + BLS LAUS) reopen R3 (Priority: P2)

**Goal**: Dual economic ingest; complementary `economic_score`; all five dims source-backed for fixtures

**Independent Test**: quickstart V9 — ACS + BLS + scoring; Bentonville economic non-placeholder; overall uses all weights with real inputs

### Tests for User Story 8

- [x] T048 [P] [US8] ACS transform tests in `workers/tests/test_acs_transform.py`
- [x] T049 [P] [US8] BLS LAUS series parse tests in `workers/tests/test_bls_laus_transform.py`
- [x] T050 [P] [US8] Economic blend formula tests (income vs unemployment; no double-count) in `workers/tests/test_economic_formula.py`
- [x] T051 [P] [US8] Extend `apps/api/tests/test_score_live.py` for mocked `sources.economic` dual contributors

### Implementation for User Story 8

- [x] T052 [US8] Implement ACS 5-year tract/county pull + upsert in `workers/ingest/acs/` → `acs_indicators`
- [x] T053 [US8] Implement BLS LAUS county unemployment pull + upsert in `workers/ingest/bls/` → `bls_laus_county`
- [x] T054 [P] [US8] Wire `worker-acs` and `worker-bls` in `docker-compose.yml`
- [x] T055 [US8] Implement economic scoring in `workers/scoring/economic.py` and integrate in `workers/scoring/compute.py`
- [x] T056 [US8] Run Compose V9 per `specs/002-data-ingestion-workers/quickstart.md` (`worker-acs` → `worker-bls` → `worker-scoring`; Bentonville economic + five-dimension smoke)

**Checkpoint**: All reopen dimensions delivered for fixture counties

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Docs + end-to-end hygiene after R1–R3

- [x] T057 [P] Update root `README.md` worker order for fbi/nces/urban/acs/bls after each phase lands
- [x] T058 [P] Keep `docs/nhiq-design-main/07-data-ingestion-workers.md` local-path note accurate (no Azure Jobs for 002)
- [x] T059 Sync `specs/002-data-ingestion-workers/contracts/worker-cli.md` if command names/env diverge during implement
- [x] T060 Run full quickstart V1–V9 against Compose; mark V7–V9 done checkboxes in `specs/002-data-ingestion-workers/quickstart.md`
- [x] T061 Confirm no Azure Container Apps Job / `master` deploy artifacts in `.github/workflows/` or `docker-compose.yml`; PR target remains `dev`
- [x] T062 [P] Remove or rewrite obsolete FBI-skeleton-only tests in `workers/tests/test_fbi_skeleton.py` once CDE runner is real

**Checkpoint**: Feature ready to close / PR to `dev`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)** → **Foundational (2)** including T011–T013 → stories
- **US1–US5**: Complete (MVP); do not regress
- **US6 (R1)**: After T011–T013; **reopen MVP** — implement next
- **US7 (R2)**: After US6 scoring integration stable (can share schema from T011)
- **US8 (R3)**: After US7 preferred (phase order); only depends on foundation + tracts for ACS geography
- **Polish**: After desired reopen phases

### User Story Dependencies

| Story | Priority | Depends on | Independently testable? |
|-------|----------|------------|-------------------------|
| US1 EPA | P1 | Foundation | Yes — MVP done |
| US2 Census | P1 | Foundation | Yes — MVP done |
| US3 CMS | P2 | Foundation | Yes — MVP done |
| US4 Scoring | P2 | US1–US3 | Yes — MVP done |
| US5 Live reports | P1 | US4 | Yes — MVP done |
| US6 Safety | P1 | Foundation + tracts + scoring plumbing | Yes — V7 |
| US7 Education | P2 | Foundation + tracts + scoring | Yes — V8 (after R1 optional) |
| US8 Economic | P2 | Foundation + tracts + scoring | Yes — V9 |

### Parallel Opportunities

- Within US6: T029–T031 tests in parallel; T032–T033 then T034; T035 parallel to T032 once formula inputs known
- Within US7: T039–T042 tests; T043 ∥ T044; T045 after both
- Within US8: T048–T051 tests; T052 ∥ T053; T054 after packages exist
- T012 ∥ T013 after T011 designed

---

## Parallel Example: User Story 6 (reopen MVP)

```bash
# Tests in parallel:
Task: "T029 CDE transform tests in workers/tests/test_fbi_cde_transform.py"
Task: "T030 safety formula tests in workers/tests/test_safety_formula.py"
Task: "T031 API sources.safety assertion in apps/api/tests/test_score_live.py"

# Then implementation:
Task: "T032–T034 FBI CDE client/transform/run"
Task: "T035–T036 scoring safety.py + compute.py integration"
Task: "T038 Compose V7 smoke"
```

---

## Implementation Strategy

### Reopen MVP (User Story 6 only)

1. Complete Phase 2 reopen foundation (T011–T013)
2. Complete Phase 8 US6 (FBI CDE + safety scores)
3. **STOP and VALIDATE** quickstart V7 + Bentonville
4. Demo / optional PR to `dev` for safety slice alone

### Incremental Delivery

1. US6 safety → validate V7
2. US7 education → validate V8
3. US8 economic → validate V9
4. Polish T057–T062 → feature close

### Already delivered (do not rebuild)

Phases 1–7 (US1–US5): census/EPA/CMS/scoring/live reports with environment provenance. Treat `[x]` as frozen unless regressing.

---

## Notes

- `[x]` = done on branch; `[ ]` = required for reopen close-out
- Do not implement Azure Jobs or merge to `master` in this feature
- Do not build source-showcase UI
- Zillow/Redfin/FEMA remain out of scope
- Prefer probe guide patterns; do not vendor full `nhiq/backend/scripts` harness
- Commit after each task or logical group when implementing

---

## Phase 12: Convergence

- [x] T063 Update live dimension summaries + deterministic `narrative` in `apps/api/app/services/score_service.py` to reflect `score_sources` for safety/education/economic (no “placeholder until ingest” copy when those sources are delivered); extend `apps/api/tests/test_score_live.py` (or score_service unit tests) accordingly per FR-007, US5/AC3, contracts/score-api.md (partial)
- [x] T064 Update `apps/web/src/components/report/ReportAiSummary.tsx` so live reports are not labeled “Sample scores — full neighborhood intelligence coming soon”; keep Claude-later framing honest per FR-014, US5 (contradicts)
- [x] T065 Redact API keys from worker HTTP client logs (FBI CDE / Census ACS query params in httpx INFO URLs) in `workers/ingest/fbi/client.py` and `workers/ingest/acs/client.py` (or shared logging setup) per Constitution V (partial)
- [x] T066 Make fixture-scoped ingest completion logs report partial vs full county coverage when some units fail (at least FBI CDE runner / shared base pattern) per Edge Cases, FR-011 (partial)

---

## Phase 13: Convergence

- [x] T067 Update `specs/002-data-ingestion-workers/quickstart.md` Done-when checkboxes for V7 (FBI CDE / Bentonville non-placeholder safety) and V9 (ACS + BLS dual-source economic) to match the completed Compose smokes; note FBI may still be partial on non-Benton fixture counties due to upstream 503s per SC-007, T060 (partial)

---

## Phase 14: TIGER land/water area (amend 2026-07-23)

**Purpose**: Persist Census TIGER `ALAND`/`AWATER` so Discover can exclude water-only tracts. Align with `003` national census path and `008` Discover filter.

- [x] T068 Add additive migration `infra/sql/010_census_tract_land_water.sql` (`aland`/`awater` BIGINT NULL) and mirror columns in `infra/sql/init.sql` per `data-model.md` / FR-004a
- [x] T069 Keep `ALAND`/`AWATER` in `workers/ingest/census/run.py` transform and `workers/ingest/census/transform.py` (`filter_tract_records`); upsert both columns on load
- [x] T070 [P] Unit/integration tests: fixture or sample TIGER row with `ALAND=0` persists `aland=0`; land tract persists positive `aland` in `workers/tests/` (or census transform tests)
- [x] T071 Document re-ingest for existing DBs in `specs/002-data-ingestion-workers/quickstart.md` (migration + `worker-census` force/re-run for Cook County / Chicago demo)
