---
name: "speckit-close"
description: "Verify that the current feature is converged and project checks pass, then safely stop repository-owned development and test services and report whether the feature is cleanly closed."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "project-local"
  source: "custom/speckit-close"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

Recognized user-input options:

* `cleanup-only`: Skip convergence and verification gates. Only discover and safely stop
  repository-owned development/test services, clean clearly temporary artifacts, and report
  repository status. This outcome MUST NOT be reported as a completed feature close.
* `keep-services`: Run the close-readiness checks and report service inventory, but do not
  stop development/test services.

When neither option is supplied, perform the complete close workflow.

## Pre-Execution Checks

**Check for extension hooks (before close)**:

* Check if `.specify/extensions.yml` exists in the project root.

* If it exists, read it and look for entries under the `hooks.before_close` key.

* If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.

* Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled`
  field as enabled by default.

* For each remaining hook, do **not** attempt to interpret or evaluate hook `condition`
  expressions:

  * If the hook has no `condition` field, or it is null/empty, treat the hook as executable.
  * If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation
    to the HookExecutor implementation.

* When constructing slash commands from hook command names, replace dots (`.`) with hyphens
  (`-`). For example, `speckit.git.review` → `/speckit-git-review`.

* For each executable hook, output the following based on its `optional` flag:

  * **Optional hook** (`optional: true`):

    ```text
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```

  * **Mandatory hook** (`optional: false`):

    ```text
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Goal.
    ```

    After emitting the block above you MUST actually invoke the hook and wait for it to finish
    before continuing. Run it the same way you would run the command yourself in this
    agent/session (the invocation may differ from the literal `{command}` id shown above,
    e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the
    block alone does not run the hook.

* If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.

## Goal

Close the current Spec Kit feature only when its implementation has converged with the
feature artifacts and the relevant project verification checks pass. Then safely stop the
frontend, backend, mock services, test watchers, local containers, emulators, preview servers,
and other development processes that are demonstrably owned by the current repository.
Clean only clearly temporary, reproducible development artifacts and present a closeout report
that tells the user whether the feature is fully closed, closed with warnings, or not ready.

The completed feature's `spec.md`, `plan.md`, `tasks.md`, checklists, and supporting documents
remain in place as project history and documentation. This command does **not** archive or
delete the feature directory and does **not** create the next feature or spec.

## Operating Constraints

**VERIFY AND CLEAN UP — NEVER IMPLEMENT**: This command MUST NOT modify application code,
tests, specifications, plans, or task definitions to make the feature appear complete. If
convergence or verification finds remaining work, report the feature as `not_ready` and hand
the work back to `/speckit-implement` or the appropriate project workflow.

The command MAY write only by:

* invoking an existing, repository-documented shutdown or cleanup command;
* terminating a process or process tree whose ownership by this repository has been verified;
* stopping containers belonging to this repository's Compose project or equivalent local stack;
* deleting clearly temporary and reproducible artifacts that are safe to remove under Step 8.

It MUST NOT:

* create a new spec or feature directory;
* modify `spec.md`, `plan.md`, `tasks.md`, checklists, or constitution files;
* modify, create, or delete application source code or tests;
* mark incomplete tasks complete;
* commit, push, merge, rebase, reset, restore, stash, or delete branches;
* open, approve, or merge a pull request;
* archive or delete the completed spec;
* delete persistent databases, migrations, fixtures, uploads, secrets, or user data;
* stop Cursor, the user's terminal application, operating-system services, or unrelated
  development processes;
* use broad termination commands such as `killall node`, `pkill -f python`, `taskkill /IM
  node.exe`, or equivalent commands that may affect unrelated projects;
* use destructive cleanup commands such as `git clean -fd`, `git reset --hard`, or
  `docker system prune`.

**Ownership Before Termination**: A process, container, or service MUST NOT be stopped unless
at least one strong ownership signal connects it to the current repository. Strong signals
include:

* its current working directory is inside the repository;
* its command line contains an absolute path inside the repository;
* it is recorded by a repository-owned PID file and the live command matches the expected
  service;
* it belongs to the repository's named Docker Compose project, configuration file, or labels;
* it is a child of a verified repository-owned launcher process;
* a repository-provided status or stop command identifies it as part of this project.

A matching port number alone is **not** sufficient proof of ownership. When ownership is
ambiguous, leave the process running and report it as a warning.

**Graceful Before Forceful**: Always use a documented stop command, interrupt, terminate
signal, or normal container shutdown first. Force termination is allowed only for the exact,
verified process or process tree after graceful shutdown fails and after a brief recheck.

**No Closure Marker**: Unless the repository already defines an explicit closure/status
mechanism, do not invent one. The durable record of completion is the retained feature
artifacts plus the eventual Git commit or pull request.

## Execution Steps

### 1. Initialize Close Context

Run the Spec Kit prerequisite checker once from the repository root and parse its JSON output
for `FEATURE_DIR` and `AVAILABLE_DOCS`.

Use the script available for the current environment:

* PowerShell:

  ```powershell
  .specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
  ```

* Bash, only when the repository provides the Bash equivalent:

  ```bash
  .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ```

Run only one platform-appropriate script. Derive absolute paths:

* SPEC = `FEATURE_DIR/spec.md`
* PLAN = `FEATURE_DIR/plan.md`
* TASKS = `FEATURE_DIR/tasks.md`
* CONSTITUTION = `.specify/memory/constitution.md` (if present)
* REPO_ROOT = repository root

Also capture:

* current Git branch, without changing it;
* current Git working-tree status, without modifying it;
* repository name and absolute path;
* current process/session identifier when available, for shutdown ownership checks.

If `spec.md`, `plan.md`, or `tasks.md` is missing, STOP the full close workflow with a clear,
actionable message naming the prerequisite command to run:

* `/speckit-specify` for a missing spec;
* `/speckit-plan` for a missing plan;
* `/speckit-tasks` for missing tasks.

Do not produce a successful close result with missing artifacts.

For single quotes in args like "I'm Groot", use escape syntax such as `'I'\''m Groot'` or use
double quotes when possible.

If `cleanup-only` was supplied, record that the workflow outcome cannot be `closed` and proceed
directly to Step 6 after initializing repository context.

### 2. Check Task Completion

Read `tasks.md` and inventory all task checklist items without modifying them.

Classify tasks as:

* complete: `- [x]` or `- [X]`;
* incomplete: `- [ ]`;
* malformed/ambiguous: task-like entries whose completion state cannot be determined.

If any incomplete or malformed task remains:

* set readiness to `not_ready`;
* list the task IDs and short descriptions;
* do not mark or rewrite them;
* do not skip service cleanup solely because tasks remain;
* continue through safe verification discovery and service cleanup so the development
  environment is left clean, but do not report the feature as closed.

### 3. Run the Convergence Gate

When the installed Spec Kit environment exposes the `speckit-converge` skill/command, invoke
it and wait for its result. Use the invocation form supported by the current agent/session,
such as `/speckit-converge`, `/skill:speckit-converge`, or `$speckit-converge`.

Interpret its outcome as follows:

* `converged`: convergence gate passes;
* `tasks_appended`: convergence gate fails, readiness becomes `not_ready`, and the newly
  appended tasks remain for `/speckit-implement`;
* invocation unavailable or failed: do not claim convergence. Set readiness to `not_ready`
  and report that `/speckit-converge` must be run successfully before the feature can be
  considered closed.

Do not duplicate or approximate convergence by editing artifacts yourself. Do not run
`/speckit-implement` from this command.

If Step 2 found incomplete tasks, convergence may still be run for diagnostics, but the
feature remains `not_ready` regardless of the convergence result.

### 4. Discover Verification Commands

Build a verification inventory from repository-owned sources, using progressive disclosure.
Inspect only what is necessary from:

* `package.json` and workspace package manifests;
* `pyproject.toml`, `tox.ini`, `pytest.ini`, `requirements` files, or equivalent;
* `Makefile`, `justfile`, `Taskfile`, or project scripts;
* build-system files;
* Docker Compose files used for tests;
* `README.md` and `CONTRIBUTING.md`;
* CI workflow files;
* `plan.md` and `tasks.md` references to required checks;
* existing scripts named `check`, `verify`, `test`, `lint`, `typecheck`, `build`, `ci`,
  `e2e`, `integration`, `format:check`, or close equivalents.

Prefer explicit repository commands over guessed tool invocations. Do not install new
dependencies, upgrade packages, or alter lockfiles.

Construct an internal ordered check plan. Include relevant one-shot checks such as:

1. formatting validation;
2. linting;
3. type checking;
4. unit tests;
5. integration tests;
6. end-to-end tests;
7. production build;
8. project-specific validation scripts.

Exclude interactive shells and indefinite watch-mode commands. When a test command requires
services, use the repository's documented one-shot orchestration when available and record any
services started so they can be stopped in Step 7.

### 5. Execute Verification

Run each discovered verification command from the documented working directory and record:

* exact command;
* working directory;
* exit status;
* concise result summary;
* whether the command started persistent child services;
* whether a failure appears related to the current feature, preexisting, environmental, or
  indeterminate.

Do not edit code or configuration to fix failures.

A failed required check sets readiness to `not_ready`. Continue with remaining independent
checks when doing so is safe and useful. Skip checks that depend on a failed prerequisite and
state why they were skipped.

A missing optional check is not a failure. A missing check explicitly required by the plan,
constitution, CI, or task artifacts is a blocker and sets readiness to `not_ready`.

### 6. Inventory Development and Test Services

Discover services associated with the current repository. Potential service classes include:

* frontend development servers;
* backend/API development servers;
* mock backends or mock API servers;
* test watchers;
* end-to-end test web servers;
* Storybook or component-preview servers;
* preview servers;
* local database containers;
* Docker Compose services;
* background workers and job processors;
* local emulators;
* file watchers and bundlers;
* processes started during Step 5.

Use repository-owned evidence such as:

* `package.json` scripts and workspace scripts;
* `Makefile`, `Taskfile`, `justfile`, or project scripts;
* Compose files and Compose project labels;
* PID files under the repository;
* documented development ports;
* command lines, current working directories, parent/child process relationships, and open
  ports;
* logs generated by known repository scripts.

For each discovered candidate, record:

* service name;
* service type;
* PID, process group, container, Compose service, or equivalent identifier;
* command line or container image;
* working directory when available;
* listening ports when available;
* ownership evidence;
* confidence: `verified`, `ambiguous`, or `not_owned`;
* preferred graceful shutdown method.

Do not expose secret values from environment variables, command lines, or configuration files
in the report. Redact credentials, tokens, and connection strings.

### 7. Stop Repository-Owned Services

Unless `keep-services` was supplied, stop every service classified as `verified` in Step 6.
Use the safest available method in this order:

1. repository-provided `stop`, `down`, `dev:stop`, `cleanup`, or equivalent command;
2. Docker Compose shutdown using the exact repository Compose files/project context;
3. graceful interrupt or terminate signal to the verified process group/process tree;
4. graceful shutdown of the exact container or emulator instance;
5. force termination of only the exact verified process/process tree when graceful shutdown
   failed.

For Docker Compose, prefer the repository's documented command. When none is documented and
ownership is verified, use the exact Compose configuration/project context rather than a global
Docker command. Do not remove named volumes unless the user explicitly requested data deletion.

For port-associated processes:

1. inspect the process listening on the port;
2. verify ownership using more than the port number;
3. stop the verified owner gracefully;
4. recheck the process and port;
5. force only the exact verified owner if graceful shutdown failed;
6. confirm whether the port was released.

For process trees, avoid terminating an unrelated terminal or editor parent. Stop the smallest
verified repository-owned process group that cleanly shuts down the service and its children.

Leave `ambiguous` and `not_owned` candidates running. Report ambiguous candidates with enough
non-sensitive evidence for the user to identify them manually.

If `keep-services` was supplied, do not stop anything; report all verified services as
intentionally retained.

### 8. Clean Clearly Temporary Artifacts

Discover temporary artifacts created by development, testing, or the commands run in Step 5.
Candidates may include:

* stale repository-owned PID files whose processes no longer exist;
* temporary logs produced by known development scripts;
* ignored test output and reports;
* ignored coverage output;
* screenshots, videos, traces, or snapshots from failed browser tests when they are generated
  artifacts rather than maintained fixtures;
* temporary mock data generated by a documented script;
* transient cache files explicitly covered by a repository cleanup command;
* temporary database files only when documentation proves they are disposable and generated
  solely for tests.

Remove an artifact only when all of the following are true:

* it is inside the repository or a repository-specific temporary directory;
* it is clearly generated and reproducible;
* it is not tracked by Git;
* it is not required as a fixture, baseline, migration, source asset, or debugging record the
  project intentionally retains;
* deleting it cannot remove persistent user or developer data;
* ownership and purpose are unambiguous.

Prefer repository-provided cleanup commands. Otherwise delete individual verified artifacts,
not broad directory patterns.

Do not remove:

* `.env` files or secrets;
* dependency directories solely to make the tree look clean;
* lockfiles;
* source files or tests;
* migrations or seed data;
* maintained fixtures, snapshots, or golden files;
* persistent local databases or Docker volumes;
* uploaded/user-generated files;
* Spec Kit artifacts;
* any file whose purpose is uncertain.

Report questionable artifacts instead of deleting them.

### 9. Review Final Repository State

Re-read, without modifying:

* Git branch;
* `git status` or equivalent working-tree status;
* modified tracked files;
* untracked files;
* ignored generated files relevant to cleanup;
* running verified/ambiguous services;
* repository-owned development ports;
* verification results;
* convergence and task status.

Inspect the final diff only for reporting purposes and flag:

* debugging statements introduced by the feature;
* temporary code;
* TODO/FIXME comments introduced by the feature;
* likely secrets;
* unrelated modifications;
* missing tests or documentation indicated by the existing artifacts.

Do not discard, rewrite, stage, or commit user changes.

### 10. Determine Close Outcome

Choose exactly one outcome:

* **`closed`**:

  * all tasks are complete;
  * convergence returned `converged`;
  * all required verification checks passed;
  * every verified repository-owned development/test service was stopped, unless
    `keep-services` was explicitly supplied;
  * required project-owned ports were released;
  * no blocking cleanup or repository-state issue remains.

* **`closed_with_warnings`**:

  * all tasks are complete;
  * convergence returned `converged`;
  * all required verification checks passed;
  * safe cleanup completed;
  * one or more non-blocking warnings remain, such as an ambiguous process, an intentionally
    retained service, a questionable generated artifact, or unrelated working-tree changes.

* **`not_ready`**:

  * incomplete/malformed tasks remain; or
  * convergence appended tasks, failed, or could not be run; or
  * any required verification check failed or was unavailable; or
  * a verified required service could not be stopped during the default full-close workflow;
  * any other blocker prevents confidently treating the feature as complete.

* **`cleanup_only`**:

  * the user supplied `cleanup-only`;
  * service cleanup and temporary-artifact cleanup were attempted;
  * no claim about feature completeness or convergence is made.

Do not report `closed` or `closed_with_warnings` merely because services were stopped.

### 11. Present the In-Session Closeout Report

Output a compact report using this structure:

## Spec Kit Closeout

**Outcome**: `closed` | `closed_with_warnings` | `not_ready` | `cleanup_only`

### Feature

| Field          | Value                          |
| -------------- | ------------------------------ |
| Feature        | `<feature name>`               |
| Branch         | `<current branch>`             |
| Spec directory | `<relative feature directory>` |

### Readiness

| Gate         | Result            | Details                                                     |
| ------------ | ----------------- | ----------------------------------------------------------- |
| Tasks        | PASS/FAIL/SKIPPED | `<completed and remaining counts>`                          |
| Convergence  | PASS/FAIL/SKIPPED | `<converged, tasks appended, unavailable, or cleanup-only>` |
| Verification | PASS/FAIL/SKIPPED | `<passed/failed/skipped command counts>`                    |

### Verification Commands

| Command     | Result            | Notes              |
| ----------- | ----------------- | ------------------ |
| `<command>` | PASS/FAIL/SKIPPED | `<concise result>` |

Omit the table only when no verification commands were discovered, and explain why.

### Development Service Cleanup

| Service     | Identifier / Port      | Ownership                    | Action                          | Final State             |
| ----------- | ---------------------- | ---------------------------- | ------------------------------- | ----------------------- |
| `<service>` | `<PID/container/port>` | verified/ambiguous/not_owned | `<shutdown method or retained>` | stopped/running/unknown |

### Temporary Artifacts

* Removed: `<count and concise list>`
* Retained for safety: `<count and concise list>`

### Repository Status

* Modified tracked files: `<count and concise list>`
* Relevant untracked files: `<count and concise list>`
* Remaining repository-owned services: `<count>`
* Remaining ambiguous services: `<count>`
* Blocking issues: `<count and concise list>`
* Warnings: `<count and concise list>`

Do not print secrets, raw environment variables, or unnecessarily long command output.

### 12. Provide Next Actions (Handoff)

* On `closed`: report:

  **"✅ Closed — the feature has converged, required checks passed, and repository-owned
  development/test services were stopped. The completed spec remains in place for review and
  version control."**

  Recommend reviewing the diff, committing/opening a pull request, and starting the next spec
  later from the appropriate new branch or feature workflow. Do not perform those actions.

* On `closed_with_warnings`: report:

  **"✅ Closed with warnings — the feature is complete and verified, and safe cleanup finished,
  but the warnings below require awareness."**

  List the warnings and recommend manual review before committing or starting the next spec.

* On `not_ready`: report:

  **"⛔ Not ready to close — cleanup was performed where safe, but one or more completion gates
  failed."**

  Give the smallest actionable next step. Prefer:

  * `/speckit-implement` when tasks remain or convergence appended tasks;
  * `/speckit-converge` when convergence was unavailable or failed;
  * the exact failed verification command when project checks failed.

* On `cleanup_only`: report:

  **"🧹 Cleanup complete — repository-owned development/test services and temporary artifacts
  were handled where ownership was verified. Feature completeness was not assessed."**

### 13. Check for Extension Hooks

After producing a `closed` or `closed_with_warnings` result, check if
`.specify/extensions.yml` exists in the project root.

* If it exists, read it and look for entries under the `hooks.after_close` key.

* If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.

* Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled`
  field as enabled by default.

* For each remaining hook, do **not** attempt to interpret or evaluate hook `condition`
  expressions:

  * If the hook has no `condition` field, or it is null/empty, treat the hook as executable.
  * If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation
    to the HookExecutor implementation.

* Report the close outcome before listing any hooks.

* When constructing slash commands from hook command names, replace dots (`.`) with hyphens
  (`-`). For example, `speckit.git.commit` → `/speckit-git-commit`.

* For each executable hook, output the following based on its `optional` flag:

  * **Optional hook** (`optional: true`):

    ```text
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```

  * **Mandatory hook** (`optional: false`):

    ```text
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```

    After emitting the block above you MUST actually invoke the hook and wait for it to finish
    before continuing. Run it the same way you would run the command yourself in this
    agent/session (the invocation may differ from the literal `{command}` id shown above,
    e.g. a skills-mode agent runs it as `/skill:speckit-...` or `$speckit-...`). Emitting the
    block alone does not run the hook.

* Do not run `after_close` hooks for `not_ready` or `cleanup_only` outcomes.

* If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.
