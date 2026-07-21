# skills

[![skills.sh](https://skills.sh/b/SystemFiles/skills)](https://skills.sh/SystemFiles/skills)

Agent skills I've built or augmented from other sources, packaged as a [skills.sh](https://www.skills.sh/) source you can install from with the [`skills` CLI](https://github.com/vercel-labs/skills).

Each skill is a directory under `skills/<name>/` containing a `SKILL.md` (plus any helper scripts/evals). The `skills` CLI installs them into whichever AI coding agents you have (Cursor, Codex, Claude Code, and [many more](https://github.com/vercel-labs/skills#supported-agents)).

## Available skills

### Authored here

| Skill | Description |
| --- | --- |
| `agentsmd-generator` | Generate project-level `AGENTS.md` onboarding guides covering structure, tooling, testing, task flow, and conventions. |
| `issue-triage` | Turn a rough GitHub Issue into an agent-executable sealed body with `ready` + size labels (explicit invocation). Clarifying Q&A persists under `.issue-triage/` (gitignored) for resume. Ships `issue_ops` + validators, offline `evals/`, and `mock_gh` for script unit tests. |
| `jj-case-insensitive-clone-fix` | Diagnose and fix the `jj git clone` "Failed to update refs" error on case-insensitive filesystems (e.g. macOS APFS). |
| `lavish-safe` | Local-only Lavish HTML review via `lavish-axi`, with share and telemetry forbidden. |
| `research_codebase` | Map how a codebase works today and save a dated, citation-backed report under `thoughts/`, using parallel sub-agents by default. |
| `sdd-linear` | Run the Spec-Driven Development (SDD) workflow with Linear issues, sub-issues, attachments, and comments as the system of record instead of `docs/specs`. |
| `sync-upstream` | Sync a fork's default branch with its upstream remote using merge or rebase, resolving conflicts as needed. |
| `taskfile-automation` | Scaffold consistent, portable repo automation with a `Taskfile` as the single entry point (run the same locally and in CI), adding Docker/Compose only when external runtime deps demand it. |
| `visual-explain` | Interactive local HTML explanation of a diff/branch/PR (Background, Intuition, Code walkthrough, Quiz). Adapted from sighup/claude-workflow `cw-explain`. |
| `work-breakdown` | Decompose large/ambiguous scope into smaller units of work with dependencies and parallelization. |

### Vendored from upstream

These skills are copied verbatim from their upstream repositories and kept fresh
automatically, so they install from this one source alongside the authored
skills. They are declared in [`upstream-skills.toml`](upstream-skills.toml),
copied in by `scripts/sync_upstream_skills.py`, and refreshed on a schedule by
the [Sync Upstream Skills](.github/workflows/sync-upstream-skills.yml) workflow.
Do not hand-edit `skills/<name>/` for these; change the catalog instead.
Provenance (source commit and license) is recorded in `upstream-skills.lock.json`.

| Skill | Upstream | License | Description |
| --- | --- | --- | --- |
| `agent-browser` | [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | Apache-2.0 | Browser automation CLI for AI agents (navigate, fill forms, screenshot, scrape, test web/Electron apps). |
| `grill-me` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Relentless interview to sharpen a plan or design (explicit invocation). |
| `grill-with-docs` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Same grilling loop, also producing ADRs and glossary docs as you go. |
| `grilling` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Stress-test a plan/decision/idea with a decision-tree interview. |
| `improve-codebase-architecture` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Scan for deepening opportunities, present an HTML report, then grill one. |
| `teach` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Teach a skill or concept inside the current workspace. |
| `test-driven-development` | [obra/superpowers](https://github.com/obra/superpowers) | MIT | TDD workflow before writing implementation code. |
| `wayfinder` | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT | Map large work as decision tickets on an issue tracker and resolve them one by one. |

Some upstream skills set `hidden: true`, so they will not appear in
`npx skills add SystemFiles/skills --list`. Install them by explicit name, for
example `npx skills add SystemFiles/skills --skill agent-browser`.

## Install

List the available skills without installing:

```bash
npx skills add SystemFiles/skills --list
```

Install a single skill (interactive agent selection):

```bash
npx skills add SystemFiles/skills --skill work-breakdown
```

Install to specific agents (e.g. Cursor and Codex):

```bash
npx skills add SystemFiles/skills --skill work-breakdown -a cursor -a codex
```

Install non-interactively (CI-friendly):

```bash
npx skills add SystemFiles/skills --skill work-breakdown --yes
```

Install globally (available across all projects) instead of into the current project:

```bash
npx skills add SystemFiles/skills --skill work-breakdown --global
```

Install every skill in this repo:

```bash
npx skills add SystemFiles/skills --skill '*'
```

## Updating and removing

```bash
# Update installed skills from this source
npx skills update

# Remove a skill
npx skills remove work-breakdown
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to add or update a skill, run validation (`task validate`), and the commit/PR conventions.
