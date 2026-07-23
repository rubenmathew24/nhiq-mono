# Feature Specification: Discover Mode (City Score Map)

**Feature Branch**: `008-discover-mode`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Build a new Discover mode accessible via a new header tab/page. Users search a city/state (e.g. Boston, MA) and land on a map locked to that region, with census tracts overlaid and colored by overall neighborhood score. POC — research feasibility."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open Discover and search a city (Priority: P1)

A visitor opens Discover from the site header, searches for a U.S. city/place with autocomplete (e.g. “Boston, MA”), and is taken to a Discover map page for that place.

**Why this priority**: Without search → map navigation, the mode does not exist.

**Independent Test**: From the header, open Discover, pick a suggested place, and confirm a map page loads for that place name.

**Acceptance Scenarios**:

1. **Given** a visitor is on any public page with the site header, **When** they click the Discover tab, **Then** they reach a Discover entry experience with city/place search.
2. **Given** the visitor types at least a few characters of a U.S. place name, **When** suggestions appear, **Then** they can select a city/place and proceed to the map for that selection.
3. **Given** a place is selected, **When** the map page opens, **Then** the page identifies the chosen place (e.g. title or label) and shows a map focused on that area.

---

### User Story 2 - Explore scored census tracts on a locked map (Priority: P1)

On the Discover map page, the visitor sees census tract boundaries inside the locked view, colored by how high each tract’s overall neighborhood score is **relative to other tracts currently shown**. Unscored tracts appear in a neutral style. The map cannot be freely explored far outside the place’s search bounding area.

**Why this priority**: The choropleth and region lock are the core product value of Discover.

**Independent Test**: Open a place known to have mixed scored/unscored tracts; confirm colors, lock behavior, legend, and partial-coverage messaging without using search history or account features.

**Acceptance Scenarios**:

1. **Given** a place whose bounding area contains scored tracts, **When** the map loads, **Then** tract borders are visible and filled according to relative overall-score ranking among tracts currently on the map, with a legend that explains the relative scale.
2. **Given** the map is showing a place, **When** the visitor tries to pan or zoom substantially outside the place’s search bounding area, **Then** the view remains constrained so the focus stays on that place.
3. **Given** some tracts in view have scores and some do not, **When** the map renders, **Then** unscored tracts appear in a neutral gray, scored tracts remain colored, and a non-blocking note indicates partial coverage.
4. **Given** the place resolves but no tract in the area has a score (or no tracts are available), **When** the map page loads, **Then** the visitor still sees the locked basemap plus a clear message that no scored neighborhoods are available yet (no colored tract overlay).

---

### User Story 3 - Inspect a tract’s overall score (Priority: P2)

The visitor can hover or click a tract to see a simple popup with the overall score (and tract identity if useful). This POC does not navigate to a full neighborhood report.

**Why this priority**: Makes the colors interpretable without expanding into report deep-links.

**Independent Test**: Interact with a scored tract and an unscored tract; confirm popup content differs appropriately; confirm no navigation to a report page.

**Acceptance Scenarios**:

1. **Given** a scored tract is visible, **When** the visitor hovers or clicks it, **Then** a popup shows the overall neighborhood score for that tract.
2. **Given** an unscored tract is visible, **When** the visitor hovers or clicks it, **Then** the popup indicates the score is unavailable.
3. **Given** any tract popup is shown, **When** the visitor dismisses it or selects another tract, **Then** they remain on the Discover map page (no report navigation in this POC).

---

### User Story 4 - City summary under the map (Priority: P2)

Below the map, the visitor sees a compact **city snapshot** for the place they searched: average overall score, highest and lowest scored tracts (with scores), scored vs total tract count, and the min–max overall score range. Snapshot stats MUST reflect tracts that belong to the **searched city**, not merely every tract drawn because it intersects the map lock box (which may include nearby non-city areas). Interacting with the highest or lowest tract row in the summary focuses that tract on the map (dim other tracts + gentle fit within lock bounds) so the visitor can find it quickly. Highest/lowest rows MUST be placed near the top of the summary so the map stays visible while interacting with them.

**Why this priority**: Turns the map into a readable city story and makes extremes discoverable without hunting.

**Independent Test**: Open a city whose map bbox includes extra surrounding tracts; confirm summary high/low/average match city-scoped tracts (not the full rendered overlay set); hover/tap highest/lowest rows and confirm map focus + dimming + gentle fit; confirm high/low rows are visible without scrolling the map out of view.

**Acceptance Scenarios**:

1. **Given** a searched place with at least two scored city tracts, **When** the map page loads, **Then** a summary below the map shows city average overall, highest tract, lowest tract, scored/total counts, and min–max range for that city scope.
2. **Given** the summary shows a highest (or lowest) tract, **When** the visitor hovers (desktop) or taps (touch) that summary row, **Then** the map gently fits/pans to that tract within lock bounds, brings it into focus, and dims other tracts; when hover ends or focus is cleared on touch, the map returns to the normal choropleth presentation (city framing restored as appropriate).
3. **Given** the summary lists a highest or lowest tract, **When** the visitor reads the row, **Then** they see the overall score and a friendly label (with GEOID secondary), not GEOID alone as the only identifier.
4. **Given** the map page with a summary, **When** the visitor interacts with the highest or lowest row, **Then** those rows are positioned such that the map remains visible on a typical desktop viewport without scrolling it away.
5. **Given** zero scored city tracts, **When** the summary would render, **Then** it shows a clear empty/unavailable summary state (not fabricated highs/lows).

---

### Edge Cases

- Place search returns no usable U.S. place: show a clear, user-facing error and do not open an empty locked map pretending success.
- Place resolves but bounding area is extremely large or tiny: still attempt the locked map; if the experience is unusable, show a clear message rather than a broken map.
- Very large number of tracts in the bounding area: map must remain usable (load and interact without appearing frozen for typical large U.S. cities); if limits are needed later, they are out of scope for inventing new geography types in this POC.
- User is signed in: Discover behaves the same as signed-out; **do not** save Discover searches to the user account or lookup history.
- Non-city place types selected from autocomplete (e.g. neighborhood or region): treat like any selected place using its search bounding area; do not special-case in this POC beyond clear labeling of what was selected.
- Map bbox includes suburbs outside the city: map may still show those tracts; city snapshot stats MUST use city scope (polygon or tighter core), not the full overlay set.
- Place polygon unavailable: fall back to tighter-core membership without failing the page.
- Focused tract outside current zoom: gentle fit must stay within map lock bounds and not unlock free exploration.
- Dimension toggles (healthcare, schools, etc.): **out of scope** for this POC; only overall score is shown. Future work may add dimensions without changing the public entry pattern.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST expose Discover via a new header navigation item that links to a Discover webpage.
- **FR-002**: Discover MUST be usable without signing in (public proof-of-concept).
- **FR-003**: Discover MUST provide U.S. city/place search with place autocomplete suggestions.
- **FR-004**: Selecting a place MUST take the user to a Discover map page scoped to that place.
- **FR-005**: The map view MUST be locked to the place’s search bounding area so users cannot meaningfully explore far outside that area.
- **FR-006**: Inside the locked view, the system MUST overlay census tract borders for tracts that intersect the bounding area (when tract shapes are available).
- **FR-007**: Tract fills MUST encode the **overall** neighborhood score using a **relative** scale among tracts currently shown on the map; a legend MUST explain that colors are relative to the current view.
- **FR-008**: Tracts without an overall score MUST render in a neutral gray; when any unscored tracts are present alongside scored ones, the page MUST show a non-blocking partial-coverage note.
- **FR-009**: If the place has zero scored tracts (or no tracts), the page MUST still show the locked basemap and a clear “no scored neighborhoods yet” message without a colored overlay.
- **FR-010**: Hover or click on a tract MUST show a popup with overall score when available, or an unavailable message when not; this POC MUST NOT navigate to the full neighborhood report from that popup.
- **FR-011**: Discover MUST NOT persist searches to user accounts, favorites, recent lookups, or similar history — including for signed-in users.
- **FR-012**: This POC MUST color **overall** score only (no dimension switcher). Future dimension filtering is expected later and MUST NOT be required for acceptance of this feature.
- **FR-013**: Errors (failed place resolution, temporary data failures) MUST show clear user-facing messages consistent with product error standards.
- **FR-014**: Below the map, the page MUST show a city snapshot summary: average overall score, highest scored tract, lowest scored tract, scored vs total tract counts, and min–max overall score range.
- **FR-015**: Snapshot statistics MUST be computed for tracts in the **searched city scope**: prefer an official/place boundary polygon when available; otherwise use a tighter core filter (e.g. tract centroids inside an inner shrink of the geocoder bounding box). Stats MUST NOT simply equal “all tracts intersecting the map lock box” when that would include non-city fringe.
- **FR-016**: Interacting with the highest or lowest tract entry in the summary MUST focus that tract on the map and dim other tracts, and MUST gently fit/pan the map to that tract within the place lock bounds. On pointer devices interaction is hover (clears on hover end). On touch devices interaction is tap-to-focus; tap again or tap elsewhere clears focus and restores the normal map presentation (including restoring the city-framed view as appropriate).
- **FR-017**: When fewer than two scored city-scoped tracts exist, the summary MUST NOT invent a meaningful highest/lowest pair; it MUST show an honest empty or insufficient-data state for those fields.
- **FR-018**: Highest and lowest summary rows MUST show the overall score and a friendly place/area label when available, with the census tract GEOID secondary (not the sole primary label).
- **FR-019**: The summary layout MUST place highest and lowest tract rows near the top of the report (immediately under any one-line city average / coverage headline) so that on a typical desktop viewport the map remains visible while the visitor interacts with those rows.

### Key Entities

- **Discover place selection**: The city/place the user chose (display name + geographic bounding area used to lock the map).
- **Census tract region**: A geographic neighborhood unit with a stable public identifier and border shape.
- **Neighborhood overall score**: A single 0–100-style overall score for a tract when available; may be missing for some tracts.
- **Map presentation state**: Locked view, relative color legend for currently visible scored tracts, partial-coverage or empty-coverage messaging, active tract popup, and optional highlight focus for a summary-selected tract.
- **City snapshot summary**: Aggregated overall-score stats for the searched city scope (average, high/low tracts, counts, min–max), shown below the map.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new visitor can go from header → Discover → select a suggested U.S. place → see a locked map in under 2 minutes without creating an account.
- **SC-002**: For a place with scored tracts, at least 95% of usability testers can correctly identify which of two pointed-to tracts is higher-scoring using color + legend alone.
- **SC-003**: For a place with mixed coverage, testers recognize within 10 seconds that some areas lack scores (gray tracts and/or partial-coverage note).
- **SC-004**: For a place with no scored tracts, testers understand within 10 seconds that scored data is not available, without assuming the product is broken.
- **SC-005**: Map interaction (pan/zoom within lock, open tract popup) remains responsive for a typical large U.S. city demo place (no multi-second freezes on common laptop/browser setups used by the team).
- **SC-006**: Signed-in and signed-out sessions show the same Discover behavior; no Discover search appears in account lookup/history after use.
- **SC-007**: For a demo city with scored data, testers can name the highest and lowest overall scores from the below-map summary within 15 seconds without opening tract popups first.
- **SC-008**: When focusing the summary’s highest or lowest row (hover or tap), at least 90% of testers correctly point to the matching focused tract on the map within 5 seconds.
- **SC-009**: On a standard laptop viewport (~1440×900), interacting with highest/lowest summary rows does not require scrolling the map out of view.

## Assumptions

- National tract shapes and overall scores already exist for a meaningful set of U.S. areas from prior ingest/scoring work; Discover surfaces what is already available rather than computing new scores on demand.
- “City” for map lock still means the autocomplete place’s search bounding area. City **snapshot** membership is stricter: place polygon when available, else tighter core (centroid-in-inner-box), so summary highs/lows stay city-relevant.
- Relative coloring is computed among scored tracts in the current view; gray tracts are excluded from the relative scale.
- Header Discover link is visible on the same public chrome as other marketing/product nav items (exact label: “Discover”).
- Mobile browsers are in scope for basic usability (search + map + popup), but desktop is the primary demo surface for the POC.
- Future dimension toggles and report deep-links are deferred; this spec does not require schema changes solely for those.

## Clarifications

### Session 2026-07-23

- Q: Who can use Discover in v1? → A: Public (no sign-in). POC; do not save Discover searches even if logged in.
- Q: What geography locks the map for “Boston, MA”? → A: Search-result bounding box from the place geocoder/autocomplete selection.
- Q: Tract interaction? → A: Hover/click popup with overall score; no report navigation.
- Q: Partial score coverage? → A: Gray unscored tracts + soft partial-coverage banner.
- Q: Color mapping? → A: Relative among tracts currently shown on the map.
- Q: Search UX? → A: Place autocomplete for U.S. cities/places.
- Q: Zero scored tracts? → A: Still show locked basemap + clear empty message (no overlay).
- Q: Overall vs dimensions? → A: Overall only for POC; dimensions likely later.

### Session 2026-07-23 (city summary expansion)

- Q: Which stats should the below-map summary include? → A: Snapshot pack (city average overall; highest tract; lowest tract; scored vs total tract count; min–max range) **plus** hover on highest/lowest report rows focuses that tract on the map and dims other tracts so it is easy to identify.
- Q: How are “in the searched city” tracts chosen for snapshot stats? → A: Place polygon when available; otherwise a tighter core (e.g. centroids inside an inner shrink of the geocoder box) so stats stay city-relevant, not full map-bbox fringe.
- Q: How are highest/lowest tracts labeled in the summary? → A: Score + friendly label + GEOID secondary (name/area when available; otherwise abbreviated location + GEOID).
- Q: Touch devices without hover? → A: Tap summary row to focus/dim; tap elsewhere or tap again to clear.
- Q: Does focusing a high/low tract pan/zoom the map? → A: Gentle fit/pan to the focused tract (within lock bounds), plus highlight/dim.
- Q: Summary layout vs map visibility on hover? → A: Highest/lowest rows MUST sit high enough in the report that the map remains visible while hovering those rows (no scrolling the map off-screen to reach them).
