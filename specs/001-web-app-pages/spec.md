# Feature Specification: Web App Pages

**Feature Branch**: `001-web-app-pages`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "I want to build out the different webpages for the web app. Currently we have 2 pages: (1) A splash page with information about the app, features, example, pricing etc. (2) Report page with a rendered map and example data shown. I want to build out the other pages listed in the docs. For instance a Login/signup page. User menu, etc. Make sure to keep the styling of current pages."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign up and sign in (Priority: P1)

A prospective or returning home buyer opens NeighborhoodIQ, creates an account with email and password, or signs in to an existing account, then lands somewhere useful (home or the page they were trying to reach).

**Why this priority**: Account access unlocks saved history, paid features later, and is the first missing page called out by the user and the product docs. Without it, dashboard and personalized flows cannot ship.

**Independent Test**: From a cold visit, complete register and login flows with valid and invalid credentials; confirm success and failure messaging without needing compare or dashboard.

**Acceptance Scenarios**:

1. **Given** a visitor on the sign-up page, **When** they submit a valid name, email, and password, **Then** they become signed in and can continue using the product as an authenticated user.
2. **Given** a visitor on the sign-in page, **When** they submit correct credentials, **Then** they become signed in and see authenticated navigation (user menu) instead of only “Get started.”
3. **Given** a visitor on sign-up, **When** they submit an invalid email or incomplete input, **Then** they see a specific, actionable message (e.g. valid email required) — not a generic “Something went wrong.”
4. **Given** a visitor on sign-in, **When** they submit wrong credentials, **Then** they see “Invalid email or password” (single non-enumerating message). **When** an unexpected failure occurs, **Then** they see “Something went wrong. Please try again.”
5. **Given** a signed-in user, **When** they choose sign out from the user menu, **Then** they become signed out and the header returns to the guest state.

---

### User Story 2 - Consistent site chrome and user menu (Priority: P1)

A visitor or signed-in user can move between marketing, auth, report, and account-related pages using a header/footer that matches the look of the existing splash and report experience. When signed in, a user menu exposes account actions (e.g., dashboard, sign out) without breaking the current visual language (fonts, colors, spacing, brand mark).

**Why this priority**: New pages must feel like the same product; the user explicitly required keeping current styling. Shared chrome also makes login/signup discoverable from the splash page.

**Independent Test**: Browse home, report, login, register, and pricing with guest and signed-in states; verify header/footer/user menu styling and links without needing dashboard data.

**Acceptance Scenarios**:

1. **Given** the existing splash page, **When** a guest views the header, **Then** they can reach sign-in / sign-up (or an equivalent clear path) without losing the current brand treatment.
2. **Given** a signed-in user on any primary page, **When** they open the user menu, **Then** they see their identity (name or email) and actions including dashboard, plans/upgrade, compare (placeholder), and sign out.
3. **Given** any newly added page in this feature, **When** a user views it, **Then** typography, color tokens, and layout density match the splash and report pages (no unrelated visual system).
4. **Given** a user on a non-home page, **When** they click Scores, AI Insights, or Pricing in the header, **Then** they navigate to the homepage section (`/#scores`, `/#ai`, or `/#pricing`), not a dead in-page hash or the upgrade page.
5. **Given** a signed-in user, **When** they view the footer, **Then** there is no Sign in link. **Given** a guest, **When** they view the footer, **Then** Sign in is available.

---

### User Story 3 - Upgrade page (signed-in plans) (Priority: P2)

A signed-in user opens an upgrade/plans page from the user menu to review Free / Buyer / Buyer Pro and see their current plan. Plan selection CTAs are UI placeholders (no billing yet). Guests cannot use this page; header “Pricing” goes to the splash pricing section instead.

**Why this priority**: Account holders need a clear upgrade surface; splash keeps marketing pricing for everyone.

**Independent Test**: As guest, header Pricing → `/#pricing` (marketing CTAs) and `/pricing` redirects to login. As signed-in user, UserMenu → Plans & upgrade → `/pricing` and splash `#pricing` both show current plan + non-functional CTAs; plan buttons do not change tier.

**Acceptance Scenarios**:

1. **Given** a guest, **When** they click Pricing in the header or scroll to splash `#pricing`, **Then** they see marketing tiers with register-oriented CTAs.
2. **Given** a guest, **When** they open `/pricing` directly, **Then** they are redirected to sign in.
3. **Given** a signed-in user, **When** they open Plans & upgrade from the user menu **or** view splash `#pricing`, **Then** they see tier cards, their current plan labeled, and non-functional plan CTAs (no payment / no tier change yet).
4. **Given** an upgrade prompt on a gated experience, **When** the user chooses to upgrade, **Then** they are taken to `/pricing` (after sign-in if needed).

---

### User Story 4 - Dashboard of saved lookups (Priority: P2)

A signed-in user opens their dashboard, can search a new address without leaving the page, and sees addresses they have previously looked up with a way to reopen a report. Empty and loading states are clear.

**Why this priority**: Docs define dashboard as “saved lookups”; it is the primary post-login destination after auth chrome exists.

**Independent Test**: As a signed-in user with zero lookups and with at least one lookup, open dashboard, use on-page search and/or open a report (confirm Back to dashboard); as a guest, confirm dashboard gate and no report dashboard link.

**Acceptance Scenarios**:

1. **Given** a signed-in user with no prior lookups, **When** they open the dashboard, **Then** they see an address search bar and an empty state that points them to that search.
2. **Given** a signed-in user, **When** they submit a valid address in the dashboard search, **Then** they are taken to the corresponding report (same lookup flow as splash).
3. **Given** a signed-in user with prior lookups, **When** they open the dashboard, **Then** they see a list of saved addresses and can open a report for one of them.
4. **Given** a guest, **When** they try to open the dashboard, **Then** they are directed to sign in rather than seeing another user’s data.
5. **Given** a signed-in user on a report page, **When** they choose Back to dashboard, **Then** they return to `/dashboard`. **Given** a guest on a report page, **When** they view the report, **Then** no Back to dashboard control is shown.

---

### User Story 5 - Compare placeholder (Priority: P3)

A user can open `/compare` (including from the user menu) and see a clear “Feature coming soon” page. Live side-by-side comparison is **out of scope** for this feature and deferred to a later release.

**Why this priority**: Compare is listed in product docs, but the live implementation is not ready; a placeholder avoids a broken experience while keeping navigation discoverable.

**Independent Test**: Open `/compare` as guest or signed-in user; confirm coming-soon copy; primary CTA goes to dashboard, secondary to home; confirm the page does not call a live compare API.

**Acceptance Scenarios**:

1. **Given** any visitor, **When** they open `/compare`, **Then** they see a “Feature coming soon” message consistent with site styling.
2. **Given** the coming-soon page, **When** they choose the primary CTA, **Then** they go to the dashboard; the secondary link returns home.
3. **Given** a signed-in user, **When** they choose Compare in the user menu, **Then** they land on the same coming-soon page (not an error or blank screen).

---

### Edge Cases

- Sign-in with unknown email or wrong password shows one **invalid credentials** message (no “email not found” vs “wrong password” enumeration). Unexpected/server failures use “Something went wrong…” (Constitution VIII).
- Registering with an invalid email format shows a specific validation message (not “Something went wrong”).
- Registering with an email that already exists shows a clear recovery path (sign in instead).
- Session expiry: protected pages (dashboard) send the user to sign in and return them afterward when practical.
- Very long address labels on dashboard wrap or truncate without breaking layout.
- Mobile viewport: auth forms, user menu, pricing, dashboard, and compare placeholder remain usable and visually consistent with the existing responsive splash/report.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a sign-up page where users can create an account with full name, email, and password.
- **FR-002**: System MUST provide a sign-in page where users can authenticate with email and password.
- **FR-003**: System MUST allow signed-in users to sign out from a user menu in the site header.
- **FR-004**: System MUST show different header actions for guests vs signed-in users (guest: path to sign in / get started; signed-in: user menu).
- **FR-005**: System MUST keep visual styling of all new pages and chrome consistent with the existing splash and report pages (brand mark, fonts, color tokens, spacing, button styles).
- **FR-006**: System MUST provide a signed-in upgrade/plans page at `/pricing` whose tier content stays consistent with the splash pricing section; plan CTAs MAY be non-functional placeholders until billing ships. Guests MUST be redirected to sign in. Header “Pricing” MUST link to `/#pricing` (splash), not `/pricing`. Splash `#pricing` MUST show guest marketing CTAs when signed out and the same upgrade UI (current plan + non-functional CTAs) when signed in.
- **FR-007**: System MUST provide a dashboard page for signed-in users with on-page address search plus a list of prior lookups with navigation to the corresponding report.
- **FR-008**: System MUST deny or redirect unauthenticated access to the dashboard and the upgrade page (`/pricing`).
- **FR-009**: System MUST provide a `/compare` page that communicates the feature is coming soon (no live two-address comparison in this feature). Primary CTA MUST prefer dashboard; secondary MUST link home.
- **FR-010**: System MUST provide an `UpgradePrompt` component suitable for future gated UI (CTA to `/pricing`); live compare entitlement gating is deferred with FR-009.
- **FR-011**: System MUST validate auth form input client-side enough to catch empty required fields and obvious format issues before submit. User-correctable failures MUST show specific messages; “Something went wrong” MUST be reserved for unexpected failures. Login MUST use one invalid-credentials message for auth rejection (Constitution VIII).
- **FR-012**: Account and entitlement decisions MUST be enforced by the product backend; the web UI MUST NOT be the sole enforcer of billing or access rules (upgrade prompts are informational; UI-only plan buttons do not grant entitlements).
- **FR-013**: Existing splash and report pages MUST remain available; this feature MUST NOT regress their primary layouts while integrating shared header/user menu behavior.
- **FR-014**: Navigation MUST expose paths appropriate to user state (splash pricing for guests; plans/upgrade and dashboard when signed in). Header section links that refer to splash content MUST use root-anchored paths (`/#scores`, `/#ai`, `/#pricing`) so they work from any page.
- **FR-015**: Footer MUST hide Sign in when the user is authenticated.
- **FR-016**: Report pages (`/report/[addressId]`) MUST show a Back to dashboard control only when the user is signed in.

### Key Entities

- **User account**: Identity used to sign in (name, email); signed-in vs guest state drives chrome and access.
- **Session**: Active signed-in state until sign-out or expiry.
- **Saved lookup**: A prior address analysis belonging to a user, shown on the dashboard and linkable to a report.
- **Neighborhood report**: Existing report experience for one address.
- **Subscription tier**: Free vs paid capabilities (pricing CTAs); live compare gating deferred.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can complete sign-up from the marketing site in under 2 minutes with clear success feedback.
- **SC-002**: A returning user can sign in from the sign-in page in under 30 seconds when credentials are correct.
- **SC-003**: 100% of newly added primary pages (sign-in, sign-up, pricing, dashboard, compare placeholder) visually match the existing splash/report design language in a side-by-side design review (fonts, colors, header brand treatment).
- **SC-004**: In usability checks, at least 9 of 10 participants can find sign-in and open the dashboard (when signed in) without assistance.
- **SC-005**: Guests attempting dashboard access are redirected or prompted to authenticate 100% of the time (no data leak).
- **SC-006**: Opening `/compare` shows coming-soon messaging within one navigation, with no blank or error page.
- **SC-007**: From `/pricing`, Scores and AI Insights header links reach the corresponding homepage sections 100% of the time in manual checks.

## Assumptions

- Scope is the **web app pages and shared chrome** listed in the frontend design docs: sign-in, sign-up, user menu (header), signed-in upgrade/plans page, dashboard (search + saved lookups), and a **compare coming-soon placeholder** — plus wiring upgrade prompts to `/pricing` for future gates.
- **Live side-by-side compare** (API + results UI + tier gate) is **deferred** beyond this feature.
- Splash (home) and report pages already exist and are the visual source of truth; this feature extends them rather than redesigning them.
- Authentication is **email and password** (no social/OAuth providers in this feature).
- **Payment checkout / Stripe** and functional plan upgrades are out of scope; upgrade CTAs are UI placeholders only.
- **No Postgres user database yet**: auth and saved lookups are backed by a **temporary text/JSONL file store** in the API for this feature only. That store MUST be removed and replaced with the real user/lookup tables when backend auth is implemented (see `research.md` removal checklist).
- Agent white-label, PDF export, and brokerage API portals are out of scope.
- “Keep the styling” means reuse the current design tokens, typography (display + body), header brand treatment, and component patterns already on splash/report — not introduce a second visual system.
