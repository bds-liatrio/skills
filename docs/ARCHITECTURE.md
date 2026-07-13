# Architecture

This repo is a **skills.sh source catalog**, not an application. Consumers install skills with the [skills CLI](https://github.com/vercel-labs/skills) (`npx skills add SystemFiles/skills …`). Agents load installed `SKILL.md` files; this repo’s Python tooling only validates the catalog and vendors upstream copies.

## Layout

```text
.
├── skills/<name>/          # installable units (authored + vendored)
│   └── SKILL.md            # required; YAML frontmatter name + description
├── scripts/                # catalog maintenance (sync / capture)
├── tests/                  # pytest contracts + script unit tests
├── upstream-skills.toml    # declaration of vendored skills
├── upstream-skills.lock.json
├── Taskfile.yml            # single automation entry point
├── docs/                   # agent/dev architecture + local development
└── .github/workflows/      # ci, pr-title-lint, sync-upstream-skills
```

Optional under a skill: `scripts/`, `evals/`, `references/`, `examples/`, attribution files (`LICENSE`, `NOTICE`).

## Two skill populations

```text
  authored                          vendored
  ────────                          ────────
  Edit skills/<name>/ directly      Edit upstream-skills.toml only
       │                                 │
       │                                 ▼
       │                    task sync-upstream-skills
       │                    (scripts/sync_upstream_skills.py)
       │                                 │
       │                                 ▼
       │                    skills/<name>/ + lockfile
       ▼                                 │
  tests/test_skill_contract.py ◄─────────┘
  (every */SKILL.md: name, description, dir==name, unique)
```

| Kind | Source of truth | Rule |
| --- | --- | --- |
| **Authored** | `skills/<name>/` in this repo | Edit freely; keep dir name = frontmatter `name` |
| **Vendored** | `upstream-skills.toml` + upstream git | Do not hand-edit `skills/<name>/`; change catalog → re-sync → commit tree + lockfile |

Sync clones each `[[skill]]`, copies the skill folder (and LICENSE/NOTICE), refuses copyleft licenses, writes provenance to `upstream-skills.lock.json`. Scheduled workflow [sync-upstream-skills](../.github/workflows/sync-upstream-skills.yml) refreshes vendored copies; pushes use `SYNC_UPSTREAM_PAT` so other workflows still fire.

`task capture-project PROJECT=…` scans another project’s installed skills and proposes catalog entries. Local-only skills with no shareable git source stay out of the catalog (promotion target: authored skills here).

## Discovery contract

The skills CLI finds skills by **frontmatter `name`**, not directory name alone. Contract tests enforce:

- Non-empty `name` and `description`
- Directory name equals frontmatter `name`
- Names unique across `skills/`
- A pinned `EXPECTED_SKILLS` set stays present (authored baseline; update when adding/removing authored skills)

Install surface for humans: root `README.md` skill tables.

## Quality pipeline

```text
local / CI
    task ci
      ├─ task validate  →  uv run pytest -q
      └─ task lint      →  uv run pre-commit run --all-files
                            (markdownlint, cspell, gitleaks, …)

local (opt-in; needs Cursor agent CLI)
    task evals:validate          →  scripts/validate_evals.py
    task evals [SKILL=<name>]    →  agent -p (Sonnet 5): one process per eval in parallel, then aggregate

PR title  →  Conventional Commits (pr-title-lint workflow)
```

No runtime services or Docker: catalog + scripts only. `pyproject.toml` sets `package = false`; uv only manages the dev dependency group.

## Skill-internal patterns (authored)

Prefer **deterministic helpers** under `skills/<name>/scripts/` for anything an agent would otherwise invent (CLIs, schemas, allowlists). Cover them from repo-root `tests/`.

Skills that talk to external systems (GitHub, etc.) should keep **evals offline** via local snapshots (no live I/O). Reserve mocks for script unit tests — e.g. `issue-triage` uses issue fixtures in `evals/` and `mock_gh.py` only under `tests/`.

## Non-canon paths

- `.lavish/` — local review artifacts; not architecture or process canon
- `.agents/`, `skills-lock.json` — install-side artifacts; gitignored (this repo is a source, not a consumer)
- `skills/*-workspace/` — skill-creator eval run workspaces; gitignored

## Related docs

- [DEVELOPMENT.md](DEVELOPMENT.md) — setup, tasks, day-to-day patterns
- [CONTRIBUTING.md](../CONTRIBUTING.md) — contributor / PR conventions
- [README.md](../README.md) — install UX and skill inventory
