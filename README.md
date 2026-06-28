# skills

[![skills.sh](https://skills.sh/b/SystemFiles/skills)](https://skills.sh/SystemFiles/skills)

Agent skills I've built or augmented from other sources, packaged as a [skills.sh](https://www.skills.sh/) source you can install from with the [`skills` CLI](https://github.com/vercel-labs/skills).

Each skill is a directory under `skills/<name>/` containing a `SKILL.md` (plus any helper scripts/evals). The `skills` CLI installs them into whichever AI coding agents you have (Cursor, Codex, Claude Code, and [many more](https://github.com/vercel-labs/skills#supported-agents)).

## Available skills

| Skill | Description |
| --- | --- |
| `agentsmd-generator` | Generate project-level `AGENTS.md` onboarding guides covering structure, tooling, testing, task flow, and conventions. |
| `jj-case-insensitive-clone-fix` | Diagnose and fix the `jj git clone` "Failed to update refs" error on case-insensitive filesystems (e.g. macOS APFS). |
| `research_codebase` | Map how a codebase works today and save a dated, citation-backed report under `thoughts/`, using parallel sub-agents by default. |
| `sdd-linear` | Run the Spec-Driven Development (SDD) workflow with Linear issues, sub-issues, attachments, and comments as the system of record instead of `docs/specs`. |
| `sync-upstream` | Sync a fork's default branch with its upstream remote using merge or rebase, resolving conflicts as needed. |
| `work-breakdown` | Decompose large/ambiguous scope into smaller units of work with dependencies and parallelization. |

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

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to add or update a skill, run validation (`make validate`), and the commit/PR conventions.
