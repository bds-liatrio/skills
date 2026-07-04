# Contributing

Thanks for your interest in contributing skills to this repository.

## What lives here

Each skill is a directory under `skills/<name>/` containing a `SKILL.md` with YAML frontmatter. The `skills` CLI discovers skills by their frontmatter `name` (not the directory name), so keep them consistent.

```text
skills/
  my-skill/
    SKILL.md        # required: frontmatter with `name` and `description`
    scripts/        # optional helper scripts (keep them executable)
    evals/          # optional evaluation cases
```

## Adding or updating a skill

1. Create `skills/<name>/SKILL.md` with at least:

   ```markdown
   ---
   name: my-skill
   description: What this skill does and when an agent should use it.
   ---

   # My Skill

   Instructions for the agent...
   ```

2. Keep the directory name equal to the frontmatter `name`.
3. If you add shell scripts, ensure they are executable (`chmod +x`).
4. Validate locally before opening a PR.

## Adding an upstream skill (vendored)

Third-party skills you want to install from this source but not maintain by hand
are declared in [`upstream-skills.toml`](upstream-skills.toml) and copied in
automatically. To add one:

1. Add a `[[skill]]` entry to `upstream-skills.toml` (`name`, `repo`, optional
   `path`/`ref`). The `name` must match the upstream frontmatter `name`. You can
   also generate entries from a project's installed skills with
   `make capture-project PROJECT=/path/to/project`.
2. Run `make sync-upstream-skills` to clone the upstream repo and copy its skill
   folder into `skills/<name>/`, recording provenance in
   `upstream-skills.lock.json`.
3. Commit the catalog, the vendored `skills/<name>/`, and the lockfile together.

A scheduled GitHub Action (`Sync Upstream Skills`) re-runs the sync so vendored
copies stay current without manual effort. Do not hand-edit `skills/<name>/` for
vendored skills; edit the catalog and re-sync.

**Licensing.** Only vendor permissively licensed skills — the sync refuses
copyleft licenses (GPL/AGPL/LGPL). The upstream `LICENSE`/`NOTICE` is copied into
the vendored folder to preserve attribution. Note that install telemetry counts
toward this repo (`SystemFiles/skills`), not the upstream source.

Local/project-built skills (no shareable git source) are intentionally out of
scope for the catalog; `make capture-project` flags them as candidates for
promotion into this repo as first-class authored skills instead.

## Local development

This project uses [uv](https://docs.astral.sh/uv/) for all Python tooling. Install uv, then:

```bash
uv sync               # creates .venv and installs the dev dependency group
make install-hooks    # installs pre-commit git hooks
```

`uv` provisions a compatible Python (3.12+) automatically; you do not need to manage a venv or `pip` yourself. Prefix ad-hoc Python commands with `uv run` (e.g. `uv run pytest -q`).

Run the checks:

```bash
make validate          # contract test: every SKILL.md has valid name/description
make lint              # full pre-commit gate (markdownlint, cspell, gitleaks, ...)
make verify-discovery  # list skills via the skills CLI from this local path
```

## Commit and PR conventions

- Commit messages and **PR titles** must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. PR titles are validated automatically.
- Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Suggested branch names: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`.
- Ensure the pre-commit gate passes before requesting review.

## Secrets

`gitleaks` scans committed content. Never commit credentials, tokens, or real secret values.
