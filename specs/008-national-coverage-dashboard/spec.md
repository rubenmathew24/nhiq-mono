# Feature Specification: National Coverage Dashboard

**Feature Branch**: `007-national-ingest-redesign` (feature artifacts: `008-national-coverage-dashboard`)

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Add a public dashboard page on the site that shows how much of the national data has been loaded — overall and by state (with a source filter including overall) — with no auth. Use correct expected denominators from the national ingest redesign. Deliver via Spec Kit on the existing 007 branch."

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

### User Story 2 - Browse coverage by state (with source filter) (Priority: P1)

A visitor switches to a **By state** view and picks a filter: **Overall** (mean of sources) or one tracked ingest/scoring source. They see a per-state table for that filter — so they can spot lagging states for a single pipeline stage or for overall completeness — using the correct grain for each source. No separate “by source” tab: national per-source rows live on the Overall tab; geographic drill-down is always by state.

**Why this priority**: Geographic unevenness is the main story during a multi-day national ingest; source lag is already visible on Overall.

**Independent Test**: Pick a state known to be fully loaded and one known incomplete; confirm the by-state view reflects that difference for both Overall and a single source, using that state’s county (or state-grain) expected totals from the national registry. Confirm CMS/Timely use state-grain totals when those filters are selected.

**Acceptance Scenarios**:

1. **Given** national data is partially loaded, **When** the visitor opens By state and selects a source, **Then** each included state shows done count, total expected, and percentage for that source against that state’s expected units (national summary for the selected source also shown).
2. **Given** CMS and CMS Timely are state-grain sources, **When** those filters are selected, **Then** totals reflect the expected state count for 50+DC (not county count).
3. **Given** the visitor selects **Overall** in By state, **When** the state table renders, **Then** each state shows mean-of-sources % (no fake done/total), and the summary uses the same overall mean as the national headline.
4. **Given** the visitor is on the coverage page, **When** they switch between Overall and By state, **Then** they can understand national coverage without leaving the page or authenticating.

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
- **FR-002**: The page MUST present national coverage in two tabs: **Overall** (national per-source table) and **By state** (per-state breakdown with a source filter that includes **Overall** plus each tracked job).
- **FR-003**: Coverage denominators MUST use the full included national universe (50 states + DC) from the county registry for county-grain sources — not “only counties already loaded into census.”
- **FR-004**: Scoring coverage MUST use county-grain done-ness consistent with national ingest redesign (every tract in the county has required safety source + non-empty score detail) against the national county total.
- **FR-005**: CMS and CMS Timely coverage MUST use state-grain totals for the included jurisdictions.
- **FR-006**: By-state coverage MUST use each state’s share of the national registry as the expected total for county-grain sources (and state-grain rules for CMS/Timely). When the filter is Overall, each state shows mean-of-sources % only (display formatting; API still returns per-source state stats).
- **FR-007**: Coverage data MUST be served by the product API as a read-only public contract; the web page MUST not query the database or invent completion math in the browser beyond display formatting (including mean-of-sources for the Overall filter).
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

- **SC-001**: A visitor can open `/coverage` without signing in and see overall and by-source national percentages (Overall tab) within a few seconds of a successful API response.
- **SC-002**: With a known partial nation, scoring and other county-grain sources never report near-100% solely because only a subset of states exist in tract tables — percentages stay consistent with full-registry denominators.
- **SC-003**: A visitor can identify at least one lagging source (Overall tab) and at least one lagging state (By state tab) from the page without operator tools or auth.
- **SC-004**: CMS/Timely rows use state-scale totals; county-grain sources use county-scale totals — verified by spot-check against known registry sizes.

## Assumptions

- Delivered on git branch `007-national-ingest-redesign` alongside national ingest redesign; Spec Kit feature directory is `008-national-coverage-dashboard`.
- Public path is `/coverage` because `/dashboard` is already the authenticated saved-lookups experience.
- Tracked sources match national ingest status jobs (census, epa, cms, fbi, nces, urban, acs, bls, fema, cms_timely, scoring).
- Completion rules align with `007` national status semantics (including scoring county grain).
- Page is informational (“roughly how much of the nation we cover”), not a live ops control panel; slight staleness from query time is acceptable.
- No auth, rate-limit productization, or caching product is required for v1 beyond normal API practices.
- Thin client / fat API: Next.js displays; FastAPI computes.
- UI has exactly two tabs (Overall, By state); source drill-down is a filter on By state, not a third tab.
