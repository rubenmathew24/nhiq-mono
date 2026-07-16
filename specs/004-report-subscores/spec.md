# Feature Specification: Report Sub-Scores & Category Detail

**Feature Branch**: `004-report-subscores`

**Created**: 2026-07-16

**Status**: Draft (UX polish revision 2026-07-16)

**Input**: User description: "Expand the report page so it shows major scores and sub-scores. Users can click a category to see extra stats. Blend seamlessly with the current UI and make clickability obvious. New workers and schema changes are allowed; document all proposed storage changes and the cost to convert existing data."

**Revision input (post-implement explore)**: Category boxes instead of subtle “View details”; plain-English labels; ER wait coloring aligned to score tiers; Safety/Environment/Schools expand copy cleanup; Schools by level (not single nearest + PTR/locale); Economy keep current + one/two glanceable ACS extras.

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

A user understands that **each category is an obvious interactive box**, clicks (or taps) the box, and sees an expanded panel of **extra stats** in plain English (nearest facilities, distances, ratings, rates, benchmarks, etc.) that blend with the current report card UI. Collapsing returns to the compact view.

**Why this priority**: Sub-scores alone are not enough for the “closest ER / how far / rating” experience the product wants; expand detail is the primary research-backed UX.

**Independent Test**: On a live report, expand Healthcare and Schools and verify concrete facility + distance + rating stats; expand all five categories and collapse again; confirm each category reads as a tappable/clickable box before the first click (not a muted text link).

**Acceptance Scenarios**:

1. **Given** the score breakdown, **When** the user has not expanded anything yet, **Then** each category is presented as a distinct interactive box (visible border/surface + clear hover highlight) whose **entire surface** is focusable and activatable—not only the title row or a subtle “View details” text link.
2. **Given** an unexpanded category box, **When** the user activates it (click/tap anywhere on the box), **Then** an in-place expanded section appears under that category with the documented expand stats for that pillar, without navigating away from the report.
3. **Given** an expanded category, **When** the user activates it again (or chooses collapse), **Then** the detail hides and the compact category + sub-score view remains.
4. **Given** Healthcare expanded on a fixture address with nearby hospitals, **When** the user reads the detail, **Then** they see the nearest emergency facility plus up to two more ranked ERs labeled as **2nd nearest ER** / **3rd nearest ER** (not “Also nearby”), each with distance and star rating when stored; missing ratings show **`★-`**.
5. **Given** Healthcare expanded with an ER wait figure, **When** the wait is at or worse than state/national benchmarks (e.g. Bentonville ~162 min slightly above national), **Then** the wait value’s color uses the same good/mid/poor tiering as the score bar—not a misleading “good” (green) tint.
6. **Given** Schools expanded, **When** the user reads the detail, **Then** they see nearest-distance (and name when available) for each available school level bucket within **25 miles**—not a single “nearest school,” not pupil–teacher ratio or locale codes, and not schools hundreds of miles away.
7. **Given** Safety expanded, **When** the user reads the detail, **Then** offense labels are full plain English (e.g. Homicide, Robbery, Assault—never `ASS` / `HOM` codes), the violent-crime comparison describes intensity **vs the state average per resident** (not share of statewide totals), and geography + reporting agencies are condensed.
8. **Given** Environment expanded, **When** the user reads air-quality stats, **Then** copy does **not** expose internal source ids such as `open_meteo` to the end user.
9. **Given** Economy expanded, **When** the user reads the detail, **Then** they still see median household income and county unemployment, plus the documented extra glanceable ACS labor stats (plain English).

---

### User Story 3 - Richer environment & healthcare detail from new data (Priority: P2)

After hazard and ER-wait data are collected for the geographies the report covers, expanding Environment shows hazard context (e.g. flood / composite risk), and expanding Healthcare shows ER wait / timeliness context relative to state or national benchmarks when available.

**Why this priority**: These are the highest-value gaps versus marketing/mock promises (flood risk, ER waits). They require new collection jobs and storage, so they trail the P1 UI that can ship on existing data—but they are in scope for this feature so the report does not permanently omit them.

**Independent Test**: With hazard and timely-care data present for a test geography, open Environment and Healthcare expands and verify the new stats; with data absent, verify graceful limited-data messaging (not invented flood/wait numbers).

**Acceptance Scenarios**:

1. **Given** hazard data stored for the report’s census tract, **When** the user expands Environment, **Then** they see a hazard-related sub-score or equivalent labeled risk summary plus at least one concrete hazard fact (e.g. flood or composite risk band).
2. **Given** no hazard data for that tract, **When** the user expands Environment, **Then** air-quality stats still appear and hazard content shows a clear unavailable state (not a fabricated “Moderate flood”).
3. **Given** timely-care measures stored for nearby hospitals, **When** the user expands Healthcare, **Then** they see at least one ER wait / timeliness figure with state or national comparison when the source provides it, colored with score-bar tiers.
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
- Touch / keyboard users → category box activate works without hover; expanded region is reachable and dismissible.
- Safety detail → must remain neutral (no “safe/unsafe” steering language); agency/county grain is disclosed briefly when crime is not tract-level.
- School level missing for a type → omit that row or show unavailable for that level; do not invent a school.
- Nearest school for a level beyond 25 miles → treat as not found for expand (no absurd distances).
- Zoning / attendance boundaries → **out of scope**; never imply the listed school is “your assigned school.”
- Violent crime “× state” absolute share → **not** allowed as user-facing meaning; use per-resident intensity.
- National vs metro scope → feature targets the **dev/local report experience** first; national ingest (003) may widen geography later without changing the report contract.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The report MUST display the overall neighborhood score and the five category scores (Healthcare, Safety, Schools/Education, Environment, Economy) consistent with stored scores for that address’s geography and active data vintage.
- **FR-002**: Each category MUST display its defined **sub-scores** with labels and numeric values (0–100 scale unless a documented exception applies for a specific sub-score).
- **FR-003**: Category rows MUST be activatable (click/tap/keyboard) to expand and collapse **extra stats** for that category in place on the report page.
- **FR-004**: Before any expand, each category MUST render as an **obvious interactive box**. The **entire box** (title, score bar, sub-scores, summary, and expanded panel chrome) MUST be one activatable control. Hover MUST apply a clear highlight (stronger than a near-invisible muted wash) so clickability is obvious. Subtle text-only “View details” links are not sufficient.
- **FR-005**: Expanded Healthcare MUST include nearest emergency facility identity, distance, and quality rating when stored; up to two additional ERs labeled **2nd nearest ER** / **3rd nearest ER**; and ER wait / timeliness vs benchmark when collected. Wait (and other scored expand values that use tone) MUST use the same good/mid/poor color tiers as the score bar (`scoreTier`: ≥75 / ≥50 / else). When an ER has no star rating, the value MUST still include a star placeholder **`★-`** so rows align visually with rated ERs.
- **FR-006**: Expanded Safety MUST use plain-English labels for crime types and comparisons (no raw CDE offense codes such as `ASS`); personal/property meaning MUST be glanceable without developer jargon; geography note and reporting agencies MUST be condensed (short combined lines, not a long list of separate agency rows). The violent-crime comparison MUST express **intensity vs the state average on a per-resident basis** (how this area compares to typical places in the state)—NOT the county’s share of statewide absolute incident totals. Wording MUST stay Fair Housing–neutral (e.g. lower/higher than state average per resident; no “safe/unsafe neighborhood” steering).
- **FR-007**: Expanded Schools MUST list nearest public school **by level** (Pre-K, Elementary, Middle, Junior High, High—whichever levels exist in stored data for the area), with name and distance when available, **only if that school is within `SCHOOL_MAX_EXPAND_MILES` (25 miles)**. Beyond that cutoff, that level MUST show a clear **No schools found** (or equivalent) rather than an absurd distant facility. MUST NOT show pupil–teacher ratio or locale codes. MUST NOT claim zoning/assignment. Staffing sub-score may remain limited-data until a zoning-backed signal exists.
- **FR-008**: Expanded Environment MUST include air-quality summary in plain English (value + human-readable category); MUST NOT surface internal source identifiers such as `open_meteo` in user-visible copy; and hazard risk summary when hazard data has been collected.
- **FR-009**: Expanded Economy MUST include tract median household income and county unemployment when available, plus **tract employment rate** (share of labor force employed from existing ACS columns) as an additional glanceable labor stat.
- **FR-010**: Sub-scores and expand stats MUST be served from the product’s precomputed / stored path (no browser or request-time calls to government source APIs for these figures).
- **FR-011**: Missing inputs MUST yield clear unavailable or limited-data presentation for affected sub-scores/stats without inventing values presented as measured.
- **FR-012**: Visual language (typography, color tokens, spacing) MUST remain consistent with the existing report page; category boxes and expand detail MUST feel like part of the same breakdown card, not a separate product skin.
- **FR-013**: The system MUST collect and store **hazard (National Risk Index–class)** data needed for Environment expand/sub-score for the active local/metro geography set used to verify reports.
- **FR-014**: The system MUST collect and store **hospital timely/effective care (ER wait–class)** measures needed for Healthcare expand/sub-score for hospitals relevant to that geography set.
- **FR-015**: After new raw data lands, score/detail refresh MUST update reports for affected geographies so expand content matches storage (cache invalidation or equivalent so users are not stuck on stale thin reports).
- **FR-016**: Proposed storage changes for this feature MUST be documented for operators (see Proposed storage & conversion impact) including what is additive vs breaking and the effort to bring existing databases forward.
- **FR-017**: Pharmacy / urgent-care directory expansion (NPPES-class) is **out of scope** for this feature’s acceptance; Healthcare expand may mention hospitals/ERs only unless a later clarification pulls NPPES in.
- **FR-018**: Private listing-market sources (Zillow/Redfin) remain **out of scope**.
- **FR-019**: All user-visible expand labels and values MUST be plain English suitable for a non-technical buyer glance—no raw API codes, internal source ids, or abbreviations that read as unprofessional (e.g. `ASS` for assault).
- **FR-020**: Safety personal-crime scoring and expand comparison MUST use a **population-normalized** local-vs-state intensity ratio (incidents per resident / per 100k), not raw county counts divided by raw statewide counts.

### Key Entities

- **Neighborhood report**: Overall score, five categories, narrative, vintage; extended with per-category sub-scores and expand detail.
- **Category score**: One of healthcare, safety, education/schools, environment, economic — weighted into overall as already published (25/25/20/15/15).
- **Category box**: Interactive UI container for one category (score + sub-scores + expand panel).
- **Sub-score**: Named component of a category (0–100). Required set:

  | Category | Sub-scores |
  |----------|------------|
  | Healthcare | Access (distance), Quality (star ratings), Timeliness (ER wait / timely care) when data exists |
  | Safety | Crimes against people, Crimes against property (user-facing labels; ids may remain `personal` / `property`) |
  | Schools | Access (proximity by school level); Staffing limited-data until zoning-backed signal exists |
  | Environment | Air quality; Hazard risk when data exists |
  | Economy | Income, Labor (unemployment) |

- **Expand stat**: Concrete labeled fact shown when a category is opened—plain English only.
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
| F. UX polish rewrite of `score_detail` stats labels/shape (ER ordinals, safety copy, schools-by-level, hide source ids, employment rate) | Plain-English expand | No new tables; re-score writes new JSON | **Low**: re-run `worker-scoring` for smoke/metro_10 after code change |

**Not required for P1 UI**: wiping or reshaping `epa_aqi_readings`, `crime_offense_monthly`, `schools_nces`, `schools_urban`, `acs_indicators`, or `bls_laus_county`. Those already hold most expand stats for Safety, Schools, Economy, and air quality.

**Operator sequence (conceptual)**: apply additive schema → run hazard + timely-care collection for active scope → re-run score/detail job → verify fixture reports → (later) widen geography with national ingest processes. After UX polish: re-run score/detail only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a prepared fixture/metro report, a first-time tester can identify all five category scores and their sub-scores within 15 seconds without coaching.
- **SC-002**: On the same report, ≥90% of testers correctly identify that categories can be opened before their first expand (affordance test)—boxes must look clickable without reading microcopy.
- **SC-003**: Expanding Healthcare on a prepared address shows nearest ER name, distance, and rating in under one interaction (single activate); 2nd/3rd nearest use ordinal labels.
- **SC-004**: When hazard and timely-care data are prepared, Environment and Healthcare expands each show at least one new concrete stat that was not available on the pre-feature report.
- **SC-005**: When hazard or timely-care data is missing, users never see fabricated flood or wait figures presented as measured (unavailable/limited copy only).
- **SC-006**: Report page visual continuity: design review finds no new color system or unrelated card language vs the current report breakdown (category boxes may use existing border/muted tokens).
- **SC-007**: Existing metro/fixture score path still produces overall + category scores after schema apply; additive migration does not require dropping production-like local volumes to proceed.
- **SC-008**: Non-technical reviewer finds no raw offense codes, locale codes, or `open_meteo`-style source ids in expand panels on the Bentonville fixture report.
- **SC-009**: Bentonville ER wait that is at/above national average does not render in the score-bar “good” (green) tier.
- **SC-010**: Bentonville Safety expand does not present violent crime as a tiny “× state” share-of-state-totals figure; comparison reads as vs state average **per resident** (or equivalent plain intensity language).
- **SC-011**: Schools expand never lists a facility farther than 25 miles; levels beyond cutoff show no-schools-found copy (Bentonville must not show ~457 mi Pre-K).
- **SC-012**: Hovering a category box shows a clearly stronger highlight than the pre-polish muted wash; clicking outside the title (e.g. on sub-score area) still toggles expand.

## Assumptions

- Primary verification surface is the **local/dev report** only. Geography scope for new ingest + scoring is **`smoke`** (Benton County) and **`metro_10`** (the ten fixture metro counties)—not `national` / 003 batches.
- Sub-scores **explain** category composition; published category weights into overall stay as today unless a later product decision changes weights.
- Expand interaction is **in-place accordion-style** within the existing score breakdown, with each category as an interactive box (not a separate route or modal-first design).
- Safety communication remains Fair Housing–aware: neutral wording; disclose agency/county grain briefly.
- Open-Meteo remains allowed as modeled air-quality fallback internally; user-visible Environment copy omits the source id (product may revisit source honesty copy later).
- CMS Timely & Effective Care is in scope for wait/timeliness; HCAHPS and full Hospital Compare catalogs are deferred.
- NPPES pharmacy/urgent-care directory is deferred (FR-017).
- School attendance zoning is out of scope; proximity-by-level is the Schools expand contract.
- **`SCHOOL_MAX_EXPAND_MILES` = 25** for expand listing (access sub-score may still use in-range schools only).
- Economy extra stats use **existing** ACS columns already in `acs_indicators` (no new Census variable ingest in this polish) except as needed for **county/state population** to normalize safety rates (ACS B01003 or equivalent).
- National geography expansion remains owned by `003-national-ingest`; this feature defines report contracts and local/metro collection for new sources.
- Mock demo report, if retained for tests, must not be confused with live detail in acceptance of live paths.

## Clarifications

### Session 2026-07-16 (UX explore → re-plan)

- Category affordance → interactive **boxes**, not subtle “View details.”
- Healthcare ER list → ordinal labels (`2nd nearest ER`, `3rd nearest ER`); ER wait color → score-bar tiers; fix misleading green when wait ≈/above national.
- Safety → plain-English crime labels; condense geography + agencies.
- Environment → hide `open_meteo` (and similar) from stats copy.
- Schools → nearest by level; drop PTR and locale; no zoning claims; staffing sub-score limited until zoning.
- Economy → keep income + unemployment; add tract employment rate from existing ACS labor fields.

### Session 2026-07-16 (UX polish round 2)

- Safety violent-crime line → **per-resident vs state average** meaning (not share of statewide absolute totals); update score ratio accordingly.
- Healthcare → missing ER stars render as **`★-`** for column alignment.
- Schools → **25 mi** max expand distance; beyond → no schools found for that level.
- Category box → **entire box** clickable; **stronger hover** highlight.
