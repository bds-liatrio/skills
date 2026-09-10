---
name: agentsmd-generator
description: Generate project-level AGENTS.md guides that capture conventions, workflows, and required follow-up tasks. Use when a repository needs clear agent onboarding covering structure, tooling, testing, task flow, README expectations, and conventional commit summaries.
license: MIT
allowed-tools: Read Write Edit Bash(ls:*) Bash(git:*) Bash(just:*) Bash(make:*) Bash(tree:*) Bash(SKILL_DIR=*)
---

# Agent Context Generator

Inventory the repo from source (not docs), then write an `AGENTS.md` that future agents can follow. Treat README/CONTRIBUTING/`docs/` as hints only: verify every claim against code, configs, scripts, CI, and manifests. When they disagree, the code wins — flag the discrepancy. Prefer `just`/`make`/`task` entry points. Include wrap-up duties: update the README after significant changes, and summarize work in conventional commits.

`$SKILL_DIR` is the absolute path of the directory containing this `SKILL.md`. Set it in the *same* command you run — shell state does not survive between tool calls, and a bare `scripts/…` would resolve against the inventoried repo.

## Phase 1 · Understand the repository

1. **Run the bundled [`repo-inventory`](scripts/repo-inventory)** from the repo root:

   ```bash
   SKILL_DIR=<absolute path to this skill's directory>
   "$SKILL_DIR/scripts/repo-inventory"
   ```

   It emits `key=value` facts (`languages`, `package_managers`, `runners`, `make_targets`/`just_recipes`, `ci_files`, `env_files`) plus a gitignore-aware `[tree]` (with `tree --prune` and `git ls-files` fallbacks). Use `-C <dir>` to scope a subdirectory or `--depth <n>` to widen/trim the tree. Everything below is judgment the script cannot infer (ownership, intent, stale-doc reconciliation).
2. **Existing AGENTS.md** — find current files and their scope inheritance so you update instead of duplicating.
3. **Docs as hints** — skim README, CONTRIBUTING, and other onboarding docs. Cross-check every stated convention, command, tool, or workflow against the inventory and the code before including it.
4. **Layout** — start from `[tree]` and `languages`. Add ownership the script cannot infer (e.g. "`src/ui` maintained by Frontend"). Flag must-read files (ADR indexes, architecture overviews, runbooks). If `tree` was unavailable, the script already fell back; trim to the top 2–3 levels.
5. **Automation** — confirm which `runners` / `make_targets` / `just_recipes` are canonical for lint, test, build, and data sync. If `just` is not installed, read the `Justfile` for recipe names.
6. **Tooling & environment** — add required runtimes, secrets handling, and local services on top of `languages`, `package_managers`, and `env_files`.
7. **Testing & quality** — start from `ci_files`, then name test suites, coverage, lint, and format expectations.
8. **Ambiguities** — ask before drafting when ownership, workflows, or whether `plans/`/`docs/` are canonical is unclear.

## Phase 2 · Plan the structure

Use this order:

1. **Header** — Title + short purpose.
2. **Context Marker** — Emoji marker (🧠) so agents signal they loaded project context.
3. **Quick Facts** — Languages, package manager, key scripts, CI.
4. **Repository Tour** — Directory map with responsibilities and ownership.
5. **Tooling & Setup** — Runtimes, package managers, env vars, secrets.
6. **Common Tasks** — Lint/test/build/deploy. Prefer `just` recipes, then `make` targets, then raw commands.
7. **Testing & Quality** — When and how to run tests, lint, format, coverage, CI.
8. **Workflow Expectations** — Branching, review, feature flags, deploy cadence.
9. **Documentation Duties** — When to update README, diagrams, or other docs.
10. **Finish the Task** — Mandatory wrap-up checklist.

For nested directories (e.g. `services/api/`), add a Scope note at the top describing inheritance. Confirm with the developer before creating per-directory AGENTS files.

## Phase 3 · Compose AGENTS.md

```markdown
# Project Agent Guide

> Scope: Root project (applies to all subdirectories unless overridden)

## Context Marker

The marker for this instruction is: 🧠

## Quick Facts
- **Primary language:**
- **Package manager:**
- **Entrypoints:**
- **CI/CD:**

## Repository Tour
- `path/` — description & owner

## Tooling & Setup
- Install instructions (per OS)
- Required environment variables (with purpose)
- Secrets management notes

## Common Tasks
- `just <task>` — what it does (preferred)
- `make <target>` — what it does
- Raw command fallback when automation missing

## Testing & Quality Gates
- Unit/integration test commands
- Lint/format commands
- Coverage expectations & thresholds
- CI status command or dashboard link

## Workflow Expectations
- Branch naming and review rules
- Feature toggles or release cadence
- Any approval or ticket linkage requirements

## Documentation Duties
- Update `README.md` when features, setup steps, or developer ergonomics change materially
- List other docs to refresh (architecture, ADRs, etc.)

## Finish the Task Checklist
- [ ] Update relevant docs (`README.md` if the change is significant)
- [ ] Summarize changes in conventional commit format (e.g. `feat: ...`, `fix: ...`)
```

Subdirectory template (only with developer approval):

```markdown
# <Directory Name> Agent Guide

> Scope: ./path/to/directory (inherits root AGENTS.md unless noted)

## Purpose
- What lives here
- Who owns it (team/contact)

## Key Files
- `file_or_folder/` — why it matters

## Common Tasks
- `just <task>` / `make <target>` / command snippets scoped to this directory

## Testing & Quality
- Specific tests, linters, or data fixtures for this directory

## Hand-off Notes
- Docs or runbooks to reference
- Open questions captured during discovery
```

Writing notes:

- Agents following emoji-marker conventions prepend 🧠 to responses after loading this file.
- Keep language direct. Commands should be copyable.
- Prefer relative paths for scripts (e.g. `scripts/bootstrap.sh`).
- Include a trimmed `tree --gitignore` snapshot (or a link to it) in the Repository Tour.
- Call out unanswered questions as action items.
- Mixed-language repos: subsections per component, global guidance first.

## Phase 4 · Validate

- Scope rules stated (inheritance / overrides).
- Canonical automation commands present.
- README update and conventional-commit reminders in the wrap-up checklist.
- Per-directory files only exist if the developer approved them.

When handing off, summarize what was added or updated, confirm the wrap-up reminders, and list leftover gaps (missing tests, stale scripts).
