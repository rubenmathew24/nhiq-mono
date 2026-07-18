# Feature Specification: National Coverage Dashboard

**Feature Branch**: `007-national-ingest-redesign` (feature artifacts: `008-national-coverage-dashboard`)

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Add a public dashboard page on the site that shows how much of the national data has been loaded — overall, by state, and by source — with no auth. Use correct expected denominators from the national ingest redesign. Deliver via Spec Kit on the existing 007 branch."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See overall national coverage at a glance (Priority: P1)

A visitor opens a public coverage page on the website and immediately sees how much of the 50-state + DC nation is covered overall and for each data source (including scoring). Percentages use the same national expected totals as ops ingest status (full county registry for county-grain sources; state grain where that is the source’s true grain). No login is required.

**Why this priority**: The primary ask is a trustworthy, glanceable answer to “how much of the country do we have?”

**Independent Test**: With a known partial national load, open the public coverage page and confirm overall/source percentages match the national denominator semantics (not inflated by only-loaded geography).

**Acceptance Scenarios**:

1. **Given** the national county registry exists for 50 states + DC, **When** a visitor opens the public coverage page, **Then** they see overall and per-source completion without signing in.
2. **Given** only a minority of states have finished scoring, **When** scoring coverage is shown, **Then** the percentage is roughly completed counties ÷ total national counties (same meaning as national ingest scoring progress).
3. **Given** the registry is empty or unavailable, **When** the page loads, **Then** the visitor sees a clear empty/unavailable state rather than a fake 100% or silent blank.

---

### User Story 2 - Browse coverage by data source (Priority: P1)

A visitor can focus on one source at a time (or see all sources listed) to understand which pipeline stages are lagging nationwide — e.g. hazards vs schools vs scoring — using the correct grain for each source.

**Why this priority**: Operators and stakeholders need source-level truth, not a single opaque number.

**Independent Test**: Compare each source’s done/total on the page against the known national completion rules for that source (county vs state grain).

**Acceptance Scenarios**:

1. **Given** national data is partially loaded, **When** the visitor views by-source coverage, **Then** each tracked ingest/scoring source shows done count, total expected, and percentage against the national universe for that source’s grain.
2. **Given** CMS and CMS Timely are state-grain sources, **When** those rows are shown, **Then** totals reflect the expected state count for 50+DC (not county count).

---

### User Story 3 - Browse coverage by state (Priority: P1)

A visitor can switch to a by-state view and see, for each included state (and DC), how complete that jurisdiction is for the tracked sources — so they can see which states are missing data without auth.

**Why this priority**: Geographic unevenness is the main story during a multi-day national ingest.

**Independent Test**: Pick a state known to be fully loaded and one known incomplete; confirm the by-state view reflects that difference using that state’s county (or state-grain) expected totals from the national registry.

**Acceptance Scenarios**:

1. **Given** some states are complete for a source and others are not, **When** the visitor opens the by-state view, **Then** each included state shows coverage for the tracked sources against that state’s expected units.
2. **Given** the visitor is on the coverage page, **When** they switch among overall, by source, and by state presentations, **Then** they can understand national coverage without leaving the page or authenticating.

---

### Edge Cases

- What if `geo_counties` is empty? Show fail-closed empty/unavailable messaging; do not invent a denominator.
- What if a source has zero rows for a state that has counties in the registry? That state/source shows 0% (or 0 done) for that source.
- What if CMS has no hospitals in a state? Treat completeness consistently with national ingest status rules for that source (done when there is nothing required, or incomplete when hospitals exist without measures — match existing status semantics).
- What if the API is down? The page shows an error state; it does not fabricate percentages.
- Territories are out of scope for v1 denominators (same included set as national ingest).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST expose a public web page (path `/coverage`) that requires no authentication.
- **FR-002**: The page MUST present national coverage in three ways: overall, by source, and by state.
- **FR-003**: Coverage denominators MUST use the full included national universe (50 states + DC) from the county registry for county-grain sources — not “only counties already loaded into census.”
- **FR-004**: Scoring coverage MUST use county-grain done-ness consistent with national ingest redesign (every tract in the county has required safety source + non-empty score detail) against the national county total.
- **FR-005**: CMS and CMS Timely coverage MUST use state-grain totals for the included jurisdictions.
- **FR-006**: By-state coverage MUST use each state’s share of the national registry as the expected total for county-grain sources (and state-grain rules for CMS/Timely).
- **FR-007**: Coverage data MUST be served by the product API as a read-only public contract; the web page MUST not query the database or invent completion math in the browser beyond display formatting.
- **FR-008**: The API response MUST include enough structure for overall summary, per-source national stats, and per-state breakdowns (done/total/percent or equivalent).
- **FR-009**: Existing authenticated `/dashboard` (saved lookups) MUST remain unchanged in purpose and auth requirements.
- **FR-010**: Smoke/metro fixture scopes are not required on this public page; the page is national-coverage oriented.

### Key Entities

- **National universe**: Counties (and derived states) in the included 50+DC registry that define expected totals.
- **Source coverage**: Per ingest/scoring job completion against that universe at the job’s grain.
- **State coverage**: Per-jurisdiction completion for those sources against that state’s expected units.
- **Coverage snapshot**: The read model returned to the public page (point-in-time from live DB queries or equivalent).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor can open `/coverage` without signing in and see overall and by-source national percentages within a few seconds of a successful API response.
- **SC-002**: With a known partial nation, scoring and other county-grain sources never report near-100% solely because only a subset of states exist in tract tables — percentages stay consistent with full-registry denominators.
- **SC-003**: A visitor can identify at least one lagging source and at least one lagging state from the page without operator tools or auth.
- **SC-004**: CMS/Timely rows use state-scale totals; county-grain sources use county-scale totals — verified by spot-check against known registry sizes.

## Assumptions

- Delivered on git branch `007-national-ingest-redesign` alongside national ingest redesign; Spec Kit feature directory is `008-national-coverage-dashboard`.
- Public path is `/coverage` because `/dashboard` is already the authenticated saved-lookups experience.
- Tracked sources match national ingest status jobs (census, epa, cms, fbi, nces, urban, acs, bls, fema, cms_timely, scoring).
- Completion rules align with `007` national status semantics (including scoring county grain).
- Page is informational (“roughly how much of the nation we cover”), not a live ops control panel; slight staleness from query time is acceptable.
- No auth, rate-limit productization, or caching product is required for v1 beyond normal API practices.
- Thin client / fat API: Next.js displays; FastAPI computes.
