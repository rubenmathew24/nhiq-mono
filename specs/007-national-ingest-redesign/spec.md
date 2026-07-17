# Feature Specification: National Ingest Redesign

**Feature Branch**: `007-national-ingest-redesign`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Redesign national ingest for speed, accurate progress reporting against the full national universe, and hands-off continuous completion of all 50 states plus DC via one GitHub Action or one PowerShell command. Collect all required source data using bulk downloads or wider queries where available, fix inflated progress percentages, and keep gathering until the nation is complete without requiring the operator to manually re-trigger for each small batch of states."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate national progress (Priority: P1)

An ops operator opens the national ingest progress view (or queries the status snapshot) while only a minority of states have been fully collected. For every data source and for scoring, the completion percentage uses the full 50-state + DC universe as the expected total. Partially loaded geography must not inflate percentages (for example, scoring must not report ~70% complete when most of the country has never been collected).

**Why this priority**: Without trustworthy progress, the operator cannot decide whether a long run is healthy, estimate remaining time, or trust that “done” means nationwide complete.

**Independent Test**: With only a known subset of states fully collected and scored, refresh national status and confirm scoring and other job percentages are consistent with that subset over the full national county universe (not over only already-loaded tracts/counties).

**Acceptance Scenarios**:

1. **Given** national scope and a full county registry for 50 states + DC, **When** status is refreshed after only a minority of states are complete, **Then** each job’s percentage uses the full national denominator and rises only as more of that universe is actually complete.
2. **Given** scoring is complete for every tract in the collected states and incomplete elsewhere, **When** national scoring progress is shown, **Then** the percentage roughly matches completed counties ÷ total national counties (not completed tracts ÷ currently loaded tracts).
3. **Given** the operator excludes chronically failing states from a run, **When** progress is viewed, **Then** excluded states still count against the national denominator until they are complete or permanently out of scope by product decision (exclusion only affects scheduling, not the meaning of “100% national”).

---

### User Story 2 - One action runs until the nation is complete (Priority: P1)

An ops operator starts national ingest once—either by running the National Ingest GitHub Action with continuous mode enabled, or by running a single local PowerShell command—and does not need to manually re-dispatch for each small batch of states. The system keeps selecting unfinished work, collecting and scoring until every required national source for 50 states + DC is complete (or until the operator stops it). Progress messages remain visible during the wait so the operator can see what is currently being collected.

**Why this priority**: Today’s bounded multi-hour nibbles leave the nation incomplete after days of wall-clock time; the operator’s primary need is hands-off completion.

**Independent Test**: Start continuous national ingest against a database with known remaining gaps spanning more states than a single short batch would cover; leave it running; confirm it continues through multiple cycles and eventually reports nationwide completion (or clearly signals remaining work only when intentionally stopped / safety budget forces a handoff that resumes automatically).

**Acceptance Scenarios**:

1. **Given** unfinished national gaps exist across many states, **When** the operator starts continuous National Ingest (Action or PowerShell), **Then** the system schedules unfinished work repeatedly until inventory shows no remaining required gaps for 50+DC.
2. **Given** a continuous run is still incomplete when a platform time limit is approached, **When** that cycle ends, **Then** a follow-on cycle starts automatically (same Action chain or PowerShell loop) without requiring a new manual click, until complete or the operator cancels.
3. **Given** continuous mode is running, **When** the operator watches the Action log or console, **Then** they can see which states/sources were selected, whether the cycle completed the nation or needs more work, and approximate national progress.
4. **Given** the operator wants a bounded diagnostic run, **When** they disable continuous mode and set a max-states (or filter) limit, **Then** only that bounded set is processed and the run ends after that batch (existing bounded controls remain available).

---

### User Story 3 - Collection finishes far faster for the same nationwide outcome (Priority: P1)

An ops operator who previously saw only ~12 states + DC after 16+ hours of orchestrated runs can complete nationwide collection in substantially less wall-clock time for the same required data products. Sources that can be obtained as one national or per-state package are collected that way instead of thousands of tiny per-county or per-agency round trips. Sources that must remain fine-grained (agency-level safety) still complete without redundant repeated fetches of the same shared data.

**Why this priority**: Speed is the reason the redesign exists; accurate progress without finishable runs is insufficient.

**Independent Test**: Measure wall-clock to finish a representative multi-state batch (or full nation in continuous mode) before vs after; confirm required tables for those states contain the same classes of data needed for scoring/report detail, with far fewer upstream requests where bulk/wide fetch applies.

**Acceptance Scenarios**:

1. **Given** hazard data for all tracts is available as a single published national package, **When** national hazard collection runs, **Then** the system obtains that package once and loads in-scope tracts without one remote query per county.
2. **Given** census ACS tract indicators are needed for many counties in a state, **When** ACS collection runs for that state, **Then** the system fetches tract indicators for the state as a whole (or equivalent wide query), not one remote call per county.
3. **Given** school directory enrichment is needed for many districts in a state, **When** that enrichment runs, **Then** the system fetches by state (or equivalent wide query) and skips districts/schools already complete, not one call per district with no skip-done.
4. **Given** safety collection still requires per-county agency selection and offense charts, **When** multiple counties in the same state are processed, **Then** shared state-level agency lists are not re-downloaded for every county, and counties may proceed concurrently within safe rate limits.
5. **Given** a continuous nationwide run, **When** comparing operator effort and wall-clock to the prior “max 5 states per manual Actions run” pattern, **Then** finishing 50+DC no longer depends on dozens of manual re-triggers and completes in substantially less total elapsed time for the same completeness criteria.

---

### User Story 4 - Partial failures do not erase finished work (Priority: P2)

An ops operator’s continuous run hits a source timeout, rate limit, or cancelled Action mid-nation. Already-stored counties/states remain durable. Restarting continuous mode (or the automatic chain) resumes from remaining gaps without wiping completed units.

**Why this priority**: Long nationwide runs will still encounter failures; resumability is what makes continuous mode safe.

**Independent Test**: Partially complete a state for one source, interrupt the run, restart continuous mode; confirm completed units are skipped and only gaps are scheduled.

**Acceptance Scenarios**:

1. **Given** some counties in a state already have durable complete rows for a source, **When** that source runs again for the same state, **Then** those counties are skipped and only incomplete units are fetched.
2. **Given** a continuous cycle ends because of a time budget with gaps remaining, **When** the next cycle starts, **Then** inventory-driven selection continues from remaining gaps without requiring force-recollect of finished sources.
3. **Given** the operator cancels the GitHub Action watcher, **When** cloud worker executions already started are considered, **Then** durable DB checkpoints remain the source of truth for what is done (no silent wipe).

---

### Edge Cases

- What if the national county registry is empty or incomplete? Status and continuous mode must fail closed with a clear message to bootstrap the registry before claiming national progress.
- What if a published bulk file URL or schema changes upstream? The run must fail with a clear error (or fall back only where an explicit fallback is defined for secondary sources), not silently mark the nation complete.
- What if excluded/blacklisted states still have gaps? Continuous mode may skip scheduling them while progress denominators still reflect the full national universe unless product scope later removes them from the included set.
- What if force-recollect is requested for specific states? Continuous/bounded controls must still honor force for those states without padding unrelated gap states when force lists are exclusive.
- What if one source finishes the nation while another still has gaps? Continuous mode continues until all required pipeline sources (and scoring) are complete for the national universe.
- What if GitHub Actions chain depth grows without bound? The system must stop auto-chaining after a documented safety limit and report that remaining work needs a new operator start or investigation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: National completion percentages for every tracked ingest/scoring job MUST use the full 50-state + DC county universe (or the documented grain for that job that maps to that universe) as the denominator.
- **FR-002**: Scoring progress MUST NOT use “tracts currently present in the database” as the national denominator when that set is only a subset of the national universe.
- **FR-003**: Operators MUST be able to start continuous national ingest with a single GitHub Action dispatch that keeps working until nationwide required gaps are closed or the operator cancels.
- **FR-004**: Operators MUST be able to start the same continuous behavior with a single local PowerShell command that loops until complete or cancelled.
- **FR-005**: Continuous mode MUST automatically continue across platform time limits (new cycle and/or new Action run) without requiring a fresh manual dispatch for each small state batch.
- **FR-006**: Continuous mode MUST remain optional; bounded runs via max-states / state filter / force lists MUST still work for diagnostics and targeted refresh.
- **FR-007**: Where a source publishes an automatable national or wide (per-state) package that preserves the required data meaning, national collection MUST use that package or wide query instead of one remote call per county/district when that reduces wall-clock substantially.
- **FR-008**: Hazard (FEMA NRI) national collection MUST obtain tract-level risk/hazard fields for the national universe without one remote query per county when a national package is available.
- **FR-009**: ACS tract indicator collection for a state MUST use a state-wide fetch (or equivalent) rather than one remote call per county.
- **FR-010**: School directory enrichment MUST support state-scoped fetch and skip-done for already complete schools/districts.
- **FR-011**: Safety (FBI CDE) collection MUST preserve per-county agency selection and offense-chart fidelity; it MUST eliminate redundant re-fetch of the same state agency list per county and MAY process counties concurrently within documented rate limits.
- **FR-012**: Continuous scheduling MUST batch multiple unfinished states into each source execution where safe, rather than requiring a separate orchestrated round trip for every single state for every source.
- **FR-013**: Durable database contents remain the checkpoint source of truth; restarts MUST skip completed units for sources that support skip-done.
- **FR-014**: Operators MUST be able to observe during a run: selected states/sources, whether the nation is complete or more work remains, and national progress percentages that satisfy FR-001/FR-002.
- **FR-015**: Auto-chaining of continuous Action runs MUST enforce a maximum chain depth and surface a clear stop condition when that depth is exceeded with work remaining.
- **FR-016**: Smoke and metro_10 scopes MUST remain usable for fast verification and MUST NOT require continuous nationwide mode.

### Key Entities

- **National universe**: The set of counties in the 50 US states plus DC that defines “complete” for national progress.
- **Ingest job progress**: Per-source done count, total count, and percentage against the national universe (or that job’s documented grain mapped to it).
- **Continuous run**: An operator-started nationwide collection that repeatedly schedules remaining gaps until inventory shows no required unfinished work.
- **Bounded run**: An operator-started collection limited by max states, include filter, force list, and/or exclude list for diagnostics or targeted refresh.
- **Gap inventory**: The set of states/counties still missing required data for each pipeline source and scoring.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With only N of 51 jurisdictions fully complete, national scoring progress is within a few percentage points of N/51 (county-equivalent), never falsely near “majority complete” solely because only loaded tracts are counted.
- **SC-002**: An operator can start continuous national ingest with one Action click or one PowerShell command and leave it unattended until 50+DC required sources and scoring are complete, without manually re-dispatching for each ≤5-state nibble.
- **SC-003**: Wall-clock time to finish nationwide collection for the same completeness criteria is reduced by at least half versus the prior sequential per-state, per-source orchestration pattern that reached only ~12 states + DC in 16+ hours (measured on comparable remaining gap sets or a documented benchmark batch).
- **SC-004**: After an interrupted continuous run, a restart skips already-complete units and only schedules remaining gaps for at least the primary long-running sources (safety, ACS, schools enrichment, hazards, scoring).
- **SC-005**: During a continuous run, the operator can answer “what is running now?” and “is the nation done?” from the Action log or console without opening Azure Portal log dumps as the only option.
- **SC-006**: Smoke and metro_10 verification paths still complete successfully after the redesign without requiring continuous nationwide mode.

## Assumptions

- The national county registry is already bootstrapped (or can be bootstrapped before continuous mode claims progress); empty registry is an error, not 0% success.
- “Required” nationwide completeness means the existing national pipeline sources needed for neighborhood scores and report detail (including hazards and timely-care where already in scope), not every conceivable future dataset.
- FBI CDE master bulk files that require manual browser download are out of scope; preserving per-county agency-based safety methodology is preferred over switching to coarser national estimate tables.
- Azure Container Apps jobs and GitHub Actions remain the primary cloud execution path; the PowerShell entry point coordinates the same cloud workers rather than re-implementing all fetches only on a laptop.
- Excluding states from scheduling is an ops control for stuck sources; it does not redefine the national denominator unless jurisdictions are removed from the included universe by a separate product decision.
- Secondary sources that already finish quickly may still adopt bulk files for consistency, but primary success is driven by hazards, ACS, schools enrichment, safety efficiency, continuous orchestration, and accurate progress.
