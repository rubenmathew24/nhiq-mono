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

### Edge Cases

- What happens when a state FIPS in the batch is unknown or not in the 50+DC list? Job fails clearly before fetch work.
- How does the system handle a territory FIPS if someone adds it before territories are enabled? Either ignored with a clear log or rejected until the extensible registry explicitly includes that jurisdiction.
- What if Census geography for a county has no usable centroid? Safety ingest skips that county with logged reason; status stays honest.
- What if upstream APIs rate-limit mid-batch? Job may fail or exit incomplete; restart resumes via checkpoints without wiping prior counties.
- What if operator re-runs an already-complete state batch? Workers mostly skip-done and exit successfully (or report nothing new to do).

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
- **FR-013**: Product in-app national progress UI, Slack/webhooks, and a single unattended all-states execution in one job are OUT OF SCOPE for this feature.
- **FR-014**: Operators MUST be able to refresh national progress via the existing ops status path (snapshot + Workbook) after state batches.

### Key Entities

- **Jurisdiction registry**: Ordered set of included state/equivalent FIPS codes (50+DC in v1; territories reserved for later append).
- **County unit**: SSCCC county identity plus geographic point used for safety selection; membership derived from authoritative Census geography for included jurisdictions.
- **State batch**: Operator-supplied list of state FIPS codes that bounds one worker execution under national scope.
- **Checkpoint unit**: A county (or state) that already has qualifying stored rows for a given worker so restart can skip it.
- **National status snapshot**: Per-worker done/total/% against the full national universe (independent of the current batch size).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete at least one non-fixture state end-to-end (ingest through scoring) using an explicit state batch, with national status % increasing for that state’s counties.
- **SC-002**: After interrupting a worker mid-batch and restarting with the same batch, at least 95% of already-complete counties in that batch are skipped (no full re-fetch), verified by skip counts / logs and stable row identities.
- **SC-003**: National status denominator equals the county count for 50 states + DC; territories are not required to reach “national complete” for v1.
- **SC-004**: Smoke and metro_10 status and a fixture-scoped worker re-run still succeed without a national state batch.
- **SC-005**: Attempting national scope with no state batch fails fast with an actionable message in under 30 seconds (no multi-hour accidental run).

## Assumptions

- Ops operators run jobs manually (Azure Container Apps Jobs or local Docker), same overall worker order as metro ingest.
- Authoritative county list and centroids come from Census TIGER (or equivalent Census geography) already used for tracts.
- Existing metro fixture addresses remain for smoke/metro_10 and local regression; they are not the national safety point source.
- Upstream rate limits and incomplete FBI coverage for some counties are expected; honest status % is preferred over fake 100%.
- ACA job time limits mean phased state batches are the supported national operating model for v1.
- Existing `ingest_status_snapshot` and Azure Monitor Workbook remain the ops visibility path.
- Spec 002 fixture-only constraint is superseded for this new feature’s national path; 002 behavior for metro/smoke is preserved.
