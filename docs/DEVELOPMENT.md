# Local Development

Setup, day-to-day commands, and patterns for working in this catalog. Architecture and skill populations: [ARCHITECTURE.md](ARCHITECTURE.md). Contributor/PR rules: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Prerequisites

| Tool | Role |
| --- | --- |
| [uv](https://docs.astral.sh/uv/) | Python 3.12+ toolchain + deps (`uv sync`) |
| [Task](https://taskfile.dev) | Single automation entry point (`Taskfile.yml`) |
| Node / `npx` | Only for `task verify-discovery` (skills CLI) |
| Cursor `agent` CLI | Only for `task evals` (skill-creator agent runs) |

No Docker, no local services, no app `.env` for ordinary work.

## Bootstrap

```bash
uv sync
task install-hooks   # pre-commit + commit-msg (commitlint)
task --list
```

Ad-hoc Python always via uv:

```bash
uv run pytest -q
uv run pytest tests/test_skill_contract.py -q
uv run python scripts/sync_upstream_skills.py
```

## Common operations

| Goal | Command |
| --- | --- |
| Full gate (same as CI) | `task ci` |
| Contract + unit tests | `task validate` (alias: `task test`) |
| Lint / format / secrets | `task lint` |
| Validate skill-creator `evals/evals.json` | `task evals:validate` (optional `SKILL=name`) |
| Run skill-creator evals via Cursor agent | `task evals` (all skills with `evals/`); `task evals SKILL=name` (one). Uses Sonnet 5 (`claude-sonnet-5-high`); override with `MODEL=…`. One agent per eval in parallel, then aggregate. |
| Confirm skills CLI sees this path | `task verify-discovery` |
| Refresh vendored skills | `task sync-upstream-skills` |
| Propose catalog from another project | `task capture-project PROJECT=/path/to/project` |
| Install git hooks | `task install-hooks` |

Prefer `task …` over inventing raw pipelines. CI runs `uv sync` then `task ci` ([ci.yml](../.github/workflows/ci.yml)).

## Patterns

### Adding or changing an authored skill

1. Create or edit `skills/<name>/SKILL.md` with frontmatter `name` + `description`.
2. Directory name **must** equal frontmatter `name`.
3. `chmod +x` any new scripts under `skills/<name>/scripts/`.
4. If the skill is part of the authored baseline, add its name to `EXPECTED_SKILLS` in `tests/test_skill_contract.py`.
5. Put guessable agent behavior in deterministic scripts; cover from `tests/`.
6. External I/O in evals: local fixtures/snapshots only; mocks belong in script unit tests (see `skills/issue-triage/`).
7. `task ci`, then update `README.md` skill table if the public inventory changed.

### Vendoring an upstream skill

1. Add `[[skill]]` to `upstream-skills.toml` (`name`, `repo`, optional `path` / `ref`).
2. `task sync-upstream-skills`.
3. Commit **together**: catalog, `skills/<name>/`, `upstream-skills.lock.json`.
4. Never hand-edit vendored trees; re-sync after catalog changes.

Or generate candidates: `task capture-project PROJECT=…` (local-only installs are flagged for authored promotion, not the catalog).

### Scripts and tests

- Repo-level tooling: `scripts/` (sync, capture).
- Skill-scoped helpers: `skills/<name>/scripts/`.
- Tests live under `tests/` at the repo root (import/path against skill scripts as needed).
- Pre-commit already runs `uv run pytest -q` as `skill-contract-tests`; still run `task ci` before review.

### Docs and spelling

- User-facing inventory/install: `README.md`.
- Process/PR: `CONTRIBUTING.md`.
- Agent map: root `AGENTS.md` → these docs.
- cspell currently scopes to a small set of authored markdown files (see `.pre-commit-config.yaml`); don’t assume new docs are spell-checked automatically.

### Secrets

- Don’t commit credentials; gitleaks is in the lint gate.
- Local development needs no secrets.
- Scheduled upstream sync in CI needs `SYNC_UPSTREAM_PAT` (see `CONTRIBUTING.md`).

### Branches and commits

- Branches: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`.
- Messages **and** PR titles: [Conventional Commits](https://www.conventionalcommits.org/) (`feat`, `fix`, `docs`, `chore`, …).
- Pass pre-commit before requesting review.

## Scratch vs canon

| Path | Treat as |
| --- | --- |
| `docs/`, `README.md`, `CONTRIBUTING.md`, `AGENTS.md` | Canon |
| `.lavish/` | Local review scratch — do not treat as process source of truth |
| `.agents/`, `skills-lock.json` | Install artifacts — gitignored |
| `skills/*-workspace/` | skill-creator eval run outputs — gitignored |
