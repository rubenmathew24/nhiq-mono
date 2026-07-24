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

Below the map, the visitor sees a compact **city snapshot** for the place they searched: average overall score, highest and lowest scored tracts (with scores), scored vs total tract count, and the min–max overall score range. Snapshot stats MUST reflect tracts that belong to the **searched city**, not merely every tract drawn because it intersects the map lock box (which may include nearby non-city areas). **Clicking** the highest or lowest tract row in the summary focuses that tract on the map (dim other tracts + gentle fit within lock bounds) so the visitor can find it quickly. Highest/lowest rows MUST be placed near the top of the summary so the map stays visible while interacting with them. Hover on those rows MUST NOT change the map.

**Why this priority**: Turns the map into a readable city story and makes extremes discoverable without hunting.

**Independent Test**: Open a city whose map bbox includes extra surrounding tracts; confirm summary high/low/average match city-scoped tracts (not the full rendered overlay set); click highest/lowest rows and confirm map focus + dimming + gentle fit; click the active row again to clear; confirm high/low rows are visible without scrolling the map out of view.

**Acceptance Scenarios**:

1. **Given** a searched place with at least two scored city tracts, **When** the map page loads, **Then** a summary below the map shows city average overall, highest tract, lowest tract, scored/total counts, and min–max range for that city scope.
2. **Given** the summary shows a highest (or lowest) tract, **When** the visitor **clicks** that summary row, **Then** the map gently fits/pans to that tract within lock bounds, brings it into focus, and dims other tracts, and the active row shows selected styling plus a short “focused / click to clear” hint. **When** the visitor clicks the other high/low row, **Then** focus switches to that tract (hint moves with focus). **When** the visitor clicks the currently focused row again, **Then** focus clears, the hint/selection clears, and the map restores the normal choropleth / city framing. Hovering over high/low rows MUST NOT focus or clear the map.
3. **Given** the summary lists a highest or lowest tract, **When** the visitor reads the row, **Then** they see the overall score and a friendly label (with GEOID secondary), not GEOID alone as the only identifier, and the numeric score is colored with the product’s absolute score-quality colors (same bands as neighborhood report / dashboard scores)—not the map’s relative choropleth ramp.
4. **Given** the map page with a summary, **When** the visitor interacts with the highest or lowest row, **Then** those rows are positioned such that the map remains visible on a typical desktop viewport without scrolling it away.
5. **Given** zero scored city tracts, **When** the summary would render, **Then** it shows a clear empty/unavailable summary state (not fabricated highs/lows).
6. **Given** water-only census tracts in the place (e.g. Lake Michigan tracts with TIGER land area `ALAND = 0`), **When** the map and summary load, **Then** those tracts MUST NOT receive colored choropleth fills and MUST NOT set city average / highest / lowest / scored counts (they may be omitted from the FeatureCollection or flagged non-display; inhabited land tracts continue to color and drive the snapshot).
7. **Given** a city snapshot with average and min–max overall scores, **When** the visitor reads the snapshot headline, **Then** those numeric scores ALSO use the same absolute product score-quality colors as the highest/lowest row scores.

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
- Summary high/low focus: click/tap only (not hover). Clicking the other high/low row switches focus; clicking the active row again clears focus and restores city framing. Map pan/zoom or tract popups MUST NOT clear summary focus. Keyboard map-focus for high/low is OUT OF SCOPE for this POC (pointer/touch acceptance only).
- Water-only tracts (`census_tracts.aland = 0`, after 002/003 land/water ingest): MUST NOT paint as scored neighborhoods or appear as city high/low; if `aland` is NULL (migration/backfill pending), treat as land for display until backfill (honest ops gap — do not invent water status).
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
- **FR-008a**: Water-only tracts (`census_tracts.aland = 0`) MUST NOT receive relative score fills and MUST NOT count toward city snapshot average, highest, lowest, scored/total counts, or min–max. Implementation MAY omit them from the FeatureCollection or return them with an explicit non-display flag the client honors. Depends on 002/003 persisting `aland` (FR-004a / FR-006a).
- **FR-009**: If the place has zero scored tracts (or no tracts), the page MUST still show the locked basemap and a clear “no scored neighborhoods yet” message without a colored overlay.
- **FR-010**: Hover or click on a tract MUST show a popup with overall score when available, or an unavailable message when not; this POC MUST NOT navigate to the full neighborhood report from that popup.
- **FR-011**: Discover MUST NOT persist searches to user accounts, favorites, recent lookups, or similar history — including for signed-in users.
- **FR-012**: This POC MUST color **overall** score only (no dimension switcher). Future dimension filtering is expected later and MUST NOT be required for acceptance of this feature.
- **FR-013**: Errors (failed place resolution, temporary data failures) MUST show clear user-facing messages consistent with product error standards.
- **FR-014**: Below the map, the page MUST show a city snapshot summary: average overall score, highest scored tract, lowest scored tract, scored vs total tract counts, and min–max overall score range.
- **FR-015**: Snapshot statistics MUST be computed for tracts in the **searched city scope**: prefer an official/place boundary polygon when available; otherwise use a tighter core filter (e.g. tract centroids inside an inner shrink of the geocoder bounding box). Stats MUST NOT simply equal “all tracts intersecting the map lock box” when that would include non-city fringe. Stats MUST also exclude water-only tracts (`aland = 0`) even when they fall inside city scope.
- **FR-016**: Clicking the highest or lowest tract entry in the summary MUST focus that tract on the map and dim other tracts, and MUST gently fit/pan the map to that tract within the place lock bounds. Hover MUST NOT change focus. Clicking the other high/low row MUST switch focus to that tract. Clicking the currently focused row again MUST clear focus and restore the normal map presentation (including restoring the city-framed view). Desktop and touch use the same click/tap semantics (no hover-to-focus path).
- **FR-017**: When fewer than two scored city-scoped tracts exist, the summary MUST NOT invent a meaningful highest/lowest pair; it MUST show an honest empty or insufficient-data state for those fields.
- **FR-018**: Highest and lowest summary rows MUST show the overall score and a friendly place/area label when available, with the census tract GEOID secondary (not the sole primary label).
- **FR-018a**: Numeric overall scores shown in the city snapshot (average, highest, lowest, and min–max range values) MUST use the product’s **absolute** score-quality color bands—the same bands used for overall scores on neighborhood reports and the dashboard (e.g. higher scores read as “good,” mid-range as “mid,” lower as “poor”). These colors MUST NOT follow the map’s **relative** choropleth ramp (FR-007). Map fills remain relative; summary score text remains absolute.
- **FR-019**: The summary layout MUST place highest and lowest tract rows near the top of the report (immediately under any one-line city average / coverage headline) so that on a typical desktop viewport the map remains visible while the visitor interacts with those rows.
- **FR-020**: While a highest or lowest row is focused, that row MUST show a clear selected/pressed visual state **and** a short affordance hint (e.g. “Focused · click to clear”) so visitors can discover how to restore city framing. Unfocused high/low rows MUST NOT show that focused hint.

### Key Entities

- **Discover place selection**: The city/place the user chose (display name + geographic bounding area used to lock the map).
- **Census tract region**: A geographic neighborhood unit with a stable public identifier and border shape.
- **Neighborhood overall score**: A single 0–100-style overall score for a tract when available; may be missing for some tracts.
- **Map presentation state**: Locked view, relative color legend for currently visible scored tracts, partial-coverage or empty-coverage messaging, active tract popup, and optional highlight focus for a summary-selected tract.
- **City snapshot summary**: Aggregated overall-score stats for the searched city scope (average, high/low tracts, counts, min–max), shown below the map; numeric scores use absolute product score-quality colors.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new visitor can go from header → Discover → select a suggested U.S. place → see a locked map in under 2 minutes without creating an account.
- **SC-002**: For a place with scored tracts, at least 95% of usability testers can correctly identify which of two pointed-to tracts is higher-scoring using color + legend alone.
- **SC-003**: For a place with mixed coverage, testers recognize within 10 seconds that some areas lack scores (gray tracts and/or partial-coverage note).
- **SC-004**: For a place with no scored tracts, testers understand within 10 seconds that scored data is not available, without assuming the product is broken.
- **SC-005**: Map interaction (pan/zoom within lock, open tract popup) remains responsive for a typical large U.S. city demo place (no multi-second freezes on common laptop/browser setups used by the team).
- **SC-006**: Signed-in and signed-out sessions show the same Discover behavior; no Discover search appears in account lookup/history after use.
- **SC-007**: For a demo city with scored data, testers can name the highest and lowest overall scores from the below-map summary within 15 seconds without opening tract popups first.
- **SC-008**: When focusing the summary’s highest or lowest row by click/tap, at least 90% of testers correctly point to the matching focused tract on the map within 5 seconds.
- **SC-009**: On a standard laptop viewport (~1440×900), interacting with highest/lowest summary rows does not require scrolling the map out of view.
- **SC-010**: For Chicago (or another metro with water-only TIGER tracts), after census land/water backfill, Discover does not color Lake Michigan water-only tracts and does not list them as city highest/lowest.
- **SC-011**: For a demo city with a high overall (≥75-style) and a mid/low overall in the snapshot, testers recognize that summary score numbers use the same quality color language as report/dashboard scores (not merely “whatever is hottest on this map”).

## Assumptions

- National tract shapes and overall scores already exist for a meaningful set of U.S. areas from prior ingest/scoring work; Discover surfaces what is already available rather than computing new scores on demand.
- “City” for map lock still means the autocomplete place’s search bounding area. City **snapshot** membership is stricter: place polygon when available, else tighter core (centroid-in-inner-box), so summary highs/lows stay city-relevant.
- Relative coloring is computed among scored **land** tracts in the current view; gray unscored land tracts are excluded from the relative scale; water-only (`aland = 0`) tracts are excluded from fills and snapshot entirely.
- City snapshot **numeric** scores use absolute product score-quality colors (aligned with report/dashboard); map fills stay relative to the current view. Visitors may see a “lowest on this map” tract still colored “mid/good” in absolute terms, or a “highest” tract still “poor” absolute—that is intentional.
- Header Discover link is visible on the same public chrome as other marketing/product nav items (exact label: “Discover”).
- Mobile browsers are in scope for basic usability (search + map + popup), but desktop is the primary demo surface for the POC.
- Future dimension toggles and report deep-links are deferred; this spec does not require schema changes solely for those. Land/water columns live on `census_tracts` via 002/003 (not Discover-owned schema).
- Water-only filter rule: **`aland = 0`**. ACS population and tract-code 9900–9998 heuristics are not required for this amend.

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

### Session 2026-07-23 (post-implement UX fixes)

- Summary high/low hover: per-row `mouseLeave` cleared focus when crossing the gap → competing city vs tract `fitBounds`; fixed with list-level leave + `map.stop()` (research §13).
- Zoom-out floors differed (scroll too tight vs un-focus vs nav − too loose); fixed by locking `minZoom` + framed `maxBounds` after city `fitBounds`, scroll around center (research §15).

### Session 2026-07-23 (city summary expansion)

- Q: Which stats should the below-map summary include? → A: Snapshot pack (city average overall; highest tract; lowest tract; scored vs total tract count; min–max range) **plus** hover on highest/lowest report rows focuses that tract on the map and dims other tracts so it is easy to identify.
- Q: How are “in the searched city” tracts chosen for snapshot stats? → A: Place polygon when available; otherwise a tighter core (e.g. centroids inside an inner shrink of the geocoder box) so stats stay city-relevant, not full map-bbox fringe.
- Q: How are highest/lowest tracts labeled in the summary? → A: Score + friendly label + GEOID secondary (name/area when available; otherwise abbreviated location + GEOID).
- Q: Touch devices without hover? → A: Tap summary row to focus/dim; tap elsewhere or tap again to clear.
- Q: Does focusing a high/low tract pan/zoom the map? → A: Gentle fit/pan to the focused tract (within lock bounds), plus highlight/dim.
- Q: Summary layout vs map visibility on hover? → A: Highest/lowest rows MUST sit high enough in the report that the map remains visible while hovering those rows (no scrolling the map off-screen to reach them).

### Session 2026-07-23 (water-only tracts)

- Q: Should Discover paint water-only census tracts (e.g. Lake Michigan)? → A: **No** — exclude from choropleth fills and from city snapshot average/high/low/counts.
- Q: How is water-only defined? → A: **`census_tracts.aland = 0`** (TIGER land area). Depends on 002/003 persisting `ALAND`/`AWATER`. Tract-code heuristics and ACS population filters are out of scope for this amend.
- Q: If `aland` is still NULL (pre-backfill)? → A: Treat as displayable land tract until backfill; do not invent water status from GEOID alone.

### Session 2026-07-23 (summary focus = click)

- Q: How should the visitor clear Highest/Lowest map focus? → A: **B** — click a row to focus; click the other switches focus; click the active row again clears and restores city framing. Hover does not focus or clear.
- Q: Should the active high/low row show selected styling? → A: **C** — selected/pressed visual state plus a short “Focused · click to clear” (or equivalent) hint on the active row.
- Q: Keyboard support for high/low focus? → A: **B** — pointer/touch only for this POC; no keyboard map-focus requirement (native button activation may still fire click where the control is a `<button>`).

### Session 2026-07-23 (snapshot score colors)

- Q: Should city snapshot score numbers use map-relative colors or product score colors? → A: **Product absolute score-quality colors** (same bands as neighborhood report / dashboard overall scores) for average, highest, lowest, and min–max numerics. Map choropleth fills remain relative (FR-007).
