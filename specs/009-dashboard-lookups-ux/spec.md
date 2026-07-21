# Feature Specification: Dashboard Lookups UX

**Feature Branch**: `009-dashboard-lookups-ux`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Update the user dashboard: address lookahead while typing; overall neighborhood score preview on each saved report (same color scaling); prevent duplicate reports for the same address per user; overflow menu (⋯) to favorite or delete; two columns — Favorites and Recent (Recent by recency; re-search or open report bumps recency)."

## Clarifications

### Session 2026-07-21

- Q: Should Favorites and Recent be mutually exclusive or dual-listed? → A: Dual listing — favorites appear under Favorites and also remain in Recent ordered by recency.
- Q: How should existing duplicate saved addresses be handled? → A: One-time cleanup — merge existing duplicates per user into a single entry (keep newest activity; preserve favorite if any duplicate was favorited).
- Q: Should delete require confirmation? → A: Confirm before delete (dialog or inline confirm).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pick an address from suggestions (Priority: P1)

A signed-in user starts typing an address in the dashboard search bar. As they type, a list of well-formatted address suggestions appears. They can select a suggestion to fill the search with a correct address and then score it, reducing failed lookups caused by typos or incomplete formatting.

**Why this priority**: Search is the primary way to create reports; suggestion selection directly improves success rate and is useful before other list UX.

**Independent Test**: On the dashboard, type a partial U.S. street address, see suggestions, select one, and successfully open/create a report for that address.

**Acceptance Scenarios**:

1. **Given** the user is on the dashboard with the search focused, **When** they type enough characters to identify a place, **Then** a list of candidate addresses appears under the search field.
2. **Given** suggestions are visible, **When** the user selects one, **Then** the search field shows that formatted address and they can submit to score it.
3. **Given** the user continues typing without selecting, **When** suggestions update, **Then** the list reflects the latest input (or clears if input is too short / no matches).
4. **Given** no matching suggestions, **When** the user finishes typing, **Then** they can still submit a free-typed address (existing score flow), with clear feedback if it cannot be found.

---

### User Story 2 - One report per address, with score preview (Priority: P1)

A signed-in user keeps a single saved identity per address (no duplicate saved entries). Each entry shows a preview of the overall neighborhood score using the same color meaning as on the full report, so they can scan quality without opening every report. If favorited, that one entry may appear in both Favorites and Recent.

**Why this priority**: Duplicate rows and missing score context are the core list-quality problems called out by the user.

**Independent Test**: Score the same address twice as the same user; the dashboard still shows a single row for that address with an overall score preview (or a clear “unavailable” state if no score exists yet).

**Acceptance Scenarios**:

1. **Given** the user already has a saved lookup for an address, **When** they search/score that same address again, **Then** the dashboard does not add a second saved identity for that address.
2. **Given** a user already has multiple saved rows for the same address from before this change, **When** they open the dashboard after the cleanup, **Then** those rows are merged into one entry (newest activity wins; favorite preserved if any was favorited).
3. **Given** a saved lookup has an available overall score, **When** the user views the dashboard, **Then** that row shows the overall score with the same color scaling used on the report.
4. **Given** a saved lookup has no score available yet, **When** the user views the dashboard, **Then** the row still appears with a clear non-numeric / unavailable score preview (not a fake score).
5. **Given** the user re-scores an address they already saved, **When** the list refreshes, **Then** that address moves to the top of Recent rather than duplicating.

---

### User Story 3 - Favorites, Recent, and row actions (Priority: P2)

The dashboard presents two columns: **Favorites** and **Recent**. Recent is ordered by how recently the user searched that address or opened its report. Each row has a three-dot control that opens a small menu to favorite/unfavorite or delete the address from the user’s list.

**Why this priority**: Organization and management complete the dashboard, but depend on a clean, de-duplicated list with scores.

**Independent Test**: Favorite an address and confirm it appears under Favorites while still listed in Recent; open or re-search another address and confirm it rises in Recent; delete an address and confirm it disappears from both columns.

**Acceptance Scenarios**:

1. **Given** the user has favorited and non-favorited saved addresses, **When** they open the dashboard, **Then** Favorites lists only favorited addresses, and Recent lists all saved addresses (including favorites) ordered by recency.
2. **Given** addresses in Recent, **When** sorted, **Then** more recently searched or opened addresses appear above older ones.
3. **Given** a favorited address, **When** the user searches it again or opens its report, **Then** its recency is updated in both Favorites and Recent ordering.
4. **Given** a row’s three-dot menu is open, **When** the user chooses Favorite, **Then** the address appears in Favorites and remains in Recent without creating a duplicate identity; **When** they choose Unfavorite, **Then** it leaves Favorites but stays in Recent.
5. **Given** a row’s three-dot menu is open, **When** the user chooses Delete, **Then** they are asked to confirm; **When** they confirm, **Then** the address is removed from their dashboard list and no longer appears in either column; **When** they cancel, **Then** the entry remains unchanged.
6. **Given** the three-dot control, **When** the user clicks outside the menu or presses Escape, **Then** the menu closes without changing the row.

---

### Edge Cases

- User types fewer than the minimum characters for suggestions → no suggestion list (or empty state), free-typed submit still allowed.
- Suggestion provider is slow or unavailable → search still works without suggestions; user sees a non-blocking empty/error state for the dropdown.
- User deletes their last address → empty Favorites and/or Recent states with helpful copy.
- Score becomes available after previously showing unavailable → next dashboard load shows the real overall score preview.
- Unauthenticated users do not get this dashboard (existing auth gate); address suggestions on public landing search are out of scope unless the shared search control already appears there and inherits suggestion UX without breaking guests.
- Rapid favorite/unfavorite or delete actions → UI stays consistent with server state (no ghost rows).
- User already has multiple saved rows for the same address before this feature → after cleanup they see a single saved identity (favorited if any of the duplicates was).
- User cancels delete confirmation → entry remains in Favorites/Recent unchanged.
## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Dashboard address search MUST show address suggestions as the user types (lookahead), and MUST allow selecting a suggestion to populate the search field before scoring.
- **FR-002**: Users MUST still be able to submit an address without picking a suggestion.
- **FR-003**: For a given signed-in user, the system MUST keep at most one saved dashboard entry per distinct address (re-search updates the existing entry rather than inserting a duplicate). Existing duplicate entries MUST be merged once into a single entry per address (retain the most recent activity timestamp; if any duplicate was favorited, the merged entry remains favorited).
- **FR-004**: Each dashboard entry MUST display an overall neighborhood score preview using the same color scaling semantics as the full report when a score is available.
- **FR-005**: When an overall score is not available, the entry MUST show a clear unavailable/empty preview (not an invented score).
- **FR-006**: Each dashboard entry MUST provide a three-dot overflow control that opens a compact menu with Favorite/Unfavorite and Delete actions.
- **FR-007**: Users MUST be able to mark or unmark an address as a favorite; Favorites lists only favorited entries, while Recent lists all saved entries (including favorites) ordered by last activity (dual listing — one underlying entry, visible in both columns when favorited).
- **FR-008**: Users MUST be able to remove an address from their own saved list via Delete after an explicit confirmation step (dialog or inline confirm); removal is per-user and does not delete shared neighborhood score data for other users.
- **FR-009**: Recent MUST be ordered by last activity (most recent first), where activity includes scoring/searching that address and opening that address’s report.
- **FR-010**: Favorites MUST be ordered by last activity (most recent first) within the Favorites column.
- **FR-011**: Opening a report from the dashboard MUST count as activity that updates recency for that entry.
- **FR-012**: Dashboard list data (columns, favorites, scores, menus) MUST only be available to the signed-in owner of those entries.

### Key Entities

- **Saved address entry**: A per-user record of an address they have scored or saved; includes display address, last activity time, favorite flag, and optional overall score preview.
- **Address suggestion**: A candidate formatted address offered while typing, selectable into the search field.
- **Overall score preview**: The single summary neighborhood score and its color band, aligned with the full report’s overall score presentation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In usability checks, at least 90% of testers can select a suggestion and reach a report without manually correcting street formatting.
- **SC-002**: After scoring the same address twice as the same user, the dashboard shows exactly one underlying saved entry for that address (a favorited entry may appear once in Favorites and once in Recent, but must not create a second saved identity).
- **SC-003**: For entries with an available score, dashboard score preview color band matches the full report’s overall score band for that address in 100% of sampled cases.
- **SC-004**: Users can favorite, unfavorite, and delete an entry in under 10 seconds from the dashboard without leaving the page.
- **SC-005**: After opening a report or re-searching an address, that entry appears at the top of Recent; if favorited, it also ranks at the top of Favorites by last activity.
- **SC-006**: Empty Favorites and empty Recent states are understandable without support help (testers correctly describe what to do next).

## Assumptions

- “Same address” means the same resolved place the product already uses after a successful lookup (normalized geocoded address / stable place identity), not merely identical free-text strings with different typos.
- Favorites and Recent use dual listing: a favorited address appears in both columns from a single saved entry (not two identities).
- Delete removes the entry from the user’s saved list only; historical scores for the neighborhood remain available if they search again later.
- Address lookahead uses the project’s allowed client-side places suggestion capability; scoring and persistence remain server-side.
- Color scaling for the overall score preview reuses the existing report overall-score visual scale (no new scoring formula).
- Minimum characters before suggestions appear follows common places-autocomplete practice (roughly 3+ characters) unless product copy already defines otherwise.
- Public landing-page search may share the same suggestion behavior if it uses the same search control; guest users still cannot access Favorites/Recent.
- Existing duplicate saved entries are merged once when this feature rolls out (newest activity kept; favorite preserved if any duplicate was favorited); thereafter duplicates are prevented.
- Delete requires an explicit confirmation step before the entry is removed from the user’s list.
