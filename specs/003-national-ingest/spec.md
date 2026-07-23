# Feature Specification: National Ingest

**Feature Branch**: `003-national-ingest`

**Created**: 2026-07-15

**Status**: Implemented (docs consolidation)

**Consolidation**: Absorbs former Spec Kit features `005-national-report-detail` (2026-07-16) and `007-national-ingest-redesign` (2026-07-17). This document is the current-truth national ops contract. Local worker formulas, fixture addresses, and live score API semantics remain in [`specs/002-data-ingestion-workers`](../002-data-ingestion-workers/). Report expand UI/formulas remain in [`specs/004-report-subscores`](../004-report-subscores/).

**Input**: National US ingest for ops: load all counties in 50 states plus DC; explicit state batches and DB checkpoints; inventory-driven orchestration; report-detail (hazard, timely care, ACS population, expand `score_detail`) as first-class gaps; accurate national progress against the full county registry; continuous unattended completion via one GitHub Action or one PowerShell command with bulk/wide fetches; preserve smoke and metro_10; Azure smoke gate before trusting expand on production.

## Clarifications

### Session 2026-07-16 (report-detail; former 005)

- Q: Must National Ingest pick already-ingested states that only lack report-detail, and fill only new gaps without force? → A: Yes. For a selected state it must only collect missing report-detail inputs and refresh expand scores—never require force-update of finished base workers.
- Q: When max_states mixes virgin states and base-complete states missing only report-detail, what selection priority? → A: Prefer base-complete states that still lack report-detail first; then virgin / other gap states.
- Q: Where must the smoke gate pass before National Ingest? → A: Azure / production DB smoke using the same jobs path as national must pass; local Compose alone is not sufficient.
- Q: Does national report-detail own a separate API/web deploy workstream? → A: No. Operator merges to `dev`, promotes `dev` → `master` (production Deploy ships expand-capable API/web), then Azure smoke.

### Session 2026-07-15 / 2026-07-17 (orchestration model)

- Original 003 assumption “a single multi-day unattended run without re-dispatch is OUT OF SCOPE” is **superseded** by continuous mode (GHA self-chain / PowerShell loop). Bounded max_states / filter / force runs remain available for diagnostics.
- Status denominators that used only loaded tracts for scoring are **superseded**: scoring done is county-grain against full `geo_counties` (fbi_cde + non-empty `score_detail`).

### Session 2026-07-23 (census land/water consistency)

- Q: Does national census ingest need the same TIGER land/water fields as local 002? → A: **Yes** — national `worker-census` uses the same `census_tracts` schema and upsert path. Persist `aland`/`awater` for every loaded tract under smoke, metro_10, and national scopes. Do not invent a parallel national-only geometry table.
- Q: Does water-only exclusion change national completeness / scoring grain? → A: **No** — tracts with `aland = 0` remain in `census_tracts` (county coverage, FEMA join, scoring still apply). Discover (008) excludes them from **map fill and city snapshot**; national status % is unchanged.
- Q: Force / re-ingest? → A: After schema migration, counties already marked census-done still lack `aland`/`awater` until force or a one-time backfill re-run; document that for ops (Azure/Compose).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scopes and county registry (Priority: P1)

An ops operator bootstraps a national county registry for 50 states + DC, then runs workers under `smoke`, `metro_10`, or `national` scopes. Smoke and metro keep their small denominators; national membership and FBI points come from the registry. Territories are not required for v1 success but the registry design allows adding them later by configuration.

**Why this priority**: Without a stable universe and scope model, batching, status %, and continuous completion cannot be honest.

**Independent Test**: Load `geo_counties` for included jurisdictions; run status under metro_10 and national; confirm metro still measures ten fixture counties only while national uses the full registry count.

**Acceptance Scenarios**:

1. **Given** the national registry is loaded for 50+DC, **When** national status is refreshed, **Then** denominators use that county universe (territories not required).
2. **Given** smoke or metro_10 scope, **When** workers and status run, **Then** they use existing small geography sets and do not require a national state batch.
3. **Given** national registry data exists, **When** metro_10 status is refreshed, **Then** metro completion still measures against the ten fixture counties only.
4. **Given** an empty or incomplete national registry (included state FIPS count ≠ 51), **When** continuous/status claims national progress, **Then** the system fails closed with a clear message—never treats empty registry as complete.

---

### User Story 2 - State batch, checkpoints, and FBI centroids (Priority: P1)

An ops operator supplies an explicit state batch under national scope, runs ingest through scoring, and can restart mid-batch without redoing finished units. Safety ingest uses per-county geographic points (centroids), not fixture street addresses, for non-fixture counties.

**Why this priority**: ACA timeouts and long runs require phased batches and durable skip-done; fixture lat/lon cannot scale nationally.

**Independent Test**: Run a small non-fixture state batch end-to-end; interrupt and restart a worker; confirm skip counts; confirm FBI agency selection used a county centroid for a non-fixture county. National without a batch fails in under 30 seconds.

**Acceptance Scenarios**:

1. **Given** national scope and an explicit state batch, **When** the worker pipeline runs, **Then** only counties in those states are targeted and data is stored without requiring all other states first.
2. **Given** national scope without an explicit state batch, **When** a national worker starts, **Then** the job refuses with a clear message (no accidental all-states run).
3. **Given** some counties already have complete stored results, **When** that worker restarts with the same batch and force off, **Then** it skips those counties using the database as checkpoint truth.
4. **Given** a county in the national universe with a known centroid, **When** safety ingest runs for a batch containing that county, **Then** agency selection uses that county’s point rather than a fixture street address.
5. **Given** partial safety coverage, **When** the job finishes, **Then** status % reflects actual coverage (no fake 100%).

---

### User Story 3 - Report-detail completeness without force (Priority: P1)

National inventory treats report-detail gaps as real work: FEMA NRI hazards, CMS Timely/ER wait, ACS `total_population` for safety rates, and non-empty expand `score_detail`. States that already finished base ingest remain selectable. Selection prefers base-complete report-detail-gap states (class A) before virgin/other gaps (class B). Force is never required solely to unlock report-detail. Production schema for these stores is additive (no wipe).

**Why this priority**: Several states may already hold “old” complete base data; without report-detail as inventory gaps they would never get expand-ready inputs unless forced.

**Independent Test**: Seed base-complete states with empty report-detail plus virgin states; run with max_states=3 and no filters; confirm A-before-B selection and only report-detail stages + expand re-score run. ACS rows with null population remain ACS gaps.

**Acceptance Scenarios**:

1. **Given** additive report-detail schema applied on a populated DB, **When** score lookups run, **Then** existing scores remain intact and storage exists for hazard, timely measures, ACS population, and `score_detail`.
2. **Given** base-complete states missing only report-detail and virgin gap states, **When** a normal max_states run has no force/filter, **Then** the orchestrator prefers class A first, then class B.
3. **Given** a selected class-A state, **When** the orchestrator runs, **Then** only unfinished report-detail stages plus expand score refresh run—finished base workers stay skipped.
4. **Given** ACS rows exist but `total_population` is null, **When** inventory evaluates ACS, **Then** that unit remains a gap and a non-force ACS run backfills population.
5. **Given** counties whose expand detail is already populated for the active vintage, **When** scoring runs without force, **Then** those counties are skipped; empty-detail counties are scored.
6. **Given** hazard/timely already stored for active vintage, **When** those jobs re-run without force, **Then** identities skip or upsert idempotently with no duplicate-key corruption.

---

### User Story 4 - Honest national progress (Priority: P1)

An ops operator opens national status while only a minority of states are complete. Every job’s percentage uses the full 50+DC universe. Scoring is county-grain done (every tract has fbi_cde safety + non-empty `score_detail`) over national county count—not tracts÷loaded tracts. Excluded states still count in the denominator. Console snapshots stay Workbook-safe (metrics-only, &lt;8KB); full detail stays in Postgres. Mid-run pulses emit after each worker and every N units (default 15).

**Why this priority**: Inflated % makes continuous runs untrustworthy.

**Independent Test**: With a known subset of states complete, confirm scoring % ≈ completed counties ÷ ~3143; exclude a state and confirm denominator unchanged; confirm slim `INGEST_STATUS_SNAPSHOT` lines parse in Workbook KQL.

**Acceptance Scenarios**:

1. **Given** only a minority of states are complete, **When** national status refreshes, **Then** each job’s % uses the full national denominator.
2. **Given** scoring complete only in collected states, **When** scoring progress is shown, **Then** % ≈ completed counties ÷ total national counties.
3. **Given** the operator excludes chronically failing states from scheduling, **When** progress is viewed, **Then** excluded states still count against the national denominator.
4. **Given** a national-scope snapshot, **When** the console log is ingested by Log Analytics, **Then** JSON includes metrics only—no full FIPS/missing lists in the log line.
5. **Given** a county-loop worker processing more than N counties, **When** it runs, **Then** it emits a status snapshot at least every N units; status emit failure must not fail ingest.

---

### User Story 5 - Continuous nationwide completion (Priority: P1)

An ops operator starts national ingest once—GitHub Action with continuous mode (default) or one PowerShell command—and the system keeps selecting unfinished work until 50+DC required sources and scoring are complete (or the operator cancels). Cycles continue across platform time limits via GHA self-chain (max chain depth 50) or PowerShell loop. Bounded diagnostic runs remain available. Inventory starts only workers with gaps; force/filter lists stay exclusive (no gap padding).

**Why this priority**: Bounded ≤5-state manual nibbles cannot finish the nation in reasonable operator effort.

**Independent Test**: Start continuous mode against a DB with gaps spanning more states than one batch; confirm multi-cycle progress and eventual `orch_cycle_result=complete` (or clear handoff on budget). Bounded mode with continuous=false still ends after max_states.

**Acceptance Scenarios**:

1. **Given** unfinished national gaps across many states, **When** continuous National Ingest starts, **Then** the system schedules unfinished work repeatedly until inventory shows no required gaps for 50+DC.
2. **Given** a cycle hits a time budget with gaps remaining, **When** that cycle ends, **Then** exit code 2 / `more_work` triggers another cycle without a fresh manual click (until complete, cancel, or chain-depth stop).
3. **Given** continuous mode is running, **When** the operator watches Action/console logs, **Then** they see selected states/sources, cycle result, and approximate national progress.
4. **Given** the operator wants a bounded diagnostic run, **When** they disable continuous mode and set max-states/filter, **Then** only that bounded set is processed.
5. **Given** remaining gaps exist only on excluded states, **When** the cycle ends, **Then** it does **not** claim `complete` (blocked_excluded / hard fail).
6. **Given** Deploy pushes to master, **When** site Deploy runs, **Then** national ingest does not start automatically.

---

### User Story 6 - Bulk and wide collection (Priority: P1)

Sources that publish automatable national or per-state packages are collected that way. Hazard uses one national NRI tracts CSV zip; ACS uses state-wide `county:*`; Urban uses state `?fips=` with skip-done; FBI keeps per-county agency fidelity but caches state agency lists and may run counties concurrently; EPA/BLS prefer bulk files with API fallback. Wall-clock for comparable gap sets is at least 50% faster than the old max-5 sequential pattern.

**Why this priority**: Accurate continuous mode is insufficient if per-county remote loops never finish.

**Independent Test**: Multi-state batch finishes with far fewer upstream calls; required table shapes unchanged for scoring/report detail.

**Acceptance Scenarios**:

1. **Given** national hazard collection, **When** FEMA runs, **Then** it obtains the national package once and loads in-scope tracts without one remote query per county (ArcGIS fallback only if bulk fails as documented).
2. **Given** ACS for a state, **When** ACS runs, **Then** it fetches tract indicators state-wide (or equivalent), not one call per county.
3. **Given** Urban enrichment for a state, **When** it runs, **Then** it fetches by state and skips already-complete schools/districts.
4. **Given** FBI for many counties in a state, **When** it runs, **Then** shared state agency lists are not re-downloaded per county; counties may proceed concurrently within rate limits.
5. **Given** continuous nationwide completion criteria, **When** comparing to prior sequential max-5 orchestration, **Then** wall-clock for the same completeness is reduced by at least half.

---

### User Story 7 - Azure smoke gate before national expand trust (Priority: P1)

Before spending a national run for expand-ready reports, an operator promotes to `master`, applies report-detail schema if needed, ensures FEMA/CMS Timely ACA jobs and worker image are current, runs smoke-scope collection on Azure against the production database, and confirms the Bentonville expand report matches the known-good local/dev (004) experience. Local Compose alone does not clear the gate.

**Why this priority**: Prevents a costly wrong national run against real Azure wiring.

**Independent Test**: Follow promote → schema → Azure smoke checklist; open Bentonville on production; fail the gate if expand is wrong even if Compose looked fine.

**Acceptance Scenarios**:

1. **Given** promote + schema + Azure smoke fill completed, **When** the operator opens the smoke address on production, **Then** category boxes, sub-scores, and expand stats match the local/dev expand class of experience.
2. **Given** smoke hazard/timely succeeded, **When** Environment/Healthcare expand, **Then** hazard and ER wait appear when sources provided them.
3. **Given** smoke looks wrong, **When** the operator evaluates the gate, **Then** they do **not** start National Ingest until Azure/prod passes.

---

### User Story 8 - Ops controls: inventory, force, status, ARM (Priority: P2)

Operators use inventory-driven orchestration (gap-only ACA starts), exclusive `force_states` / `state_filter`, `state_exclude`, mid-run status, and ARM retries on PATCH/START. Workers always receive explicit `INGEST_FORCE` 0/1 so force cannot stick on the ACA job.

**Independent Test**: Force a complete state → only that state, all workers, `INGEST_FORCE=1`. Transient ARM 500 then success within retry budget does not fail the orchestrator.

**Acceptance Scenarios**:

1. **Given** worker W complete for state S, **When** orchestrator runs for S without force, **Then** it does not start W for S.
2. **Given** `force_states=S`, **When** the orchestrator runs, **Then** only S is queued (no gap padding) and all pipeline workers run with force.
3. **Given** Azure ARM returns 500 on PATCH, **When** a subsequent retry succeeds, **Then** the orchestrator continues.

---

### Edge Cases

- Unknown / non-included state FIPS in batch → fail clearly before fetch work.
- Territory FIPS before enabled → reject or ignore with clear log until included set updated.
- Census geography with no usable centroid → safety skips county with logged reason; status stays honest.
- Upstream rate limits mid-batch → incomplete exit; restart resumes via checkpoints (no wipe).
- Empty inventory for selected states → orchestrator exits successfully without starting jobs (may refresh status)—unless forced; continuous mode treats true nation-clear as exit 0.
- GitHub Actions times out while Azure orchestrator still running → re-dispatch / chain continues from DB inventory.
- `force_states` set → only forced FIPS (capped); no padding. `state_filter` alone → only gaps within filter.
- Production has base data but no report-detail tables → additive schema only; no truncate.
- Timely-care source returns only aggregates → hospital wait unavailable; do not invent facility wait.
- Hazard missing for a tract → Environment still shows air quality; hazard unavailable.
- Bulk file URL/schema changes upstream → clear error (or documented secondary fallback); never silently mark nation complete.
- Gaps only on excluded states → not `complete`.
- Chain depth exceeded with work remaining → stop auto-chain with clear stop condition.
- Worker image older than report-detail/bulk redesign → docs require current image before smoke/national.

## Requirements *(mandatory)*

### Functional Requirements

#### Universe, scopes, batch, checkpoints

- **FR-001**: System MUST define a national county universe as all counties in the 50 US states plus DC for v1 completion denominators.
- **FR-002**: System MUST keep an extensible jurisdiction/registry design so US territories can be added later by configuration without redesigning national ingest.
- **FR-003**: System MUST NOT require territories for national v1 success criteria.
- **FR-004**: System MUST require an explicit state batch for national worker runs; empty batch under national scope MUST be rejected with a clear operator-facing message.
- **FR-005**: System MUST limit each national worker run to counties in the supplied state batch (orchestrator may set multi-state batches).
- **FR-006**: Every national-capable ingest and scoring worker MUST checkpoint progress such that a restart with the same batch skips units already successfully stored, using durable database contents as the source of truth.
- **FR-006a**: National census ingest MUST persist TIGER land area and water area (`aland` / `awater`, m²) on `census_tracts` consistently with [`002-data-ingestion-workers`](../002-data-ingestion-workers/) FR-004a. Checkpoint “census done” remains ≥1 tract row per county; land/water fields MUST be present after a fresh or forced census run for that county. Water-only tracts (`aland = 0`) MUST still be stored (not deleted) so county and report-detail coverage stay complete.
- **FR-007**: Checkpoint grain MUST be at least county for county-scoped work; state-scoped source pulls MAY checkpoint at state when that matches the source’s natural unit.
- **FR-008**: Safety ingest under national scope MUST select agencies using a per-county geographic point derived from authoritative geography (e.g. county centroid), not the metro fixture street-address list.
- **FR-009**: Safety ingest MUST continue to upsert/checkpoint per county and MUST report honest incomplete coverage when some counties fail.
- **FR-010**: Smoke and metro_10 scopes MUST remain supported with their existing small denominators and MUST NOT require a national state batch or continuous nationwide mode.
- **FR-011**: National ingest MUST use idempotent upserts; operators MUST NOT need to truncate tables to resume or re-run a batch.

#### Status and observability

- **FR-012**: National ingest status MUST compute real per-worker completion percentages against the full 50+DC county universe (or the documented grain for that job that maps to that universe)—not a stub and not “only loaded tracts” for scoring.
- **FR-013**: Scoring progress MUST count done at county grain: every tract in the county has required safety provenance (`fbi_cde`) and non-empty `score_detail` for the active vintage; denominator MUST be national `geo_counties` count.
- **FR-014**: Excluding states from scheduling MUST NOT redefine the national denominator unless jurisdictions are removed from the included universe by a separate product decision.
- **FR-015**: Empty or incomplete `geo_counties` for included 50+DC MUST fail closed for national continuous/status success (clear error; never `orch_cycle_result=complete`).
- **FR-016**: Operators MUST be able to refresh national progress via the existing ops status path (snapshot + Workbook).
- **FR-017**: The orchestrator MUST emit a national status snapshot after each worker completes; county/unit-loop workers MUST emit every N units (default 15); status emit failures MUST NOT fail the ingest job.
- **FR-018**: Console `INGEST_STATUS_SNAPSHOT` MUST be Workbook-safe metrics-only (&lt;8KB); full detail MUST remain in Postgres `ingest_status_snapshot`.
- **FR-019**: Status/progress tooling MUST include `fema` and `cms_timely` alongside other national jobs.

#### Inventory, orchestrator, force

- **FR-020**: System MUST provide an inventory of missing work per ingest/scoring worker against the national universe (county grain; CMS / CMS Timely at state grain; scoring per fbi_cde + `score_detail` rule).
- **FR-021**: Pipeline order MUST be: census → epa → cms → fbi → nces → urban → acs → bls → fema → cms_timely → scoring.
- **FR-022**: An orchestrator MUST start only ACA worker jobs for worker/state pairs that inventory marks incomplete (unless forced).
- **FR-023**: Operators MUST be able to trigger the orchestrator via manual GitHub Actions `workflow_dispatch` that does not run on ordinary master Deploy pushes.
- **FR-024**: Operators MUST be able to force re-ingest of specified state FIPS via Actions/`ORCH_FORCE_STATES`, running all pipeline workers with `INGEST_FORCE=1` (always set `0` when not forcing). When `ORCH_FORCE_STATES` is non-empty, process only that list (capped) with no gap padding.
- **FR-025**: When `INGEST_FORCE` is enabled, workers MUST NOT skip units already stored; they MUST re-process and upsert.
- **FR-026**: When `ORCH_STATE_FILTER` is non-empty and force is empty, process only gap states within that filter (capped); never states outside the filter.
- **FR-027**: Orchestrator ARM calls that patch or start ACA jobs MUST retry transient control-plane failures (HTTP 429/500/502/503) with exponential backoff.
- **FR-028**: Product in-app national progress UI and Slack/webhooks are OUT OF SCOPE for this feature.

#### Report-detail

- **FR-029**: Production database MUST support additive storage for tract hazard data, hospital timely-care measures, ACS total population for safety rate normalization, per-tract report expand detail, and census tract land/water area (`aland`/`awater`), without destroying existing ingest or score rows.
- **FR-030**: Operators MUST be able to apply those production schema updates using documented, idempotent steps (`infra/sql/007_report_detail.sql`, `infra/sql/010_census_tract_land_water.sql` when present, and related).
- **FR-031**: Hazard and timely-care collection MUST run for active national (and smoke/metro) geography scopes and persist with safe skip/upsert.
- **FR-032**: Inventory MUST treat a state/county as still having work when base ingest is complete but any report-detail stage is incomplete (hazard, timely-care, ACS total population, or empty expand detail). Force MUST NOT be required solely to unlock report-detail for previously gathered states.
- **FR-033**: When selecting states for a normal max_states / continuous gap-fill run (no force, no exclusive state filter), the orchestrator MUST prefer class A (base-complete, report-detail gaps) over class B (virgin/other), then fill remaining budget from other gap states.
- **FR-034**: When ACS indicator rows exist but total population is missing, inventory MUST count that as an incomplete ACS/report-detail gap.
- **FR-035**: Scoring MUST write expand detail for geographies that still lack it after new inputs are available, and MUST skip geographies that already have expand detail for the active vintage unless forced.
- **FR-036**: After promote to `master`, production Deploy has expand-capable API/web, schema is applied, and smoke-scope collection + score refresh have run via Azure jobs against the production database, a documented smoke address report on production MUST present the same class of expand experience as the accepted local/dev build. Local Compose success alone MUST NOT be treated as the National Ingest gate.
- **FR-037**: Production operator documentation MUST describe merge/promote → schema → Azure jobs/image → Azure/prod smoke gate → National Ingest.
- **FR-038**: Report API behavior for empty expand detail MUST remain graceful (limited data, no fabricated hazard/wait).

#### Continuous and bulk

- **FR-039**: Operators MUST be able to start continuous national ingest with a single GitHub Action dispatch and/or a single local PowerShell command that keeps working until nationwide required gaps are closed or the operator cancels.
- **FR-040**: Continuous mode MUST automatically continue across platform time limits (new cycle and/or new Action run) without requiring a fresh manual dispatch for each small state batch.
- **FR-041**: Continuous mode MUST remain optional; bounded runs via max-states / state filter / force / exclude MUST still work.
- **FR-042**: Continuous scheduling MUST batch multiple unfinished states into each source execution where safe (`ORCH_BATCH_STATES`).
- **FR-043**: Auto-chaining of continuous Action runs MUST enforce a maximum chain depth and surface a clear stop when exceeded with work remaining.
- **FR-044**: Where a source publishes an automatable national or wide (per-state) package that preserves required data meaning, national collection MUST use that package or wide query instead of one remote call per county/district when that reduces wall-clock substantially.
- **FR-045**: Hazard (FEMA NRI) national collection MUST obtain tract-level fields without one remote query per county when a national package is available.
- **FR-046**: ACS tract indicator collection for a state MUST use a state-wide fetch (or equivalent).
- **FR-047**: School directory enrichment MUST support state-scoped fetch and skip-done.
- **FR-048**: Safety (FBI CDE) MUST preserve per-county agency selection and offense-chart fidelity; MUST eliminate redundant re-fetch of the same state agency list per county; MAY process counties concurrently within documented rate limits.
- **FR-049**: Operators MUST be able to observe during a run: selected states/sources, whether the nation is complete or more work remains, and national progress percentages that satisfy FR-012/FR-013.

### Key Entities

- **Jurisdiction registry / National universe**: Included state FIPS (50+DC); counties in `geo_counties`.
- **County unit**: SSCCC identity plus geographic point for safety selection.
- **State batch**: Operator/orchestrator-supplied state FIPS list bounding one worker execution.
- **Checkpoint unit**: County (or state) with qualifying stored rows for a worker.
- **Gap inventory**: Per-worker incomplete counties/states from DB contents.
- **Class A / Class B states**: Report-detail backfill vs virgin/other gap states.
- **Report expand detail / Tract hazard / Hospital timely-care / Population for safety rates**: Report-detail stores (see data-model).
- **National status snapshot**: Per-worker done/total/% against the full national universe.
- **Orchestrator run / Continuous run / Bounded run**: Inventory → schedule → status; continuous loops until clear.
- **Force state set**: Operator-supplied FIPS that bypass skip-done for one run.
- **Smoke verification gate**: Azure/production-DB smoke check before trusting national expand.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete at least one non-fixture state end-to-end (ingest through scoring) using an explicit state batch, with national status % increasing for that state’s counties.
- **SC-002**: After interrupting a worker mid-batch and restarting (force off), at least 95% of already-complete counties in that batch are skipped.
- **SC-003**: National status denominator equals the county count for 50 states + DC; territories not required for “national complete” in v1.
- **SC-004**: Smoke and metro_10 status and fixture-scoped worker re-runs still succeed without a national state batch or continuous mode.
- **SC-005**: Attempting national scope with no state batch fails fast with an actionable message in under 30 seconds.
- **SC-006**: When inventory shows worker W complete for state S, an orchestrator run for S does not start W—unless S is in the force set.
- **SC-007**: A second orchestrator run after partial completion queues fewer (or equal) gap units than the first (force excepted).
- **SC-008**: With `force_states` set for a complete state, all pipeline workers for that state start in one run, and no other state FIPS are queued solely to fill `max_states`.
- **SC-009**: During a long county-loop worker, at least one mid-job `INGEST_STATUS_SNAPSHOT` appears when more than N counties are processed (N default 15).
- **SC-010**: A single transient ARM 500 on job PATCH does not fail the orchestrator if a subsequent retry succeeds within the retry budget.
- **SC-011**: A national-scope `INGEST_STATUS_SNAPSHOT` console line is under 8KB and Workbook KQL can parse `payload.jobs` for scope `national`.
- **SC-012**: After documented production schema updates, 100% of previously available score lookups for already-scored tracts continue to succeed (no data wipe).
- **SC-013**: After promote to `master` and a successful Azure/production-DB smoke gate, a reviewer finds matching expand capabilities vs local/dev for all five categories—and the operator is ready to start National Ingest.
- **SC-014**: For counties that already had complete base ingest, report-detail fill completes without force-rerunning finished base collections solely to unlock expand detail.
- **SC-015**: In a fixture with only previously gathered states lacking report-detail, max_states=3 with no force/filters selects from that set and completes only report-detail stages.
- **SC-016**: In a mixed A/B fixture, max_states=3 with no force/filters fills budget from class A before virgin states.
- **SC-017**: After report-detail collection for a prepared state, ≥95% of tracts in completed counties that have base scores also have non-empty expand detail (remaining gaps only where upstream inputs unavailable).
- **SC-018**: With only N of 51 jurisdictions fully complete, national scoring progress is within a few percentage points of N/51 (county-equivalent)—never falsely near “majority complete” from loaded-tract denominators.
- **SC-019**: An operator can start continuous national ingest with one Action click or one PowerShell command and leave it unattended until 50+DC required sources and scoring are complete, without manually re-dispatching for each ≤5-state nibble.
- **SC-020**: Wall-clock time to finish nationwide collection for the same completeness criteria is reduced by at least half versus the prior sequential per-state, per-source max-5 pattern.
- **SC-021**: After an interrupted continuous run, a restart skips already-complete units and only schedules remaining gaps for primary long-running sources.
- **SC-022**: During a continuous run, the operator can answer “what is running now?” and “is the nation done?” from Action log or console without Azure Portal as the only option.

## Assumptions

- Ops operators run jobs via Azure Container Apps Jobs, local Docker, inventory orchestrator (Actions → orchestrate), continuous GHA chain, or `scripts/national-ingest.ps1`.
- Authoritative county list and centroids come from Census TIGER (or equivalent) into `geo_counties`.
- Existing metro fixture addresses remain for smoke/metro_10 and local regression (002); they are not the national safety point source.
- Spec 002 fixture-only constraint is superseded for the national path; 002 behavior for metro/smoke is preserved.
- Local/dev report expand behavior from `004-report-subscores` is the visual/content reference for the Azure smoke gate.
- “Required” nationwide completeness means the national pipeline sources needed for neighborhood scores and report detail (including hazards and timely-care), not every future dataset.
- FBI CDE master bulk files that require manual browser download are out of scope; preserve per-county agency-based safety methodology.
- Azure SP / `AZURE_CREDENTIALS` patterns remain; inventory runs inside Azure so Postgres firewall rules are satisfied.
- National Ingest remains a separate operator action after the smoke gate; it does not auto-start on Deploy.
- Provider-level CMS Timely download skip (beyond vintage skip-done) may still re-fetch catalog pages; upserts remain idempotent.
- Secondary EPA/BLS bulk flags default on with API fallback.
