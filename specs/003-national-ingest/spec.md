# Feature Specification: National Ingest

**Feature Branch**: `003-national-ingest`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "National US ingest for ops: load all counties in 50 states plus DC (territories not in v1 but registry must make adding them a config change later). Phased by explicit state batch so jobs fit timeouts. Every worker must checkpoint and skip already-collected units on restart. FBI uses per-county geographic points not fixture addresses. National ingest status percent must be real for the Workbook. Keep smoke and metro_10 working. No product UI, no single unattended all-states run in v1."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run one state batch end-to-end (Priority: P1)

An ops operator selects an explicit state batch (one or more states within the 50+DC universe), runs the ingest workers in the documented order for that batch, then runs scoring, and sees durable geography and score data for counties in that batch. Progress on the national ingest status board increases accordingly.

**Why this priority**: National cannot finish in one timed job; a single successful state batch is the minimum viable national path and proves the universe, batching, and status denominator work together.

**Independent Test**: Configure a small non-fixture state batch, run census through scoring for that batch only, confirm counties in that state appear in stored geography/scores and national completion % rises while other states remain incomplete.

**Acceptance Scenarios**:

1. **Given** national scope is enabled and the operator supplies an explicit state batch, **When** they run the worker pipeline for that batch, **Then** only counties in those states are targeted for new work and data for those counties is stored without requiring all other states to run first.
2. **Given** a completed state batch, **When** the operator refreshes national ingest status, **Then** completion percentages use the full 50-state+DC county universe as the denominator and show higher done counts for workers that finished the batch.
3. **Given** national scope without an explicit state batch, **When** the operator attempts a national worker run, **Then** the job refuses to start with a clear message (no accidental all-states run).

---

### User Story 2 - Restart mid-batch without redoing finished work (Priority: P1)

An ops operator starts a state-batch worker job that is interrupted (timeout, hang, or manual stop). They restart the same worker with the same batch and the job continues from unfinished units, skipping counties (or equivalent units) already successfully stored.

**Why this priority**: National runs are long; without checkpoints, every failure forces expensive re-collection and risks timeouts forever.

**Independent Test**: Partially complete a batch (or seed DB as if some counties are done), kill/restart the worker for the same batch, confirm skip counts for completed units and new writes only for incomplete units, with no duplicate identity corruption.

**Acceptance Scenarios**:

1. **Given** some counties in the batch already have complete stored results for a worker, **When** that worker runs again for the same batch, **Then** it skips those counties and reports how many were skipped versus fetched.
2. **Given** a county failed or was never written, **When** the worker restarts, **Then** it attempts that county again.
3. **Given** a successful county write, **When** the job crashes immediately afterward, **Then** a restart treats that county as done (database contents are the checkpoint source of truth).

---

### User Story 3 - National safety points without fixture addresses (Priority: P2)

For counties outside the historic metro fixture set, the safety ingest selects agencies using a stable per-county geographic point (not the ten fixture street addresses), checkpoints per county, and still reports honest coverage when some counties cannot obtain source data.

**Why this priority**: Fixture lat/lon cannot scale to ~3,000 counties; national safety depends on a geography-based point per county.

**Independent Test**: Run safety ingest for a state batch that includes at least one non-fixture county; confirm agency selection used a county geographic point and rows checkpointed per county; incomplete coverage remains visible in status %.

**Acceptance Scenarios**:

1. **Given** a county in the national universe with a known centroid/point, **When** safety ingest runs for a batch containing that county, **Then** agency selection uses that county’s point rather than a fixture street address.
2. **Given** partial safety coverage in a batch, **When** the job finishes, **Then** successful counties remain stored, status % reflects actual coverage, and the batch does not pretend 100% success if required coverage is incomplete.

---

### User Story 4 - Preserve smoke and metro scopes (Priority: P2)

Operators can still run smoke (single-county) and metro fixture (ten-county) scopes for fast verification. Those scopes continue to work and report status against their own denominators, unaffected by national registry work.

**Why this priority**: Metro and smoke remain the fast regression path; national must not break them.

**Independent Test**: Run status and a small worker path under smoke and metro_10; confirm denominators and behavior match existing fixture expectations.

**Acceptance Scenarios**:

1. **Given** smoke or metro_10 scope, **When** workers and status run, **Then** they use the existing small geography sets and do not require a national state batch.
2. **Given** national registry data exists in the system, **When** metro_10 status is refreshed, **Then** metro completion still measures against the ten fixture counties only.

---

### User Story 5 - Inventory-driven orchestrator via Actions (Priority: P1)

An ops operator starts a manual GitHub Actions workflow that triggers an Azure orchestrator. The orchestrator inventories which counties (or states) still lack each worker’s data, then starts only the ACA jobs that have gaps—skipping workers that are already complete for a state. Re-running the workflow continues from remaining gaps without redoing finished sources. The operator watches progress on the Workbook.

**Why this priority**: Manual per-state clicking does not scale; inventory prevents wasting compute on sources that already succeeded (e.g. EPA done, FBI still missing).

**Independent Test**: With EPA complete for a test state and FBI incomplete, run orchestrator for that state filter; confirm EPA job is not started and FBI (and later pipeline steps with gaps) are started; re-run after FBI completes starts neither for that state if all workers are done.

**Acceptance Scenarios**:

1. **Given** a national universe with mixed completeness per worker, **When** the orchestrator inventories, **Then** it produces a gap list per worker and only queues worker/state pairs with missing data.
2. **Given** a worker has zero gaps for a state, **When** the orchestrator processes that state, **Then** it does not start that worker’s ACA job for that state.
3. **Given** the operator re-runs the Actions workflow after partial progress, **When** inventory runs again, **Then** only remaining gaps are queued.
4. **Given** the Actions workflow is configured, **When** code is pushed to master for site Deploy, **Then** national ingest orchestration does not start automatically.

---

### User Story 6 - Force re-ingest specified states (Priority: P2)

An ops operator wants to refresh data for one or more states that inventory already marks complete (schema/scoring change, bad prior pull, vintage refresh). They supply `force_states` on the Actions workflow (or `ORCH_FORCE_STATES` on the orchestrator). The orchestrator schedules those states and all pipeline workers regardless of gaps, and workers re-run the batch without skip-done (upserts only—no table wipe).

**Why this priority**: Gap-only orchestration cannot refresh “done” states; force is the ops escape hatch.

**Independent Test**: With a state fully complete in inventory, run orchestrator with that state in `force_states`; confirm every pipeline worker is started with `INGEST_FORCE=1` and skip counts are zero for that batch.

**Acceptance Scenarios**:

1. **Given** state S is complete for all workers, **When** the operator runs with `force_states=S` and `max_states` greater than 1, **Then** the orchestrator queues **only** S (no gap padding from other states) and starts all pipeline workers for S.
2. **Given** `INGEST_FORCE=1` on a worker, **When** that worker runs, **Then** it does not skip counties that already have stored rows (re-upserts instead).
3. **Given** a non-forced state with no gaps, **When** the orchestrator runs without that state in force, **Then** it still skips complete worker/state pairs as in US5.

---

### User Story 7 - Mid-run status monitoring (Priority: P2)

While a long national job runs, the Workbook updates more often than once per state: the orchestrator emits an `INGEST_STATUS_SNAPSHOT` after each worker completes, and long unit-loop workers emit a snapshot every N counties (or LEAIDs for Urban), default N=15. Console log lines MUST stay small enough for Log Analytics to store a complete parseable JSON (metrics only); full missing-county detail remains in Postgres.

**Why this priority**: Per-state-only status leaves ops blind during multi-hour workers (rate limits, hangs).

**Independent Test**: Run a multi-county worker with N=15; confirm multiple `INGEST_STATUS_SNAPSHOT` lines appear in logs before the worker finishes and Workbook KQL can parse `payload.jobs` for `scope=national`; after each pipeline worker in a state, an additional snapshot is emitted.

**Acceptance Scenarios**:

1. **Given** a state with multiple workers queued, **When** each worker finishes, **Then** a status snapshot is emitted before the next worker starts (or immediately after).
2. **Given** a county-loop worker processing more than N counties, **When** it processes counties, **Then** it emits a status snapshot at least every N completed units.
3. **Given** a status emit fails, **When** ingest continues, **Then** the worker/orchestrator does not hard-fail solely because of the status emit.
4. **Given** a national-scope snapshot, **When** the console log line is ingested by Log Analytics, **Then** the JSON includes `scope`, `county_count`, and `jobs` metrics and does **not** embed the full county FIPS list or per-job missing lists.

---

### Edge Cases

- What happens when a state FIPS in the batch is unknown or not in the 50+DC list? Job fails clearly before fetch work.
- How does the system handle a territory FIPS if someone adds it before territories are enabled? Either ignored with a clear log or rejected until the extensible registry explicitly includes that jurisdiction.
- What if Census geography for a county has no usable centroid? Safety ingest skips that county with logged reason; status stays honest.
- What if upstream APIs rate-limit mid-batch? Job may fail or exit incomplete; restart resumes via checkpoints without wiping prior counties.
- What if operator re-runs an already-complete state batch? Workers mostly skip-done and exit successfully (or report nothing new to do)—unless `force_states` / `INGEST_FORCE` is set, in which case they re-upsert.
- What if inventory shows all workers complete for selected states? Orchestrator exits successfully without starting ingest jobs (may still refresh status)—unless forced states are supplied.
- What if GitHub Actions times out while the Azure orchestrator is still running? Operator re-dispatches; inventory-driven queue resumes from gaps.
- What if Azure ARM returns 500 when patching/starting a job? Orchestrator retries with backoff before failing that worker.
- What if `force_states` is set (with or without `state_filter`)? Only the forced FIPS list runs (capped by `max_states`)—no padding with other gap states.
- What if only `state_filter` is set? Only gap states within that filter run (capped by `max_states`)—no states outside the filter.
- What if both force and filter are empty? Gap-fill across the national inventory up to `max_states` (unscoped national continue).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define a national county universe as all counties in the 50 US states plus the District of Columbia for v1 completion denominators.
- **FR-002**: System MUST keep an extensible jurisdiction/registry design so US territories can be added later by configuration or list update without redesigning national ingest.
- **FR-003**: System MUST NOT require territories for national v1 success criteria.
- **FR-004**: System MUST require an explicit state batch for national worker runs; empty batch under national scope MUST be rejected with a clear operator-facing message.
- **FR-005**: System MUST limit each national worker run to counties in the supplied state batch.
- **FR-006**: Every national-capable ingest and scoring worker MUST checkpoint progress such that a restart with the same batch skips units already successfully stored, using durable database contents as the source of truth (not a disposable side file).
- **FR-007**: Checkpoint grain MUST be at least county for county-scoped work; state-scoped source pulls MAY checkpoint at state when that matches the source’s natural unit, provided restart still avoids redoing finished work.
- **FR-008**: Safety ingest under national scope MUST select agencies using a per-county geographic point derived from authoritative geography (e.g. county centroid), not the metro fixture street-address list.
- **FR-009**: Safety ingest MUST continue to upsert/checkpoint per county and MUST report honest incomplete coverage for a batch when some counties fail.
- **FR-010**: National ingest status MUST compute real per-worker completion percentages against the full 50+DC county (or tract, where scoring uses tracts) universe—not a stub “not supported” result.
- **FR-011**: Smoke and metro_10 scopes MUST remain supported with their existing small denominators and MUST NOT require a national state batch.
- **FR-012**: National ingest MUST use idempotent upserts; operators MUST NOT need to truncate tables to resume or re-run a batch.
- **FR-013**: Product in-app national progress UI and Slack/webhooks are OUT OF SCOPE for this feature. A single multi-day unattended run without re-dispatch is OUT OF SCOPE; re-dispatch continues from inventory.
- **FR-014**: Operators MUST be able to refresh national progress via the existing ops status path (snapshot + Workbook) after state batches.
- **FR-015**: System MUST provide an inventory of missing work per ingest/scoring worker against the national county universe (county grain; CMS at state grain; scoring per existing fbi_cde tract rule).
- **FR-016**: An orchestrator MUST start only ACA worker jobs for worker/state pairs that inventory marks as incomplete, and MUST NOT start jobs for pairs with zero gaps.
- **FR-017**: Operators MUST be able to trigger the orchestrator via a manual GitHub Actions workflow that does not run on ordinary master Deploy pushes.
- **FR-018**: Orchestrator runs MUST be time-bounded (configurable max states per run) so re-runs continue filling remaining gaps.
- **FR-019**: Operators MUST be able to force re-ingest of specified state FIPS via Actions/`ORCH_FORCE_STATES`, causing the orchestrator to run all pipeline workers for those states and set `INGEST_FORCE=1` (always set `0` when not forcing so force does not stick on the ACA job). When `ORCH_FORCE_STATES` is non-empty, the orchestrator MUST process only that list (capped by `ORCH_MAX_STATE_UNITS`) and MUST NOT pad with other gap states.
- **FR-020**: When `INGEST_FORCE` is enabled, workers MUST NOT skip units already stored; they MUST re-process and upsert.
- **FR-021**: The orchestrator MUST emit a national status snapshot (`INGEST_STATUS_SNAPSHOT` + durable snapshot row) after each worker completes for a state.
- **FR-022**: County/unit-loop workers (at least FBI, ACS, BLS, Urban) MUST emit a status snapshot every N units (default 15, configurable via `INGEST_STATUS_EVERY_N`); status emit failures MUST NOT fail the ingest job.
- **FR-023**: Orchestrator ARM calls that patch or start ACA jobs MUST retry transient control-plane failures (HTTP 429/500/502/503) with exponential backoff before treating the call as failed.
- **FR-024**: The console `INGEST_STATUS_SNAPSHOT` line MUST be Workbook-safe: metrics only (`scope`, `county_count`, `captured_at`, per-job pct/done/total). It MUST NOT embed the full county FIPS list or large missing-county detail. Full detail MUST remain in Postgres `ingest_status_snapshot`.
- **FR-025**: When `ORCH_STATE_FILTER` is non-empty and `ORCH_FORCE_STATES` is empty, the orchestrator MUST process only gap states within that filter (capped by max), never states outside the filter.

### Key Entities

- **Jurisdiction registry**: Ordered set of included state/equivalent FIPS codes (50+DC in v1; territories reserved for later append).
- **County unit**: SSCCC county identity plus geographic point used for safety selection; membership derived from authoritative Census geography for included jurisdictions.
- **State batch**: Operator-supplied list of state FIPS codes that bounds one worker execution under national scope.
- **Checkpoint unit**: A county (or state) that already has qualifying stored rows for a given worker so restart can skip it.
- **National status snapshot**: Per-worker done/total/% against the full national universe (independent of the current batch size).
- **Gap inventory**: Per-worker list of incomplete counties (or states) derived from database contents.
- **Orchestrator run**: Bounded Azure job that inventories gaps, starts only needed worker jobs in pipeline order per state, and refreshes status.
- **Force state set**: Operator-supplied state FIPS that bypass inventory skip and worker skip-done for one run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete at least one non-fixture state end-to-end (ingest through scoring) using an explicit state batch, with national status % increasing for that state’s counties.
- **SC-002**: After interrupting a worker mid-batch and restarting with the same batch, at least 95% of already-complete counties in that batch are skipped (no full re-fetch), verified by skip counts / logs and stable row identities—unless force is enabled.
- **SC-003**: National status denominator equals the county count for 50 states + DC; territories are not required to reach “national complete” for v1.
- **SC-004**: Smoke and metro_10 status and a fixture-scoped worker re-run still succeed without a national state batch.
- **SC-005**: Attempting national scope with no state batch fails fast with an actionable message in under 30 seconds (no multi-hour accidental run).
- **SC-006**: When inventory shows worker W complete for state S, an orchestrator run for S does not start the ACA job for W—unless S is in the force set.
- **SC-007**: A second orchestrator run after partial completion queues fewer (or equal) gap units than the first, never re-queueing worker/state pairs that became complete (force runs excepted).
- **SC-008**: With `force_states` set for a complete state, all pipeline workers for that state are started in one orchestrator run, and no other state FIPS are queued solely to fill `max_states`.
- **SC-009**: During a long county-loop worker, at least one mid-job `INGEST_STATUS_SNAPSHOT` appears in logs when more than N counties are processed (N default 15).
- **SC-010**: A single transient ARM 500 on job PATCH does not fail the orchestrator if a subsequent retry succeeds within the retry budget.
- **SC-011**: A national-scope `INGEST_STATUS_SNAPSHOT` console line is under 8KB and Workbook KQL can parse `payload.jobs` for scope `national`.

## Assumptions

- Ops operators run jobs via Azure Container Apps Jobs, local Docker, or the inventory orchestrator (Actions → orchestrate job).
- Authoritative county list and centroids come from Census TIGER (or equivalent Census geography) already used for tracts.
- Existing metro fixture addresses remain for smoke/metro_10 and local regression; they are not the national safety point source.
- Upstream rate limits and incomplete FBI coverage for some counties are expected; honest status % is preferred over fake 100%.
- ACA job time limits mean phased state batches (manual or orchestrated) are the supported national operating model for v1.
- Existing `ingest_status_snapshot` and Azure Monitor Workbook remain the ops visibility path.
- Spec 002 fixture-only constraint is superseded for this new feature’s national path; 002 behavior for metro/smoke is preserved.
- GitHub Actions uses existing `AZURE_CREDENTIALS`; the orchestrator job holds SP credentials to start sibling ACA jobs.
- Inventory runs inside Azure (not on the Actions runner) so Postgres firewall rules are satisfied.
