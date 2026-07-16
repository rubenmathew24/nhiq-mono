# NeighborhoodIQ Spec Kit — Git Workflow

Canonical commit rhythm for Spec Kit feature branches. Skills that touch git **must** follow this file.

## Target history (typical feature branch)

Most feature branches should end with **three commits**:

1. **Spec** — finalized `spec.md` (and related clarify/checklist artifacts)
2. **Plan + Tasks** — `plan.md`, `tasks.md`, and other planning artifacts (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`, …)
3. **Implementation** — application / worker / infra code that delivers the feature

```text
/speckit-specify  → create branch from `dev`, write draft spec, **publish branch** (push -u). Do **not** commit the draft yet.
/speckit-clarify  → edit spec only; **never commit**
/speckit-plan     → **Commit #1 (Spec)** first, then generate the plan (+ research/contracts as usual)
/speckit-tasks    → write `tasks.md`; **do not commit** (bundled into Commit #2)
/speckit-implement→ **Commit #2 (Plan + Tasks)** first, then implement; when all tasks done → **Commit #3 (Implementation)**
```

PRs still target **`dev`** (see `.cursor/rules/git-branching.mdc`). Do **not** push commits #1–#3 during plan/implement unless the user explicitly asks (except the initial **branch publish** at specify time). **`/speckit-close`** on a successful close (`closed` / `closed_with_warnings`) **must** push the branch and open a PR into `dev` — never merge it.

## Commit protocol (when a skill requires a commit)

These automatic Spec Kit commits are explicitly requested by this workflow (override the usual “only commit when asked” default **for these steps only**).

1. Run in parallel: `git status`, `git diff` / `git diff --staged`, `git log -5 --oneline`
2. Stage **only** the paths listed for that commit below (never `.env` or secrets)
3. Commit with HEREDOC message (see user git rules)
4. Run `git status` to verify
5. **Do not** `git push` for commits #1–#3 during plan/implement (close publishes later)
6. If there is nothing to commit for that step, skip and tell the user (idempotent re-runs)

Never update git config, never `--amend` unless amend rules are fully met, never force-push to `master`/`dev`.

---

### Commit #1 — Spec (start of `/speckit-plan`)

**When:** Immediately after plan prerequisites resolve `FEATURE_DIR` / `FEATURE_SPEC`, **before** writing or overwriting `plan.md` / research / contracts.

**Stage (under `FEATURE_DIR` + pointer):**

- `specs/<feature>/spec.md`
- `specs/<feature>/checklists/` (if present)
- `.specify/feature.json` (if changed)
- Other clarify-only touch-ups under `FEATURE_DIR` that are still **spec** material (not `plan.md` / `tasks.md`)

**Do not stage:** `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, or application code.

**Message pattern:**

```text
docs(spec): finalize <NNN-short-name> specification

Frozen [NEEDS CLARIFICATION] / clarify answers before planning.
```

---

### Commit #2 — Plan + Tasks (start of `/speckit-implement`)

**When:** After implement prerequisites resolve `FEATURE_DIR` and checklists gate is passed (or user proceeds), **before** changing application/worker code or marking implementation tasks done.

**Stage (under `FEATURE_DIR`):**

- `plan.md`, `tasks.md`
- `research.md`, `data-model.md`, `quickstart.md` (if present)
- `contracts/` (if present)
- Any other planning-only files under `FEATURE_DIR` that are not `spec.md` / checklists

**Do not stage:** application code under `apps/`, `workers/`, `infra/` (except SQL/docs the **plan** intentionally added as planning artifacts), or unrelated repo changes.

**Message pattern:**

```text
docs(plan): add <NNN-short-name> plan and tasks

Planning artifacts ready for implementation.
```

---

### Commit #3 — Implementation (end of `/speckit-implement`)

**When:** After all required tasks in `tasks.md` are completed and marked `[x]`, validation has been run, and mandatory post-hooks are finished — **before** the Completion Report.

**Stage:** Implementation changes for the feature (code, tests, SQL, Compose, docs updated during implement). Include `tasks.md` checkbox updates and any converge appendices completed during implement.

**Do not stage:** secrets (`.env`), unrelated WIP on other features.

**Message pattern:**

```text
feat(<scope>): implement <NNN-short-name>

Deliver the planned feature per tasks.md.
```

Choose `<scope>` from the main surface touched (`api`, `web`, `workers`, or a short product name).

---

### Branch publish (end of `/speckit-specify`)

After the feature branch exists (hook or `create-new-feature.ps1` / equivalent) and the draft spec directory has been created:

```bash
git push -u origin HEAD
```

- Requires network / appropriate Shell permissions.
- Publishing creates remote tracking; it does **not** replace Commit #1.
- Leave the draft spec **uncommitted** until `/speckit-plan` starts (Commit #1).
- If push fails (auth/network), report the error and the exact retry command; do not block writing the local draft spec.

## Clarifications

| Situation | Behavior |
|-----------|----------|
| User skips `/speckit-clarify` | Commit #1 at plan start still commits the current `spec.md` |
| User re-runs plan after Commit #1 | Do not re-commit identical spec; new plan work stays for Commit #2 |
| User re-runs tasks after plan | Leave uncommitted; Commit #2 at next implement |
| User re-runs implement mid-feature | If Commit #2 already exists and plan/tasks unchanged, skip #2; do not create Commit #3 until **all** tasks are done |
| Converge appends tasks mid-implement | Finish via implement; fold into Commit #3 (or a follow-up implement commit if #3 already landed — prefer one #3 when possible) |
| Successful `/speckit-close` | Commit any remaining feature work if needed → `git push -u origin HEAD` → `gh pr create` into **`dev`**; never merge |
| `not_ready` / `cleanup-only` close | No push, no PR |
