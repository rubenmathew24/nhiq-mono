# Feature Specification: CI/CD Prod Deploy Completeness

**Feature Branch**: `007-cicd-prod-deploy`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Make the deploy workflow update everything needed for prod to stay current (with change detection; exclude workers). Design and implement tests that protect prod and run whenever a pull request is made to master."

## Clarifications

### Session 2026-07-21

- Q: What must fully update on every `master` push? → A: Everything **except workers**, driven by change detection. Workers remain manual / as-needed. If changes imply Redis (or other non-worker resources) need an app-facing update, do it; otherwise skip.
- Q: What must pass on a PR into `master`? → A: Fast checks (lint/typecheck/unit for changed packages) **plus** integration tests using ephemeral Postgres/Redis, including applying schema migrations in CI. No live Azure in the PR gate.
- Q: If a production schema migration fails mid-deploy? → A: Fail the Deploy workflow and **stop** — do not deploy new API/web images until migrations succeed; leave prod on previous images.
- Q: When should Postgres schema steps run on Deploy? → A: When **API and/or SQL migration paths** changed since the last successful deploy baseline; skip when neither changed.
- Q: Same PR suite on `dev`? → A: `master` **only** for this feature’s required gate.
- Q: Non-app Azure resources in scope? → A: **App-needed config/secrets only** (e.g. Container App settings the running apps require). No Redis/Postgres SKU, firewall, or networking changes.
- Q: If only web changed? → A: Rebuild/redeploy **only web**; skip API image, schema, and unrelated config.
- Q: Post-deploy health check? → A: **Deeper smoke** — public health/readiness for touched services plus one critical path against prod.
- Q: Which critical path? → A: **Anonymous lookup smoke** — known public test address; confirm report/result loads (no sign-in).



## User Scenarios & Testing *(mandatory)*



### User Story 1 - Promote to production without leftover manual steps (Priority: P1)

A release operator merges an approved promote PR into `master`. Production automatically receives every **app-facing** update required by that commit set: web and/or API as needed, database schema when API or schema definitions changed, and any newly required app configuration/secrets wiring when those requirements changed. Ingest **workers are not** part of this automatic path. The operator does not need a separate manual database apply for ordinary schema changes (the class of failure that left prod dashboards empty after a prior release).

**Why this priority**: Manual schema/config drift is the highest-cost production failure mode described for this work.

**Independent Test**: Merge (or simulate) a `master` change that adds a required database column used by the API; confirm Deploy applies schema before new API images go live, and prod serves the feature without a laptop `psql` step.

**Acceptance Scenarios**:

1. **Given** `master` changes include new schema definitions the API needs, **When** Deploy runs, **Then** schema is applied successfully **before** new API images are rolled out.
2. **Given** schema application fails, **When** Deploy continues, **Then** the workflow fails and **no** new API/web images are deployed; production keeps the previous app images.
3. **Given** `master` changes only the web app, **When** Deploy runs, **Then** only the web app is rebuilt/redeployed; API image rebuild, schema, and unrelated config steps are skipped.
4. **Given** `master` changes neither API nor schema definitions, **When** Deploy runs, **Then** schema steps are skipped.
5. **Given** `master` changes only worker/ingest code, **When** Deploy runs, **Then** workers are **not** rebuilt or redeployed by this workflow.

---



### User Story 2 - Change-aware updates for app-needed configuration (Priority: P2)

When a release changes documented requirements for how production apps are configured (new required environment values or secret bindings the apps need), Deploy updates those app settings. When those requirements did not change, Deploy does not touch them. Resizing databases/caches, firewall rules, and network topology remain out of scope.

**Why this priority**: Prevents “images updated but missing env” breaks without turning Deploy into full infrastructure management.

**Independent Test**: Introduce a new required app setting in the release; confirm Deploy applies it when detected and skips config when only unrelated files changed.

**Acceptance Scenarios**:

1. **Given** the release adds or changes an app-required setting, **When** Deploy detects that change, **Then** production app configuration is updated accordingly.
2. **Given** the release does not change app-required settings, **When** Deploy runs, **Then** those settings are left unchanged.
3. **Given** the release would only affect cache/database size, firewall, or networking, **When** Deploy runs, **Then** it does **not** perform those infrastructure changes.

---



### User Story 3 - Protect production via checks on PRs to `master` (Priority: P1)

Before a promote PR can be trusted for `master`, automated checks run: static quality (lint/typecheck) and unit tests for affected packages, plus integration tests against temporary Postgres and Redis that apply schema migrations and exercise API/database contracts. These checks do **not** call live Azure production. Feature PRs into `dev` are outside this feature’s required gate.

**Why this priority**: Equal to deploy completeness — catching schema/app mismatches before merge prevents the empty-dashboard class of incident.

**Independent Test**: Open a PR targeting `master` that breaks a schema/API assumption; the check suite fails. Open a PR with a correct schema+API change; integration tests pass including migrations on ephemeral databases.

**Acceptance Scenarios**:

1. **Given** a pull request targets `master`, **When** checks run, **Then** lint/typecheck and unit tests for changed packages execute.
2. **Given** that PR, **When** integration tests run, **Then** they use ephemeral Postgres and Redis (not production Azure) and apply schema migrations as part of the suite.
3. **Given** a PR that would ship API behavior requiring a missing schema change, **When** integration tests run, **Then** the suite fails before merge.
4. **Given** a pull request targets `dev` only, **When** this feature’s gate is considered, **Then** it is **not** required to run this `master`-only suite (existing `dev` practices unchanged by this requirement).

---



### User Story 4 - Post-deploy smoke proves the site still works (Priority: P2)

After Deploy successfully updates the services it touched, an automated smoke confirms production health endpoints for those services and completes an **anonymous** address lookup with a known test address, verifying a report/result loads. Sign-in and dashboard checks are not required for this smoke.

**Why this priority**: Confirms the live revision after Azure rollout, beyond “workflow steps succeeded.”

**Independent Test**: After a successful Deploy, smoke passes against prod health + anonymous lookup; deliberately break the lookup path and confirm smoke fails the workflow.

**Acceptance Scenarios**:

1. **Given** Deploy finished applying the selected updates, **When** smoke runs, **Then** public health/readiness checks succeed for services that were deployed.
2. **Given** smoke runs, **When** it submits the known anonymous test address, **Then** a report/result experience loads successfully.
3. **Given** health or anonymous lookup smoke fails, **When** the workflow finishes, **Then** Deploy is marked failed so operators know production may be unhealthy.

---



### Edge Cases

- What if only documentation or unrelated paths change on `master`? Deploy should no-op meaningful prod updates (or exit successfully with skips) rather than forcing full rebuilds.
- What if schema is already applied (idempotent / already-current)? Schema step succeeds without destructive resets; existing user data remains intact.
- What if API changed but schema files did not, yet the API expects new columns? PR integration tests should fail; Deploy still runs schema when API paths changed so pending migration runners can apply anything pending—planning must define how “pending” is detected without wiping data.
- What if web and API both changed? Both rebuild/redeploy; schema runs if API and/or SQL changed; smoke covers health for deployed services plus anonymous lookup.
- What if post-deploy smoke fails after images already rolled out? Workflow fails; recovery is operational (revert/redeploy)—this feature does not require automatic image rollback beyond the pre-image migration stop rule.
- Workers, national ingest jobs, and one-off data backfills remain manual and must not be triggered by ordinary Deploy.



## Requirements *(mandatory)*



### Functional Requirements

- **FR-001**: On push to `master` (and manual Deploy dispatch), the system MUST determine which production updates are required from the change set relative to a clear previous-deploy baseline.
- **FR-002**: The system MUST rebuild and redeploy the web application only when web-relevant paths changed; otherwise it MUST skip web rebuild/redeploy.
- **FR-003**: The system MUST rebuild and redeploy the API application only when API-relevant paths changed; otherwise it MUST skip API rebuild/redeploy.
- **FR-004**: The system MUST run production schema migration steps when API-relevant and/or schema-definition paths changed; otherwise it MUST skip schema steps.
- **FR-005**: Schema migration failure MUST fail Deploy and MUST prevent rollout of new API and web images for that run.
- **FR-006**: Successful schema application MUST occur before new API images are rolled out when both schema and API updates are in scope for the run.
- **FR-007**: Schema steps MUST be non-destructive to existing production data (no truncate/wipe as part of routine Deploy).
- **FR-008**: The system MUST update app-required production configuration/secret bindings when those requirements changed in the release; otherwise it MUST skip those updates.
- **FR-009**: The system MUST NOT change Redis/Postgres SKU/tier, firewall rules, or networking as part of Deploy.
- **FR-010**: The system MUST NOT rebuild or redeploy ingest workers as part of Deploy.
- **FR-011**: Pull requests targeting `master` MUST run lint/typecheck and unit tests for changed packages.
- **FR-012**: Pull requests targeting `master` MUST run integration tests against ephemeral Postgres and Redis that apply schema migrations and validate API/database behavior relevant to preventing schema-drift outages.
- **FR-013**: The `master` PR check suite MUST NOT depend on live Azure production resources.
- **FR-014**: This feature’s required PR gate applies to `master` only (not required for `dev` PRs).
- **FR-015**: After a successful Deploy application phase, the system MUST run production health/readiness checks for services it deployed and an anonymous lookup smoke with a known test address; smoke failure MUST fail the Deploy workflow.
- **FR-016**: Deploy and PR-check behavior MUST be documented for operators (when steps skip, fail, and what remains manual for workers).



### Key Entities

- **Deploy change set**: The set of path/category signals (web, API, schema, app-config) derived from commits since the last successful production deploy baseline.
- **Schema migration set**: Ordered, repeatable schema definitions that bring production Postgres to the version expected by the API without wiping data.
- **PR verification suite**: The automated checks required on pull requests into `master`.
- **Post-deploy smoke**: Health checks plus anonymous lookup against production after updates apply.



## Success Criteria *(mandatory)*



### Measurable Outcomes

- **SC-001**: For a release that only adds schema required by the API, production becomes correct via Deploy alone—no manual laptop database apply—on 100% of such test releases in verification.
- **SC-002**: When schema application fails in a controlled test, new API/web images are not rolled out (0 successful image rollouts after a failed schema step).
- **SC-003**: A web-only `master` change results in web update without API rebuild and without schema execution (verified by Deploy logs/skips).
- **SC-004**: A PR to `master` that omits a required schema change for new API behavior fails the integration suite before merge in verification scenarios.
- **SC-005**: Ephemeral integration tests (including migrations) complete as part of the `master` PR suite without contacting production Azure.
- **SC-006**: After a successful Deploy in verification, anonymous lookup smoke for the known test address succeeds within 3 minutes of the smoke step starting.
- **SC-007**: Worker-only changes on `master` do not trigger worker image or job updates via Deploy (0 worker deploys attributed to Deploy for those changes).



## Assumptions

- Production continues to be released by promoting to `master`; feature work still integrates through `dev` first.
- A known public test address suitable for anonymous lookup smoke already exists or will be agreed during planning (stable, non-destructive).
- App-required configuration changes are detectable from repository signals agreed in planning (for example documented setting manifests)—not ad-hoc Portal-only edits.
- Redis remains cache-only; “updating Redis” in this feature means app-facing connection/config wiring when required, not cache flushing as a routine deploy step unless planning explicitly requires it for correctness.
- Existing production data and users remain; Deploy must never truncate business tables as a migration strategy.
- National ingest / worker execution stays a separate operational workflow.
- GitHub branch-protection “required checks” UI may be enabled by the operator; the feature delivers the workflows/checks themselves.

