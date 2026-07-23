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

### Edge Cases

- Place search returns no usable U.S. place: show a clear, user-facing error and do not open an empty locked map pretending success.
- Place resolves but bounding area is extremely large or tiny: still attempt the locked map; if the experience is unusable, show a clear message rather than a broken map.
- Very large number of tracts in the bounding area: map must remain usable (load and interact without appearing frozen for typical large U.S. cities); if limits are needed later, they are out of scope for inventing new geography types in this POC.
- User is signed in: Discover behaves the same as signed-out; **do not** save Discover searches to the user account or lookup history.
- Non-city place types selected from autocomplete (e.g. neighborhood or region): treat like any selected place using its search bounding area; do not special-case in this POC beyond clear labeling of what was selected.
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

### Key Entities

- **Discover place selection**: The city/place the user chose (display name + geographic bounding area used to lock the map).
- **Census tract region**: A geographic neighborhood unit with a stable public identifier and border shape.
- **Neighborhood overall score**: A single 0–100-style overall score for a tract when available; may be missing for some tracts.
- **Map presentation state**: Locked view, relative color legend for currently visible scored tracts, partial-coverage or empty-coverage messaging, and active tract popup.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new visitor can go from header → Discover → select a suggested U.S. place → see a locked map in under 2 minutes without creating an account.
- **SC-002**: For a place with scored tracts, at least 95% of usability testers can correctly identify which of two pointed-to tracts is higher-scoring using color + legend alone.
- **SC-003**: For a place with mixed coverage, testers recognize within 10 seconds that some areas lack scores (gray tracts and/or partial-coverage note).
- **SC-004**: For a place with no scored tracts, testers understand within 10 seconds that scored data is not available, without assuming the product is broken.
- **SC-005**: Map interaction (pan/zoom within lock, open tract popup) remains responsive for a typical large U.S. city demo place (no multi-second freezes on common laptop/browser setups used by the team).
- **SC-006**: Signed-in and signed-out sessions show the same Discover behavior; no Discover search appears in account lookup/history after use.

## Assumptions

- National tract shapes and overall scores already exist for a meaningful set of U.S. areas from prior ingest/scoring work; Discover surfaces what is already available rather than computing new scores on demand.
- “City” for this POC means whatever place the autocomplete returns, locked by that place’s search bounding area — not a separately curated city-boundary dataset.
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
