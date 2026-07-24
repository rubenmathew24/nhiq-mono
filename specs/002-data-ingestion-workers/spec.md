# Feature Specification: Data Ingestion Workers

**Feature Branch**: `002-data-ingestion-workers`

**Created**: 2026-07-14

**Status**: Draft (reopened for safety / education / economic source workers)

**Input**: User description: "We need to get the workers up and running. Use docs/nhiq-design-main/07-data-ingestion-workers.md to help you design the spec." Follow-on: extend this same feature (not a new branch) to replace safety, education, and economic placeholders with real source workers.

## Clarifications

### Session 2026-07-14

- Q: How should local verification of workers prove end-to-end value? → A: Use a fixed fixture of **10 street addresses** (including `609 SE Jamaica Dr, Bentonville, AR`); workers populate the DB with the raw + score data those addresses need; the **local/dev app** must let an operator search those addresses and open score reports driven by ingested/computed data (not mock-only).
- Q: Should production cloud scheduling ship in this feature? → A: No (option B) — local Docker one-off runs only; cloud schedules deferred.
- Q: How wide should local worker ingest be? → A: **Fixture-scoped only** (option A) — ingest/score geographies needed for the 10 addresses (and hospitals usable nearby). **No national-scope testing** in this feature.
- Q: Which tracts should the score job compute? → A: **All tracts in the counties** that contain the 10 fixture addresses (not only the single address tract; not whole-state or national). Address-only tracts are insufficient for nearby/context scoring inputs.
- Q: Environment AQ when EPA monitors are sparse/missing? → A: **EPA AQS is primary**. If county EPA data in the scoring window is missing or unworthy (fewer than a documented minimum of distinct monitor-days), **fall back to Open-Meteo modeled US AQI** at the county centroid. Persist per-dimension **source provenance** on score rows (and return it on the API) so a future “show sources” feature can use it — showcase UI is **out of scope** for this feature.
- Q: How should safety, school (education), and economy workers be delivered after the healthcare/environment MVP? → A: **Reopen / extend `002-data-ingestion-workers`** (same feature branch and spec)—do **not** start a separate `003` feature for these dimensions.
- Q: What must pass before this reopen is considered done? → A: **Phased on the same `002` branch** (option B) — **safety first** as a closeable slice; then **education**; then **economic** as follow-on tasks. Placeholders remain only for dimensions not yet delivered in the current phase.
- Q: What is the primary safety data source for the first reopen phase? → A: **FBI Crime Data Explorer (CDE) chart/agency path** (option A) — fixture-county nearest agencies via `FBI_CDE_API_KEY`; replace the FBI skeleton with a real ingest that feeds non-placeholder safety scores.
- Q: What education sources are required before the education phase closes? → A: **Both NCES and Urban Institute** (option B) — NCES for government-provided school directory/identity; Urban for complementary statistics. Planning MUST explore fields from each and use complementary signals in the education score (not duplicate the same metric twice).
- Q: Which sources must the economic phase use? → A: **Census ACS + BLS LAUS** (option B / recommended) — ACS as the government spine for fixture geographies; BLS LAUS unemployment as a complementary labor signal. Planning MUST explore fields from each for scoring. Zillow/Redfin remain out of scope (FR-013).

### Session 2026-07-23 (TIGER land/water area)

- Q: Should census tract ingest keep TIGER land/water area? → A: **Yes** — persist `ALAND` / `AWATER` (m²) on each `census_tracts` row. TIGER already ships these attributes; do not drop them on transform. Building footprints remain OUT OF SCOPE.
- Q: What is a “water-only” tract for downstream products? → A: **`ALAND = 0`** (Census land area). Tract codes in the 9900–9998 range may corroborate but MUST NOT be the sole filter. ACS population filters are OUT OF SCOPE for this amendment (may be revisited later).
- Q: Existing DBs without land/water columns? → A: Additive migration + census re-ingest (force/re-run for affected counties) so rows refresh; no wipe of scores required.

### Canonical test addresses (fixture)

Documented fixture for verification (order stable; Bentonville required):

1. 609 SE Jamaica Dr, Bentonville, AR 72712
2. 233 S Wacker Dr, Chicago, IL 60606
3. 350 5th Ave, New York, NY 10118
4. 98 San Jacinto Blvd, Austin, TX 78701
5. 400 Broad St, Seattle, WA 98109
6. 1001 Brickell Bay Dr, Miami, FL 33131
7. 1700 Broadway, Denver, CO 80202
8. 191 Peachtree St NE, Atlanta, GA 30303
9. 1 Market St, San Francisco, CA 94105
10. 2 N Central Ave, Phoenix, AZ 85004

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run EPA air quality ingestion locally (Priority: P1)

An operator (or developer) starts the local database, runs the EPA air quality ingestion job once for the **fixture-scoped** geography set, and sees normalized daily air quality readings stored for the counties those test addresses need so environment scoring has real source data.

**Why this priority**: EPA is the designed first worker (simplest authenticated source). Without county-level air quality in the system of record, environment scores cannot leave placeholders grounded in live ingestion.

**Independent Test**: With required EPA credentials configured and the local database running, execute the EPA worker once for the fixture geography set; confirm rows appear for counties covering the fixture addresses and a re-run does not create duplicates for the same county, parameter, and date.

**Acceptance Scenarios**:

1. **Given** a healthy local database and valid EPA source credentials, **When** the operator runs the EPA ingestion job for the fixture geography set, **Then** air quality readings for those counties are stored with county identity, parameter, date, AQI value, and category when the source provides them.
2. **Given** readings already exist for a county, parameter, and date, **When** the operator runs the EPA job again for the same day, **Then** existing rows are updated rather than duplicated.
3. **Given** a source response that includes malformed or incomplete records, **When** ingestion runs, **Then** valid records still load and bad records are skipped without aborting the entire job (with observable skip/error logging).
4. **Given** missing or invalid EPA credentials, **When** the operator runs the job, **Then** the job fails clearly with an actionable message and does not write partial “success” state for that run.

---

### User Story 2 - Load census tract boundaries (Priority: P1)

An operator runs the census tract boundary ingestion job for the **fixture-scoped** geography set and ends up with tract geographies sufficient to locate each of the 10 test addresses and support spatial joins for scoring.

**Why this priority**: Tract geometry is the spatial backbone for NeighborhoodInsight scores; healthcare distance and tract-level scoring depend on it.

**Independent Test**: Run census tract ingestion for the fixture geography set against the local PostGIS-enabled database; confirm each fixture address can be matched to a tract with geometry usable for distance/centroid queries.

**Acceptance Scenarios**:

1. **Given** a healthy local database with spatial support, **When** the operator runs the census tract ingestion job for the fixture geography set, **Then** tract records covering the fixture addresses are stored with geographic IDs (state, county, tract components), polygon geometry in a consistent geographic coordinate system, and Census TIGER **land area** and **water area** (square meters) for each tract.
2. **Given** a failure downloading or parsing one unit of the fixture geography set, **When** ingestion continues for remaining units, **Then** successful units still load and the failure is reported without silently marking the whole run successful.
3. **Given** tracts already loaded for a fixture geography unit, **When** the operator re-runs ingestion, **Then** the job ends in a defined, documented reload behavior (no uncontrolled duplicate tracts for the same geographic ID) and land/water area fields refresh from TIGER when present.
4. **Given** this feature’s local path, **When** workers run, **Then** they MUST NOT require or claim a full 50-state / national ingest.

---

### User Story 3 - Load hospital quality locations (Priority: P2)

An operator runs the hospital (CMS) ingestion job and stores provider locations with ratings and emergency-service flags so healthcare scoring can use nearest facilities.

**Why this priority**: Healthcare is a primary score dimension; hospital locations and star ratings are the first designed healthcare inputs after geometry exists.

**Independent Test**: Run CMS hospital ingestion once; confirm hospitals persist with provider IDs, coordinates/geometry, and ratings; re-run updates ratings without creating duplicate providers.

**Acceptance Scenarios**:

1. **Given** a healthy local database, **When** the operator runs hospital ingestion, **Then** hospitals are stored with unique provider identity, location, and overall rating when available.
2. **Given** a hospital already stored, **When** ingestion runs again, **Then** mutable fields such as star rating refresh and the provider is not duplicated.
3. **Given** a provider without usable coordinates or with “not available” rating text, **When** records are processed, **Then** the job still completes and omits or nulls invalid fields without corrupting other providers.

---

### User Story 4 - Compute healthcare and environment scores (Priority: P2)

After raw EPA, census tract, and hospital data are present for the fixture counties, an operator runs the score computation job and obtains stored overall and dimension scores for **every census tract in each county that contains a canonical test address** (not merely the single tract of each street address).

**Why this priority**: Constitution requires precomputed scores from ingested data; county-wide tract scores give enough spatial neighborhood context for healthcare distance and environment inputs, and enable reports for the fixture addresses (and other points in those counties once scores exist).

**Independent Test**: With tracts, hospitals, and recent AQI rows available for the fixture counties, run score computation; verify healthcare and environment scores plus overall score are stored for all tracts in those counties, with other dimensions filled by documented placeholders until their source workers exist.

**Acceptance Scenarios**:

1. **Given** tract geometry, hospitals with emergency services, and recent county AQI readings for a fixture county, **When** score computation runs for a tract in that county, **Then** healthcare and environment scores (0–100) and a weighted overall score are stored with a data vintage label.
2. **Given** a tract with no nearby hospital data, **When** healthcare score is computed, **Then** a documented default (not a crash) is used so the overall score can still be produced.
3. **Given** scores already stored for a tract and vintage, **When** computation runs again, **Then** scores update in place rather than creating duplicate vintage rows.
4. **Given** a dimension’s source worker is not yet complete in the current phase, **When** scores are written, **Then** that dimension uses an explicit documented placeholder and does not block other dimensions already implemented (healthcare, environment, and any later-delivered dimensions for that phase).
5. **Given** the 10 canonical test addresses, **When** scoring completes for this feature’s local path, **Then** every fixture address resolves to a tract that has a stored neighborhood score for the active vintage, and **every other tract in those same counties** also has a stored score for that vintage.

---

### User Story 5 - Search fixture addresses and view live score reports in local/dev (Priority: P1)

An operator runs the local/dev stack after workers have populated data, searches one of the canonical test addresses (including Bentonville), and opens a score report that reflects computed neighborhood scores from the database—not a static mock that ignores ingested data.

**Why this priority**: The agreed verification plan is end-to-end: ingest → score → see it in the app. Without this, workers cannot be signed off as “up and running” for product use.

**Independent Test**: With DB populated for the fixture set, use the local web UI address search for at least three fixture addresses (must include Bentonville) and confirm each report shows overall and dimension scores consistent with stored neighborhood scores for that address’s tract.

**Acceptance Scenarios**:

1. **Given** the local/dev app and a populated fixture dataset, **When** the operator searches `609 SE Jamaica Dr, Bentonville, AR`, **Then** they can open a score report whose overall and dimension values match the stored scores for that address’s census tract.
2. **Given** the same prepared environment, **When** the operator searches at least two other canonical fixture addresses, **Then** each yields a report backed by stored scores (not an unrelated hard-coded demo destination).
3. **Given** a report is shown after a phase completes, **When** a dimension has been delivered by that phase (e.g. safety after the safety slice), **Then** the report shows the stored non-placeholder score for that dimension; undelivered dimensions remain visible with the same placeholder-backed values written by the score job (reports must not invent a second mock set).
4. **Given** an address outside the prepared fixture geographies with no stored score, **When** the operator looks it up, **Then** behavior is defined and user-visible (clear empty/unavailable state—not a silent wrong mock score presented as real).

---

### User Story 6 - Safety ingestion and scoring (first reopen phase) (Priority: P1)

An operator runs the safety (crime) ingestion job for the fixture geography set, re-runs scoring, and sees **non-placeholder safety scores** for tracts in fixture counties; education and economic may still use documented placeholders until their later phases.

**Why this priority**: Safety is 25% of the overall weight and is the first agreed reopen phase after healthcare/environment.

**Independent Test**: With safety credentials/config present, run the safety worker and scoring; confirm safety scores and provenance differ from the prior placeholder constant for fixture-county tracts; live Bentonville report reflects the new safety value.

**Acceptance Scenarios**:

1. **Given** a healthy local database and required safety-source credentials, **When** the operator runs safety ingestion for the fixture geography set, **Then** crime/safety source rows needed for scoring those counties are stored with upsert-safe keys.
2. **Given** safety raw data is present, **When** score computation runs, **Then** `safety_score` is computed from ingested data (not the silent placeholder) for fixture-county tracts, with `score_sources.safety` provenance populated.
3. **Given** Docker and the local database, **When** an operator follows documented worker run commands, **Then** each implemented worker (including safety) can be executed as a one-off job; missing secrets fail with an actionable message.
4. **Given** education and economic phases are not yet delivered, **When** scores are written, **Then** those two dimensions may remain on documented placeholders without blocking safety.

---

### User Story 7 - Education ingestion and scoring (second reopen phase) (Priority: P2)

After the safety slice, an operator runs **both** NCES and Urban Institute school-related ingest paths for fixture geographies, re-runs scoring, and sees **non-placeholder education scores** for fixture-county tracts that combine complementary fields from both sources. Economic may still use placeholders.

**Independent Test**: Run NCES + Urban education workers (or a documented dual-source suite) + scoring; education scores and `score_sources.education` leave the prior placeholder and identify both contributors; Bentonville report updates education accordingly.

**Acceptance Scenarios**:

1. **Given** fixture counties and reachable NCES + Urban sources, **When** education ingestion runs, **Then** school/directory rows from NCES and statistical fields from Urban needed for scoring those geographies are stored with upsert-safe keys.
2. **Given** both source tables are populated, **When** score computation runs, **Then** `education_score` uses complementary fields from both (documented in planning—e.g. NCES location/identity + Urban outcome/quality stats) and `score_sources.education` records both contributors (or a composed provenance object).
3. **Given** one of the two education sources fails for a fixture unit, **When** ingestion/scoring runs, **Then** behavior is documented (partial score, defer, or fail the phase)—must not silently reuse the old global placeholder while claiming dual-source success.

### User Story 8 - Economic ingestion and scoring (third reopen phase) (Priority: P2)

After education, an operator runs **Census ACS** and **BLS LAUS** ingest for fixture geographies, re-runs scoring, and sees **non-placeholder economic scores** for fixture-county tracts that combine complementary ACS and LAUS signals so all five dimensions are source-backed for the fixture set.

**Independent Test**: Run ACS + BLS economic workers (or documented dual-source suite) + scoring; economic scores and `score_sources.economic` leave the prior placeholder and identify both contributors; overall scores reflect all published weights with real dimension inputs for fixture counties.

**Acceptance Scenarios**:

1. **Given** fixture counties and reachable ACS + BLS LAUS sources, **When** economic ingestion runs, **Then** indicator rows for those geographies are stored with upsert-safe keys from both sources.
2. **Given** both source tables are populated, **When** score computation runs, **Then** `economic_score` uses complementary ACS and LAUS fields (documented in planning) and `score_sources.economic` records both contributors.
3. **Given** private listing-market sources (Zillow/Redfin), **When** this feature runs, **Then** they are not required and remain out of scope.

---

### Edge Cases

- Upstream government APIs/files rate-limit, time out, or return empty payloads for a fixture geography unit/page — job reports partial progress and does not claim full fixture-set success.
- Re-running a fixture-scoped ingest mid-failure must be safe (upsert / defined reload), not leave undetectable half-duplicates.
- AQI values missing or non-numeric for some monitors — those rows skipped; other rows load.
- Hospital rating strings that are not numeric (“Not Available”) — stored as null rating, not job failure.
- Score computation for a tract whose county has no AQI in the last 30 days — documented environment default / fallback.
- Worker starts without `DATABASE_URL` — fails fast with a clear configuration error.
- Fixture-scoped loads that still pull oversized files (e.g., whole-state tract files for a fixture state) — job may take a while but must remain restartable and observable; operators are not expected to wait on a 50-state run.
- A fixture address fails geocoding or tract match — operator sees a clear failure for that address; other fixture addresses still work.
- Operator searches a non-fixture address with no stored score — must not display mock scores as if they were live ingested results.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a shared ingestion worker contract (fetch → transform → load → timed logging) that each source worker follows.
- **FR-002**: System MUST ingest daily EPA air quality summaries into durable county-level readings for the **fixture-scoped** geography set, keyed so the same county, parameter, and local date cannot duplicate.
- **FR-002a**: Environment scoring MUST prefer EPA AQS county aggregates when worthy (documented min distinct monitor-days in the scoring window); when EPA is missing or unworthy, MUST fall back to Open-Meteo modeled US AQI (or a documented numeric default if both fail). Score rows MUST persist machine-readable dimension provenance (`score_sources`) including the environment `source_id`.
- **FR-003**: System MUST support configuring EPA source credentials via environment/secret configuration (never committed secrets).
- **FR-004**: System MUST ingest census tract boundaries with geographic identifiers and polygon geometry suitable for spatial distance and centroid queries, limited to the **fixture-scoped** geography set required by the canonical test addresses (not a 50-state national load).
- **FR-004a**: Census tract ingestion MUST persist Census TIGER **land area** (`ALAND`) and **water area** (`AWATER`) in square meters on each tract row (nullable only when the source row lacks the attribute). These fields enable downstream products (e.g. Discover) to treat **water-only** tracts (`ALAND = 0`) differently from inhabited land tracts. Building footprints are OUT OF SCOPE.
- **FR-005**: System MUST ingest CMS hospital records including provider identity, location, emergency-services flag, and overall star rating when available, upserting on provider identity, limited to facilities usable for scoring the fixture geographies (not a national hospital warehouse as a success requirement).
- **FR-006**: System MUST provide a score computation job that reads ingested raw tables and writes neighborhood scores for healthcare and environment (0–100), plus an overall score using the product’s published dimension weights (healthcare 25%, safety 25%, education 20%, environment 15%, economic 15%). For this feature’s local path, the job MUST score **all census tracts in each county that contains a canonical test address** (county-scoped), not only the single tract of each street address and not whole-state/national tract sets.
- **FR-007**: System MUST use documented placeholder scores for any of safety, education, and economic that are **not yet delivered** in the current phase. After a dimension’s source worker and scoring path ship in a closeable slice, that dimension MUST NOT remain on a silent placeholder for fixture-county tracts.
- **FR-007a**: Delivery of the three unfinished dimensions MUST be **phased on this feature branch**: (1) **safety**, (2) **education**, (3) **economic**. Each phase is independently testable; later phases MUST NOT be required to mark an earlier phase’s slice complete.
- **FR-008**: System MUST implement **fixture-scoped FBI CDE chart/agency ingestion** (replacing the FBI skeleton) as the first reopen phase, using `FBI_CDE_API_KEY`, so safety scores can leave placeholders. Education and economic workers follow in later phases on the same branch.
- **FR-008a**: Safety scoring MUST derive `safety_score` from ingested CDE offense/benchmark fields for agencies serving fixture counties (documented formula in planning), persist `score_sources.safety` with `source_id` identifying FBI CDE, and fail clearly when `FBI_CDE_API_KEY` is missing.
- **FR-008b**: Education phase MUST ingest **both** NCES (government school directory/identity) and Urban Institute school statistics for fixture geographies. Planning MUST compare available fields and define a scoring formula that uses **complementary** signals from each (avoid double-counting the same metric). `score_sources.education` MUST record both contributors.
- **FR-008c**: Economic phase MUST ingest **Census ACS** and **BLS LAUS** for fixture geographies. Planning MUST compare available fields and define a scoring formula that uses **complementary** signals from each. `score_sources.economic` MUST record both contributors. Zillow/Redfin MUST remain out of scope.
- **FR-009**: System MUST allow operators to run each implemented worker as a one-off job against the local Docker database using project-documented commands (including Docker Compose worker profiles where applicable).
- **FR-010**: System MUST create or apply the durable schemas needed for EPA readings, census tracts, hospitals, crime stats (FBI CDE), schools/education tables (NCES + Urban), economic indicator tables (when that phase lands), and neighborhood scores as workers come online.
- **FR-011**: System MUST log per-unit progress (e.g., per state or per page batch) and final totals so operators can verify runs.
- **FR-012**: Scheduled cloud execution (Container Apps Jobs or equivalent production schedulers) MUST be out of scope for this feature; a later feature will add production scheduling once local workers are proven.
- **FR-013**: FEMA and Zillow (or other later-priority sources listed after FBI in the design priority order) MUST be out of scope for this feature unless a later clarification explicitly pulls one in. **Safety, education, and economic source workers are in scope for this reopened feature** (delivery vehicle: same `002` branch/spec—not a new Spec Kit feature).
- **FR-014**: For the local/dev stack, the address lookup and score report path MUST serve neighborhood scores from the system of record for addresses that have stored scores (including all canonical fixture addresses after a successful worker prep). Mock-only reports MUST NOT be presented as live results when stored scores exist.
- **FR-015**: System MUST document and retain a canonical fixture of exactly 10 street addresses (listed in Clarifications), including `609 SE Jamaica Dr, Bentonville, AR 72712`, used as the required local verification set.
- **FR-016**: After the documented local worker prep path, each of the 10 fixture addresses MUST map to a census tract that has a stored neighborhood score for the active data vintage, and every tract in those fixture counties MUST also have a stored score for that vintage.
- **FR-017**: When a lookup/report is requested for an address with no stored score, the system MUST return a clear unavailable/empty outcome rather than fabricating a mock score presented as ingested data. Addresses that geocode into a scored fixture county MUST be eligible for live reports when their tract score exists (not limited to the exact fixture street strings).
- **FR-018**: Local worker verification for this feature MUST be **fixture-county-scoped** — geographies derived from the counties of the 10 canonical test addresses. Full national (50-state) or whole-state-unless-needed ingest/scoring is explicitly out of scope for this feature’s acceptance.

### Key Entities

- **Air quality reading**: County-day observation for a pollutant parameter, with AQI and category.
- **Census tract**: Geographic polygon with a stable national GEOID and state/county/tract components, plus TIGER land/water area (m²) when ingested.
- **Hospital**: CMS-identified facility with location, optional star rating, and emergency-services flag.
- **Crime stats (FBI CDE)**: Agency-oriented offense/benchmark aggregates from the FBI Crime Data Explorer chart API, keyed for upsert and joined into safety scoring for fixture counties.
- **Neighborhood score**: Per-tract healthcare, safety, environment, education, economic, and overall scores for a data vintage, computed from raw ingested data (with placeholders where sources are missing for not-yet-delivered phases).
- **School (NCES)**: Government school directory/identity records (and related geography/attributes) for fixture-scoped education ingest.
- **School statistics (Urban Institute)**: Complementary school/district statistics joined into education scoring alongside NCES identity/location (not a substitute for NCES).
- **ACS economic indicators**: Census American Community Survey measures (e.g. income/poverty/employment mix) at fixture-relevant geography for the economic phase.
- **BLS LAUS indicators**: Local Area Unemployment Statistics complementary labor signals joined into economic scoring alongside ACS.
- **Canonical test address**: One of the 10 fixed verification addresses; used to prove geocode → tract → score → report end to end.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete a successful EPA ingestion run against the local database in one documented command path, and afterwards AQI readings exist for counties covering the fixture addresses.
- **SC-002**: After census ingestion for the agreed geography set, each of the 10 fixture addresses can be matched to a tract with valid geometry, and fixture-county tract rows include populated land/water area fields from TIGER (or an explicit null only when the source omitted them).
- **SC-003**: After hospital ingestion, hospitals usable for nearest-facility scoring exist for each fixture geography (at least one emergency-capable facility within a documented search radius, or the healthcare default path is exercised and documented per address).
- **SC-004**: Score computation produces healthcare, environment, and overall scores for **100%** of census tracts in the counties containing the 10 fixture addresses (verified by count of tracts in those counties vs scored rows) without manual data patching.
- **SC-005**: Re-running EPA and hospital jobs twice in succession results in zero duplicate natural keys (county+parameter+date; provider id).
- **SC-006**: A new engineer can complete the documented local prep path (workers + verify Bentonville report in the app) using only project docs within 45 minutes of active setup time (excluding source credential signup and bulk download wait time).
- **SC-007**: Each implemented worker for the current phase (EPA, census, CMS, scoring, plus safety/education/economic as each phase lands) completes at least one successful local one-off run against the Docker database with progress logs and a clear completion message.
- **SC-009**: After the safety phase, fixture-county tracts have non-placeholder `safety_score` values with populated `score_sources.safety` (Bentonville report matches DB).
- **SC-010**: After the education phase, fixture-county tracts have non-placeholder `education_score` with `score_sources.education` that reflects **both** NCES and Urban Institute contributions.
- **SC-011**: After the economic phase, fixture-county tracts have non-placeholder `economic_score` with `score_sources.economic` that reflects **both** Census ACS and BLS LAUS contributions.
- **SC-008**: In the local/dev web app, searching Bentonville plus at least two other fixture addresses opens score reports whose overall scores match the stored neighborhood scores for those tracts (±0 difference after rounding rules documented by the API).

## Assumptions

- Design doc `docs/nhiq-design-main/07-data-ingestion-workers.md` is the product/tech intent for baseline order: EPA → Census → CMS → FBI → scoring; this reopen extends scoring inputs with FBI CDE safety, NCES+Urban education, and ACS+BLS economic (still FEMA/Zillow deferred).
- This feature is **local-only** for execution environment: success means workers run against the local Docker database and the local/dev app can display results. Azure Container Apps Jobs / production schedules remain deferred.
- Local “up and running” uses the existing Docker Compose database (PostGIS) and worker profiles; operators may also run workers in a Python environment when documented.
- Verification centers on the **10 canonical test addresses** in Clarifications; workers load **fixture-county-scoped** geographies (tracts, AQI, and hospitals needed for those counties). Score job covers all tracts in those counties. No national- or whole-state-as-acceptance-bar runs in this feature (state-sized source files may still be downloaded if that is how a source is packaged, then filtered to fixture counties).
- Other addresses that land in a scored fixture county should work in the local/dev report path once their tract is scored; exact fixture street strings are the required verification set, not an exclusive allowlist.
- EPA source registration (email + key) is available to the operator; without it, EPA runs are expected to fail fast (not silently skip).
- Reopen phases on this branch: **safety (FBI CDE) → education (NCES + Urban Institute) → economic (Census ACS + BLS LAUS)**. The former FBI skeleton is upgraded to a real CDE worker in the safety phase. Education and economic scoring each combine complementary dual-source fields after planners explore both catalogs. Zillow/Redfin stay out of scope.
- Score weight table matches the design doc; placeholder constants for **not-yet-delivered** dimensions are acceptable and must be documented; the report UI may show those placeholders as part of the live score record until that phase ships.
- Live lookup/report against stored scores for fixture addresses is **in scope** for this feature (local/dev only).
- Redis cache invalidation after score writes SHOULD occur when the API serves live scores so stale mock/cached payloads cannot override fresh scores.
- Fixture list ZIP codes and street forms may be normalized by geocoding; Bentonville address text is authoritative as given by the product owner.
