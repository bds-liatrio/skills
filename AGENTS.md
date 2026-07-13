# Skills Catalog — Agent Guide

> Scope: Root project (applies to all subdirectories unless overridden)

Agent skills catalog for the [skills CLI](https://github.com/vercel-labs/skills). Each skill is `skills/<name>/SKILL.md` (+ optional helpers).

## Quick Facts

- **Primary language:** Markdown skills; Python 3.12+ for contracts and catalog scripts
- **Package manager:** [uv](https://docs.astral.sh/uv/) (`pyproject.toml`, `package = false`)
- **Entrypoints:** `task` via `Taskfile.yml`
- **CI:** `.github/workflows/ci.yml` → `task ci`; PR title lint; scheduled upstream sync

## Canonical docs

| Doc | Contents |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Repo shape, authored vs vendored, discovery contract, quality pipeline |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Bootstrap, `task` operations, local patterns (skills, tests, vendor sync) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Human contributor workflow, upstream PAT, commit/PR conventions |
| [README.md](README.md) | Install UX and public skill inventory |

## Orientation (one screen)

- **Authored** skills: edit `skills/<name>/`; dir name = frontmatter `name`.
- **Vendored** skills: edit `upstream-skills.toml` only → `task sync-upstream-skills`; never hand-edit vendored trees.
- Day-to-day gate: `task ci` (`validate` + `lint`). Details: [DEVELOPMENT.md](docs/DEVELOPMENT.md).
- How the catalog fits together: [ARCHITECTURE.md](docs/ARCHITECTURE.md).
- `.lavish/` is local scratch, not canon.

## Documentation Duties

- Update `README.md` when the skill list or install story changes
- Update `docs/DEVELOPMENT.md` / `docs/ARCHITECTURE.md` when ops or structure change
- Update `CONTRIBUTING.md` when validation/sync/PR rules change
- Keep skill `description` frontmatter accurate (discovery + install UX)

## Finish the Task Checklist

- [ ] `task ci` clean (or `task validate` + relevant lint)
- [ ] Relevant docs updated (`README.md` / `docs/*` / `CONTRIBUTING.md` as needed)
- [ ] Summarize changes in conventional commit form (e.g. `feat: …`, `fix: …`, `docs: …`)
- [ ] No hand-edits to vendored `skills/<name>/` without catalog + re-sync
