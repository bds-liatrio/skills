---
name: taskfile-automation
description: Scaffold consistent, portable repo automation using a Taskfile (https://taskfile.dev) as the single entry point, run identically on a developer machine and in CI. Adds Docker/Compose only when the repo has external runtime dependencies (a database, queue, browser, etc.). Use when a repo needs a task runner set up, when build/test/deploy commands drift between local and CI, or when someone asks for "3 Musketeers"-style automation with Task instead of Make.
disable-model-invocation: true
---

# Taskfile Automation

Set up repo automation so that **one command does the same thing everywhere** — a
developer's laptop and the CI runner execute the identical `task <name>`. This is the
[3 Musketeers](https://3musketeers.pages.dev/about/what-is-3musketeers/) pattern with two
deliberate changes:

- **[Task](https://taskfile.dev) replaces Make** as the orchestrator (cleaner YAML syntax,
  cross-platform, no tab pitfalls, built-in `--list`).
- **Docker + Compose are optional, not mandatory.** Reach for them only when the repo depends
  on something that must run *externally* (a database, cache, message queue, headless browser).
  When the toolchain runs fine on the host via the language's own env manager (`uv`, `nvm`,
  `mise`, `cargo`, …), skip containers entirely.

The three goals stay the same: **Consistency** (same commands on any OS and any Docker-capable
CI), **Control** (versions and pipeline live in the repo), **Confidence** (run the exact CI gate
locally before you push).

## Core principles

1. **Task is the only entry point.** Humans and CI both call `task <name>`. CI must not shell out
   to raw tool commands that bypass the Taskfile — if CI runs something, it is a task.
2. **Public vs internal tasks.** A public task holds the *portable* invocation (host command, or
   `docker compose run …`). Anything that needs a specific environment goes in an `internal: true`
   task that the public task delegates to. This mirrors 3 Musketeers' `target` / `_target`
   convention.
3. **A `ci` aggregate task.** One task chains the full gate (lint + test + build …) so CI and
   contributors invoke the same thing.
4. **Containers are a means, not the default.** Add a `compose.yml` only for external services or
   a toolchain that can't be assumed on the host. Document why each service exists.

## Step 1 — Inspect the repo

Gather the facts before writing anything:

1. **Language & toolchain** — read dependency manifests (`pyproject.toml`, `package.json`,
   `go.mod`, `Cargo.toml`, `Gemfile`, …) and any env-manager config (`.python-version`,
   `.nvmrc`, `mise.toml`). Determine how the toolchain is provisioned today.
2. **Existing automation** — is there a `Taskfile.yml`, `Makefile`, `Justfile`, or npm scripts?
   Capture the current target names and what each runs so you preserve intent (strangler-fig:
   migrate them, don't silently drop behavior).
3. **CI provider** — inspect `.github/workflows/`, `.gitlab-ci.yml`, `.circleci/`, etc. Note what
   each job actually runs; those commands become tasks.
4. **External runtime dependencies** — look for a database, cache, queue, object store, or browser
   the code/tests need at runtime (docker-compose files, connection strings, testcontainers,
   service clients). **This is the deciding factor for whether you introduce Docker/Compose.**
5. **Ambiguities** — if the toolchain provisioning or the canonical commands are unclear, ask the
   developer before scaffolding.

## Step 2 — Design the tasks

- Name tasks after the lifecycle: `lint`, `test`, `build`, `run`, `deploy`, plus a `ci` aggregate.
- Decide execution mode **per task** using Step 1's findings:
  - **Host mode** (default): the task runs the tool directly (e.g. `uv run pytest`, `npm test`).
  - **Container mode**: only when the task needs an external service or an unavailable toolchain.
    The public task runs `docker compose run --rm <service> …`; the actual command lives in an
    `internal: true` task when it needs to be re-run inside the container.
- A repo may mix modes freely — `test` can be host-mode while `e2e` (needs a DB) is container-mode.
- Add `desc:` to every public task so `task --list` is self-documenting. Mark helper tasks
  `internal: true` to keep the list clean.

## Step 3 — Scaffold the Taskfile

Write `Taskfile.yml` at the repo root. Host-only template (no external deps):

```yaml
version: '3'

tasks:
  default:
    desc: List available tasks
    cmds:
      - task --list
    silent: true

  lint:
    desc: Run linters/formatters
    cmds:
      - <host lint command>

  test:
    desc: Run the test suite
    cmds:
      - <host test command>

  ci:
    desc: Run the full gate the same way CI does
    cmds:
      - task: lint
      - task: test
```

Only if Step 1 found an external dependency, add a `compose.yml` and route the affected tasks
through it. Example for a suite that needs Postgres:

```yaml
# compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: dev
  app:
    build: .
    depends_on: [db]
    volumes:
      - .:/app
```

```yaml
# Taskfile.yml (excerpt)
  test:
    desc: Run the test suite against a real database
    cmds:
      - docker compose run --rm app task _test
      - defer: docker compose down -v   # clean up the network/volumes

  _test:
    internal: true   # runs inside the container, where the DB is reachable
    cmds:
      - <in-container test command>
```

Keep host-mode tasks as plain commands; do not wrap them in Docker "just in case."

## Step 4 — Wire CI to Task

Make CI call the same tasks. The CI job installs Task, provisions the toolchain, then runs the
aggregate:

```yaml
# GitHub Actions example
      - uses: arduino/setup-task@v2
        with:
          version: 3.x
          repo-token: ${{ secrets.GITHUB_TOKEN }}
      - run: task ci
```

If any task is container-mode, the CI runner only needs Docker — it does not need the language
toolchain installed, because that lives in the image.

## Step 5 — Validate and wrap up

1. Run `task --list` and confirm the tasks and descriptions read cleanly.
2. Run `task ci` locally and confirm it passes end-to-end. If you can't run it, it isn't done.
3. Remove the automation you replaced (old `Makefile`/`Justfile`/npm scripts) once tasks cover it —
   removal is part of the migration, not a later cleanup.
4. Update the repo's docs (README/CONTRIBUTING) to point at `task <name>`, and note that `task` and
   the toolchain manager are prerequisites.
5. Summarize what you scaffolded, which tasks are host- vs container-mode, and why any external
   service was introduced.
