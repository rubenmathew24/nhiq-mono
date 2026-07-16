# Feature Specification: Report Sub-Scores & Category Detail

**Feature Branch**: `004-report-subscores`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Expand the report page so it shows major scores and sub-scores. Users can click a category to see extra stats. Blend seamlessly with the current UI and make clickability obvious. New workers and schema changes are allowed; document all proposed storage changes and the cost to convert existing data."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See dimension scores with sub-scores (Priority: P1)

A home buyer opens a neighborhood score report (including any of the local fixture / metro test addresses) and sees the overall score plus the five category scores. Under each category they also see the category’s **sub-scores** (smaller scores that explain how the category was built), without needing to click yet.

**Why this priority**: Today the breakdown only shows a single number and a short summary per category. Sub-scores are the minimum product upgrade that makes the report trustworthy and match how scores are actually composed.

**Independent Test**: Open a report that has live stored scores; confirm overall + five categories each show labeled sub-scores with numeric values; confirm layout still matches the existing report look (card, bars, typography).

**Acceptance Scenarios**:

1. **Given** a report with stored neighborhood scores, **When** the user views the score breakdown, **Then** each of Healthcare, Safety, Schools, Environment, and Economy shows its category score and at least the documented sub-scores for that category (see Key Entities).
2. **Given** the same report, **When** the user compares the category score to its sub-scores, **Then** the category score remains the authoritative category value already used for the overall score (sub-scores explain; they do not invent a second overall).
3. **Given** a report whose category still uses a documented default because inputs were missing, **When** the user views that category, **Then** sub-scores and detail still render with clear “limited data” / default messaging rather than blank or fake richness.

---

### User Story 2 - Expand a category for extra stats (Priority: P1)

A user understands that categories are interactive, clicks (or taps) a category, and sees an expanded panel of **extra stats** (nearest facilities, distances, ratings, rates, benchmarks, etc.) that blend with the current report card UI. Collapsing returns to the compact view.

**Why this priority**: Sub-scores alone are not enough for the “closest ER / how far / rating” experience the product wants; expand detail is the primary research-backed UX.

**Independent Test**: On a live report, expand Healthcare and Schools and verify concrete facility + distance + rating/ratio stats; expand all five categories and collapse again; confirm affordance is visible before the first click.

**Acceptance Scenarios**:

1. **Given** the score breakdown, **When** the user has not expanded anything yet, **Then** each category row/card clearly indicates it can be opened (e.g. chevron, “View details”, focusable control)—not only hover styling that fails on touch.
2. **Given** an unexpanded category, **When** the user activates it, **Then** an in-place expanded section appears under that category with the documented expand stats for that pillar, without navigating away from the report.
3. **Given** an expanded category, **When** the user activates it again (or chooses collapse), **Then** the detail hides and the compact category + sub-score view remains.
4. **Given** Healthcare expanded on a fixture address with nearby hospitals, **When** the user reads the detail, **Then** they see at least the nearest emergency facility name, distance, and star rating when those values exist in stored data.
5. **Given** Schools expanded with nearby schools, **When** the user reads the detail, **Then** they see at least the nearest school name, distance, and a staffing-related stat (e.g. pupil–teacher ratio) when available.

---

### User Story 3 - Richer environment & healthcare detail from new data (Priority: P2)

After hazard and ER-wait data are collected for the geographies the report covers, expanding Environment shows hazard context (e.g. flood / composite risk), and expanding Healthcare shows ER wait / timeliness context relative to state or national benchmarks when available.

**Why this priority**: These are the highest-value gaps versus marketing/mock promises (flood risk, ER waits). They require new collection jobs and storage, so they trail the P1 UI that can ship on existing data—but they are in scope for this feature so the report does not permanently omit them.

**Independent Test**: With hazard and timely-care data present for a test geography, open Environment and Healthcare expands and verify the new stats; with data absent, verify graceful limited-data messaging (not invented flood/wait numbers).

**Acceptance Scenarios**:

1. **Given** hazard data stored for the report’s census tract, **When** the user expands Environment, **Then** they see a hazard-related sub-score or equivalent labeled risk summary plus at least one concrete hazard fact (e.g. flood or composite risk band).
2. **Given** no hazard data for that tract, **When** the user expands Environment, **Then** air-quality stats still appear and hazard content shows a clear unavailable state (not a fabricated “Moderate flood”).
3. **Given** timely-care measures stored for nearby hospitals, **When** the user expands Healthcare, **Then** they see at least one ER wait / timeliness figure with state or national comparison when the source provides it.
4. **Given** timely-care data is missing for the nearest hospitals, **When** the user expands Healthcare, **Then** access/quality stats still appear and wait-time content shows unavailable rather than a mock wait.

---

### User Story 4 - Operator prepares data for detailed reports (Priority: P2)

An operator runs the documented collection and score-refresh path (including any new hazard / timely-care jobs) for the active local or metro geography set so expanded reports are backed by stored data—not live government calls at request time.

**Why this priority**: Constitution requires precomputed paths; expand UI is useless without operator-runnable ingest.

**Independent Test**: Follow the feature quickstart (once planned): run required jobs, open a fixture report, confirm new detail fields are populated.

**Acceptance Scenarios**:

1. **Given** a clean or partially filled database for the active geography scope, **When** the operator runs the documented ingest + score path for this feature, **Then** category detail for fixture reports becomes available without the web app calling government APIs directly.
2. **Given** an operator re-runs those jobs, **When** collection completes, **Then** stored detail updates idempotently (no duplicate identity corruption for the same facilities / tracts / measures).

---

### Edge Cases

- Report with overall/category scores but incomplete detail for one pillar → show available sub-scores/stats; mark missing pieces unavailable.
- Address with `SCORE_UNAVAILABLE` → unchanged: clear empty state; no fake expand content.
- Demo/mock-only report path (if still present for UI tests) → either updated to the new shape or clearly excluded from “live detail” claims.
- Very long facility names / many nearby facilities → expand shows a small ranked list (nearest first), not an unbounded dump.
- Touch / keyboard users → category activate works without hover; expanded region is reachable and dismissible.
- Safety detail → must remain neutral (no “safe/unsafe” steering language); agency/county grain is disclosed when crime is not tract-level.
- National vs metro scope → feature targets the **dev/local report experience** first; national ingest (003) may widen geography later without changing the report contract.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The report MUST display the overall neighborhood score and the five category scores (Healthcare, Safety, Schools/Education, Environment, Economy) consistent with stored scores for that address’s geography and active data vintage.
- **FR-002**: Each category MUST display its defined **sub-scores** with labels and numeric values (0–100 scale unless a documented exception applies for a specific sub-score).
- **FR-003**: Category rows MUST be activatable (click/tap/keyboard) to expand and collapse **extra stats** for that category in place on the report page.
- **FR-004**: Before any expand, the UI MUST make interactivity obvious (visible control affordance and accessible name such as “Expand healthcare details”), including on touch devices.
- **FR-005**: Expanded Healthcare MUST include nearest emergency facility identity, distance, and quality rating when stored; and ER wait / timeliness vs benchmark when that data has been collected.
- **FR-006**: Expanded Safety MUST include personal-crime and property-crime oriented stats versus a state (or documented) benchmark, plus which agencies contributed when available, with grain honesty (agency/county vs tract).
- **FR-007**: Expanded Schools MUST include nearest school identity, distance, and staffing/capacity-related stats when stored.
- **FR-008**: Expanded Environment MUST include air-quality summary (value and human-readable category/source honesty); and hazard risk summary when hazard data has been collected.
- **FR-009**: Expanded Economy MUST include tract median household income and county unemployment (or equivalent stored labor signal) when available.
- **FR-010**: Sub-scores and expand stats MUST be served from the product’s precomputed / stored path (no browser or request-time calls to government source APIs for these figures).
- **FR-011**: Missing inputs MUST yield clear unavailable or limited-data presentation for affected sub-scores/stats without inventing values presented as measured.
- **FR-012**: Visual language (typography, color tokens, spacing, card treatment) MUST remain consistent with the existing report page; expand detail MUST feel like part of the same breakdown card, not a separate product skin.
- **FR-013**: The system MUST collect and store **hazard (National Risk Index–class)** data needed for Environment expand/sub-score for the active local/metro geography set used to verify reports.
- **FR-014**: The system MUST collect and store **hospital timely/effective care (ER wait–class)** measures needed for Healthcare expand/sub-score for hospitals relevant to that geography set.
- **FR-015**: After new raw data lands, score/detail refresh MUST update reports for affected geographies so expand content matches storage (cache invalidation or equivalent so users are not stuck on stale thin reports).
- **FR-016**: Proposed storage changes for this feature MUST be documented for operators (see Proposed storage & conversion impact) including what is additive vs breaking and the effort to bring existing databases forward.
- **FR-017**: Pharmacy / urgent-care directory expansion (NPPES-class) is **out of scope** for this feature’s acceptance; Healthcare expand may mention hospitals/ERs only unless a later clarification pulls NPPES in.
- **FR-018**: Private listing-market sources (Zillow/Redfin) remain **out of scope**.

### Key Entities

- **Neighborhood report**: Overall score, five categories, narrative, vintage; extended with per-category sub-scores and expand detail.
- **Category score**: One of healthcare, safety, education/schools, environment, economic — weighted into overall as already published (25/25/20/15/15).
- **Sub-score**: Named component of a category (0–100). Required set:

  | Category | Sub-scores |
  |----------|------------|
  | Healthcare | Access (distance), Quality (star ratings), Timeliness (ER wait / timely care) when data exists |
  | Safety | Personal crime, Property crime |
  | Schools | Access (proximity), Staffing (pupil–teacher / capacity) |
  | Environment | Air quality; Hazard risk when data exists |
  | Economy | Income, Labor (unemployment) |

- **Expand stat**: Concrete labeled fact shown when a category is opened (facility name, miles, rating, AQI, income, unemployment %, offense vs state, agency list, hazard band, wait vs benchmark, etc.).
- **Hazard record**: Tract-level natural-hazard / risk index attributes used for Environment hazard sub-score and stats.
- **Timely-care measure**: Hospital-linked ER wait / timely & effective care measures used for Healthcare timeliness sub-score and stats.
- **Data vintage**: Label shared with existing scores so detail and scores stay aligned.

### Proposed storage & conversion impact *(operator-facing)*

This feature expects **additive** storage where possible so existing score rows and raw tables keep working during rollout.

| Change | Purpose | Impact on existing DBs | Conversion cost (order of magnitude) |
|--------|---------|------------------------|--------------------------------------|
| A. Extend score/detail payload (or sibling detail table) with sub-scores + expand facts per category | Serve report UI without re-querying raw tables on every click | Additive columns/JSON or new table keyed by tract + vintage; existing `neighborhood_scores` rows remain valid until re-score | **Low**: apply migration/SQL; **re-run scoring** for scored tracts (minutes–hours on metro fixture set; longer nationally). No full reload of CMS/EPA/FBI/schools required for A alone if scoring can derive detail from current raw tables. |
| B. New hazard table (tract risk + selected hazard bands) | Environment hazard sub-score/stats | New table only | **Medium**: one-time load for active geography (fixture/metro first). National later follows 003-style batches. No rewrite of existing score tables beyond re-score after load. |
| C. New timely-care / ER-wait measures table (hospital + measure + scores/benchmarks) | Healthcare timeliness | New table; join to existing hospitals by CMS facility id | **Medium**: ingest for hospitals already in `hospitals` (or state filter). Existing hospital rows unchanged. Re-score/detail refresh afterward. |
| D. Optional enrich of hospital/school rows (e.g. persist nearest-facility names already computable today into detail JSON) | Faster/stable expand | Prefer writing into score detail (A) over altering raw schemas | **Low** if kept in detail payload; **avoid** breaking changes to `hospitals` / `schools_*` PKs. |
| E. Breaking renames/drops of existing raw columns | — | **Not proposed** | N/A |

**Not required for P1 UI**: wiping or reshaping `epa_aqi_readings`, `crime_offense_monthly`, `schools_nces`, `schools_urban`, `acs_indicators`, or `bls_laus_county`. Those already hold most expand stats for Safety, Schools, Economy, and air quality.

**Operator sequence (conceptual)**: apply additive schema → run hazard + timely-care collection for active scope → re-run score/detail job → verify fixture reports → (later) widen geography with national ingest processes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a prepared fixture/metro report, a first-time tester can identify all five category scores and their sub-scores within 15 seconds without coaching.
- **SC-002**: On the same report, ≥90% of testers correctly identify that categories can be opened before their first expand (affordance test).
- **SC-003**: Expanding Healthcare on a prepared address shows nearest ER name, distance, and rating in under one interaction (single activate).
- **SC-004**: When hazard and timely-care data are prepared, Environment and Healthcare expands each show at least one new concrete stat that was not available on the pre-feature report.
- **SC-005**: When hazard or timely-care data is missing, users never see fabricated flood or wait figures presented as measured (unavailable/limited copy only).
- **SC-006**: Report page visual continuity: design review finds no new color system or unrelated card language vs the current report breakdown.
- **SC-007**: Existing metro/fixture score path still produces overall + category scores after schema apply; additive migration does not require dropping production-like local volumes to proceed.

## Assumptions

- Primary verification surface is the **local/dev report** only. Geography scope for new ingest + scoring is **`smoke`** (Benton County) and **`metro_10`** (the ten fixture metro counties)—not `national` / 003 batches.
- Sub-scores **explain** category composition; published category weights into overall stay as today unless a later product decision changes weights.
- Expand interaction is **in-place accordion-style** within the existing score breakdown card (not a separate route or modal-first design).
- Safety communication remains Fair Housing–aware: neutral wording; disclose agency/county grain.
- Open-Meteo remains allowed as modeled air-quality fallback; hazard content comes from FEMA NRI–class data, not invented from AQI.
- CMS Timely & Effective Care is in scope for wait/timeliness; HCAHPS and full Hospital Compare catalogs are deferred.
- NPPES pharmacy/urgent-care directory is deferred (FR-017).
- National geography expansion remains owned by `003-national-ingest`; this feature defines report contracts and local/metro collection for new sources.
- Mock demo report, if retained for tests, must not be confused with live detail in acceptance of live paths.
