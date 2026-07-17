# Feature Specification: National Report Detail Ingest

**Feature Branch**: `005-national-report-detail`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Make the changes needed to prod and any files or documentation in the branch to allow the national ingest workflow to get all the information we need for report sub-scores (hazard, ER wait/timeliness, population-normalized safety, and re-scored expand detail). We will run a test manually with the smoke test. And if it looks just like it did in the dev build, I will start running the National Ingest workflow."

## Clarifications

### Session 2026-07-16

- Q: Must National Ingest pick already-ingested states that only lack report-detail, and fill only new gaps without force? → A: Yes. Example: if AR/MA/MS/TX/NY already have base ingest and a run uses max_states=3 with no filters, the orchestrator may select among those five (and any other gap states); for a selected state it must only collect missing report-detail inputs and refresh expand scores—never require force-update of finished base workers.
- Q: When max_states mixes virgin states and base-complete states missing only report-detail, what selection priority? → A: Prefer base-complete states that still lack report-detail first; then virgin / other gap states.
- Q: Where must the smoke gate pass before National Ingest? → A: Azure / production DB smoke using the same jobs path as national must pass; local Compose alone is not sufficient.
- Q: Does this feature own deploying expand API/web for the smoke report? → A: No separate API/web deploy workstream in 005. Operator merges 005 → dev, then promotes dev → master (so production Deploy ships expand-capable API/web with this feature) before initiating the Azure smoke test.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator prepares production for expanded reports (Priority: P1)

An operator applies the documented production database updates for report expand detail, then confirms the live product can serve expanded reports once scores are refreshed—without wiping existing national or metro data already collected.

**Why this priority**: Without production storage ready for hazard rows, timely-care measures, population fields used in safety rates, and stored expand detail, National Ingest cannot persist the new inputs and the live report cannot match the local/dev expand experience.

**Independent Test**: On a production-like database that already has neighborhood scores, apply the documented additive updates; confirm existing score lookups still succeed; confirm new storage for hazard, timely care, and expand detail is present and empty or defaulted until new jobs run.

**Acceptance Scenarios**:

1. **Given** a production database that already holds neighborhood scores and prior ingest tables, **When** the operator applies the documented additive schema updates for report detail, **Then** existing score and ingest data remain intact and score lookups continue to succeed.
2. **Given** those schema updates are applied, **When** the operator inspects storage readiness, **Then** places exist to store hazard-by-tract data, hospital timely-care measures, ACS total population used for safety rates, and per-tract expand detail for reports.
3. **Given** schema is applied but new jobs have not yet filled hazard/timely data, **When** a user opens a report that already has category scores, **Then** the report still loads; expand content that depends on missing new inputs shows limited-data / unavailable messaging rather than invented flood or wait figures.

---

### User Story 2 - Smoke gate matches the local/dev expand report (Priority: P1)

Before spending a national run, an operator first merges this feature to `dev`, promotes `dev` to `master` so production Deploy has shipped expand-capable API and web together with worker/docs changes, applies report-detail schema on production if not already applied, then runs the documented **smoke-scope path on Azure against the production database** (same worker image and job path used for national). They open a known fixture address on the live site. The expanded report looks like the accepted local/dev build: category boxes with sub-scores, plain-English expand stats, and hazard/wait detail when those smoke jobs have completed. Local Compose may be used for development, but it does **not** satisfy the gate to start National Ingest.

**Why this priority**: The user will only start National Ingest after production smoke looks correct on the post-promote stack; this is the release gate that prevents a costly wrong national run against real Azure wiring.

**Independent Test**: After `005 → dev → master` promote and schema apply, follow the Azure/production smoke operator checklist; open the Bentonville (or documented smoke) report on production; compare expand behavior to the known-good local/dev report.

**Acceptance Scenarios**:

1. **Given** this feature has been merged to `dev`, `dev` has been promoted to `master`, production Deploy has the expand report UI/API, schema is ready, and smoke-scope collection + score refresh have completed via Azure jobs against the production database, **When** the operator opens the documented smoke address report on production, **Then** each category shows sub-scores and can expand to plain-English stats consistent with the local/dev expand report.
2. **Given** smoke hazard and timely-care collection succeeded for that geography on Azure/prod, **When** the operator expands Environment and Healthcare, **Then** hazard context and ER wait / timeliness comparison appear when the sources provided them (same expectations as the local/dev feature).
3. **Given** smoke looks wrong (missing expand detail, property scored as zero when limited-data is expected, absurd school distances, raw source ids in copy), **When** the operator evaluates the gate, **Then** they stop and do **not** start National Ingest until the Azure/prod checklist passes—even if local Compose looked fine.

---

### User Story 3 - National Ingest collects report-detail inputs without redoing finished work (Priority: P1)

An operator starts the National Ingest workflow (or equivalent orchestrated national path) with a normal phased run (for example max_states=3 and no force / no state filter). The inventory treats **report-detail gaps as real gaps**: states that already finished base ingest (census through labor and prior scoring) but still lack hazard, timely-care, ACS population for safety rates, and/or expand detail remain eligible for selection. **Selection priority:** among eligible gap states, prefer those that are base-complete but still missing report-detail; only after those are satisfied (or the max_states budget is filled with them) select virgin / other gap states. For each selected state, only the unfinished report-detail stages run; finished base workers are skipped. The operator does **not** need to force-update a state solely to unlock the new information.

**Why this priority**: National runs are expensive; several states may already hold “old” complete base data. Without treating report-detail as inventory gaps, those states would look “done” and never get hazard/timely/expand detail unless the operator forces them—which the operator refuses to require.

**Independent Test**: Seed a DB where five states have complete base ingest but empty report-detail and other virgin states exist; run National Ingest with max_states=3 and no filters; confirm the budget prefers the five base-complete states; for each chosen state only report-detail jobs and expand re-score run; base workers stay skipped. Re-run and confirm skip-done for already-filled report-detail rows.

**Acceptance Scenarios**:

1. **Given** states such as AR, MA, MS, TX, and NY that already have complete base ingest and neighborhood scores but empty expand detail / missing hazard or timely-care inputs, **and** other states with no base data yet, **When** the operator runs National Ingest with max_states=3 and no force and no state filter, **Then** the orchestrator prefers selecting from the base-complete report-detail-gap set first (up to three), and for each selected state runs only the missing report-detail stages plus expand score refresh—without forcing or re-running finished base workers.
2. **Given** no remaining base-complete report-detail-only gaps (or max_states not yet filled), **When** the same style of run continues, **Then** virgin / other gap states may be selected next under the remaining budget.
3. **Given** tracts that already have hazard rows and hospitals that already have timely measures for the active vintage, **When** those jobs re-run without an explicit force, **Then** already-stored identities are skipped or upserted idempotently with no duplicate-key corruption.
4. **Given** counties whose expand detail is already populated for the active score vintage, **When** scoring runs without force, **Then** those counties are skipped; counties with empty expand detail are still scored.
5. **Given** ACS rows exist for a county but total population used for safety rates is missing, **When** inventory/orchestration evaluates ACS completeness, **Then** that county/state remains an ACS (or report-detail) gap and a normal (non-force) run backfills population without redoing non-ACS workers.

---

### User Story 4 - Operators have clear prod docs and run order (Priority: P2)

An operator following production documentation can merge/promote to `master`, apply schema, create or start any new national jobs required for report detail, run Azure smoke verification, then start National Ingest—without hunting through local-only Compose notes.

**Why this priority**: As-built Azure docs currently stop before report-detail schema and omit the new jobs from the national worker list; wrong docs cause failed national runs or skipped stages.

**Independent Test**: A second operator (or the same operator on a clean checklist) completes promote → schema apply → Azure smoke verify → national start using only the updated production documentation.

**Acceptance Scenarios**:

1. **Given** the production setup / CI docs for workers, **When** the operator looks up schema migrations and job list, **Then** report-detail schema and the hazard / timely-care (and scoring/ACS implications) steps are listed in order with merge/promote → smoke-before-national guidance.
2. **Given** National Ingest status / progress views, **When** report-detail jobs are part of the national path, **Then** operators can see completion progress for those jobs in the same status approach used for other national workers (or the docs state the interim visibility method until status is extended).

---

### Edge Cases

- Production already has some metro/national base data but no report-detail tables → additive schema only; no truncate.
- States with 100% complete base ingest but missing report-detail → still appear as gap states in a normal max_states run; force is not required; these states are preferred over virgin states when filling the max_states budget.
- Smoke passes UI but national refuse / missing jobs still block hazard/timely at national scope → national path MUST allow those collections (lifting local-only refusals for this feature).
- Timely-care source returns only state/national aggregates for a hospital → treat hospital wait as unavailable; do not invent a facility wait from aggregates alone.
- Hazard missing for a tract after national run → Environment still shows air quality; hazard shows unavailable.
- Re-score changes category numbers slightly when new sub-score components appear (timeliness, hazard) → expected; overall weights stay the product’s published weights; document that smoke gate includes spot-checking scores still look sane.
- Explicit force-rerun for selected states → may re-upsert report-detail inputs and re-score those states; must not silently force the entire unfinished national universe unless the operator asked for that; force is never the only way to unlock report-detail for already-ingested states.
- Worker image on Azure older than this feature → docs MUST require deploying the worker image that includes the new jobs before smoke/national report-detail runs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Production database MUST support additive storage for tract hazard data, hospital timely-care measures, ACS total population for safety rate normalization, and per-tract report expand detail, without destroying existing ingest or score rows.
- **FR-002**: Operators MUST be able to apply those production schema updates using documented, idempotent steps suitable for an already-populated database.
- **FR-003**: Hazard collection MUST run for active national (and smoke) geography scopes and persist tract-level results keyed so re-runs skip or upsert safely.
- **FR-004**: Timely-care / ER wait measure collection MUST run for hospitals already in scope for the active geography and persist facility-level measures with state/national comparisons when the source provides them.
- **FR-005**: National Ingest orchestration (inventory + job start path) MUST include the new report-detail collection stages and score refresh needs so a national run can close gaps for expand-ready reports.
- **FR-006**: Gap detection MUST prefer skipping work that is already complete: base ingest checkpoints remain valid; hazard/timely/score-detail gaps drive only the remaining work.
- **FR-006a**: Inventory MUST treat a state/county as still having work when base ingest is complete but any report-detail stage is incomplete (missing hazard coverage, missing timely-care for in-scope hospitals, missing ACS total population, or empty expand detail). Such states MUST remain selectable in a normal phased National Ingest run (max_states, no force, no state filter)—force MUST NOT be required solely to unlock report-detail for previously gathered states.
- **FR-006b**: When selecting states for a normal max_states run (no force, no exclusive state filter), the orchestrator MUST prefer states that are base-complete but still have report-detail gaps over virgin / other gap states, then fill any remaining max_states budget from other gap states.
- **FR-007**: When ACS indicator rows exist but total population is missing, inventory MUST count that as an incomplete ACS/report-detail gap so a normal (non-force) run backfills population without requiring unrelated workers to re-run.
- **FR-008**: Scoring MUST write expand detail for geographies that still lack it after new inputs are available, and MUST skip geographies that already have expand detail for the active vintage unless the operator explicitly forces a re-score.
- **FR-009**: After this feature is on `master` via the documented promote path (`005` → `dev` → `master`), production Deploy has expand-capable API/web, schema is applied, and smoke-scope collection + score refresh have run via Azure jobs against the production database, a documented smoke address report on production MUST present the same class of expand experience as the accepted local/dev build (sub-scores, plain-English factors, hazard/wait when prepared). Local Compose success alone MUST NOT be treated as the National Ingest gate.
- **FR-010**: Production operator documentation MUST describe merge/promote to `master`, schema apply, new Azure jobs / worker image, Azure/prod smoke verification gate, then National Ingest—including that National Ingest should not start until Azure/prod smoke looks correct.
- **FR-011**: Report API behavior for empty expand detail MUST remain graceful (limited data, no fabricated hazard/wait) so deploying API/UI ahead of a full national fill does not break lookups.
- **FR-012**: Status/progress tooling used for national ops MUST either include the new jobs or document how operators verify hazard/timely/score-detail completion until status is extended.

### Key Entities

- **Report expand detail**: Stored per-tract explanation of category sub-scores and expand stats served on the report; empty until score refresh after inputs exist.
- **Tract hazard record**: Natural-hazard / composite risk context for a census tract used in Environment expand and related sub-scores.
- **Hospital timely-care measure**: Facility-level wait/timeliness figures (with optional state/national benchmarks) used in Healthcare expand.
- **Population for safety rates**: Total population at tract and state grains used to express violent/property crime intensity per resident vs state.
- **National Ingest run**: Operator-triggered, gap-aware collection across states that must now also close report-detail gaps.
- **Smoke verification gate**: Azure/production-DB smoke check that must match local/dev expand quality before a national run (Compose alone insufficient).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After documented production schema updates, 100% of previously available score lookups for already-scored tracts continue to succeed (no data wipe required).
- **SC-002**: After promote to `master` and a successful Azure/production-DB smoke gate, a reviewer comparing that environment’s smoke report to the known-good local/dev expand report finds matching expand capabilities for all five categories (sub-scores visible; expand stats present; hazard and wait present when smoke jobs completed)—and the operator is ready to start National Ingest.
- **SC-003**: For counties that already had complete base ingest before this feature, a national/smoke report-detail fill completes without the operator needing to delete or force-rerun finished census, air-quality, hospital directory, crime, school, or labor collections solely to unlock expand detail.
- **SC-003a**: In a fixture where only previously gathered states lack report-detail (base complete), a National Ingest run with max_states=3 and no force/filters selects up to three gap states from that eligible set and completes only report-detail stages for them—demonstrably without force.
- **SC-003b**: In a fixture that mixes base-complete report-detail-gap states with virgin gap states, a max_states=3 run with no force/filters fills its budget from the base-complete report-detail-gap set first before selecting virgin states.
- **SC-004**: A second run of hazard and timely-care collection over the same smoke geography does not create duplicate identity rows and skips or no-ops already-complete units when force is off.
- **SC-005**: After national (or phased state) report-detail collection for a prepared state, at least 95% of tracts in that state’s completed county set that have base scores also have non-empty expand detail for the active vintage (remaining gaps only where upstream inputs are genuinely unavailable).
- **SC-006**: An operator new to the runbook can locate merge/promote → schema → smoke → national steps in production docs and complete the smoke gate without undocumented tribal knowledge.

## Assumptions

- Local/dev report expand behavior from feature `004-report-subscores` is the visual and content reference for the smoke gate (“looks just like the dev build”).
- Operator sequence before smoke: merge `005-national-report-detail` into `dev`, promote `dev` → `master`, let production Deploy update API/web/workers as configured; then apply schema if needed and run Azure smoke. This feature’s implementation focus is production schema, national/smoke collection path, orchestration, status/docs—not a separate ad-hoc API/web release outside that promote.
- Base national or metro ingest may already be partially complete; this feature must be additive and gap-aware.
- Operators will continue national with ordinary max_states batches; they must not be required to pass force_states merely because a state’s base data predated report-detail jobs.
- Smoke verification uses the existing smoke geography / fixture address (Bentonville path) on Azure against the production database unless ops docs name a different production smoke pin; local Compose is for development only and does not clear the national gate.
- National Ingest remains a separate operator action after the smoke gate; this feature enables the workflow, it does not auto-start national on every deploy.
- Azure Container Apps Jobs (or the project’s current national job host) remain the execution environment for production workers.
- No new paid third-party data contracts are required beyond existing public FEMA and CMS sources already used in local report-detail work.
- Territories remain out of scope consistent with current national ingest policy unless already included in the geo registry.
