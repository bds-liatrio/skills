---
name: research_codebase
description: Produce a thorough, citation-backed map of how an existing codebase works today and save it as a dated document under `thoughts/`. Use when the user asks to research, document, understand, or map how part of a codebase works, how components interact, or where functionality lives, and wants a durable written report rather than a one-off answer.
disable-model-invocation: true
---

# Research Codebase

Document how the codebase works **as it exists today**, then write the findings to a dated research document. Self-contained: the only helper it needs ships in `scripts/`. It dispatches parallel sub-agents by default, falling back to sequential research only when your agent can't spawn them.

## The one rule: describe, don't evaluate

Your job is to document, not critique. While researching:

- Describe what exists, where it lives, how it works, and how pieces interact.
- Do NOT suggest improvements, refactors, optimizations, or future work.
- Do NOT do root-cause analysis or flag problems.
- Do those things only if the user explicitly asks.

You are drawing a technical map of the current system.

## Step 1 — Get the question

If no research question was given, ask for one and wait:

> What part of the codebase should I research? Give me a question or area of interest.

## Step 2 — Read what's referenced

If the user names specific files (tickets, docs, code), read each **in full** (no truncation) before anything else, so you decompose the work with full context.

## Step 3 — Decompose

Break the question into concrete facets (components, data flow, entry points, config, tests, etc.). If your agent has a todo/checklist tool, record the facets there to track progress.

## Step 4 — Investigate

Run three kinds of passes. **Default to parallel sub-agents: dispatch one sub-agent (or task) per facet/pass so they run concurrently. Use this path whenever your agent can spawn sub-agents.** Only fall back to running the passes yourself, sequentially, when sub-agents aren't available.

1. **Locate** — find *where* relevant files, components, configs, and tests live (file search + grep).
2. **Analyze** — read the located files and document *how* they work and connect. Capture exact `path:line` references as you go.
3. **Find patterns** — find existing examples/usages of the relevant patterns elsewhere in the repo.

Optional passes, only when relevant:

- **Prior research** — scan the `thoughts/` directory (if present) for related earlier documents; treat them as historical context, not current truth.
- **External docs** — only if the user explicitly asks; return links and include them in the report.
- **Issue tracker** — only if relevant and your agent already has access to one; never assume a specific integration exists.

Rules for this step:

- Whoever investigates is a documentarian: describe, never evaluate.
- The live codebase is the source of truth; prior `thoughts/` docs are secondary.
- Wait for every pass to finish before synthesizing.

## Step 5 — Synthesize

Combine the findings: connect components, keep concrete `path:line` references, and answer the question with evidence. Prioritize live-code findings; use `thoughts/` only as supplementary history.

## Step 6 — Gather metadata

Run the bundled script from the repo root to capture document metadata:

```bash
scripts/spec_metadata.sh
```

It prints `date`, `researcher`, `git_commit`, `branch`, `repository`, and `last_updated*` values for the frontmatter. Works in any git repo, including jj-colocated ones.

## Step 7 — Write the document

Default path: `thoughts/research/YYYY-MM-DD-<topic>.md` (add a ticket id when there is one, e.g. `YYYY-MM-DD-ENG-1234-<topic>.md`). Create the directory if needed. Never write placeholder values — fill every field from real data.

```markdown
---
date: <from spec_metadata.sh>
researcher: <from spec_metadata.sh>
git_commit: <from spec_metadata.sh>
branch: <from spec_metadata.sh>
repository: <from spec_metadata.sh>
topic: "<user's question>"
tags: [research, codebase, <relevant-components>]
status: complete
last_updated: <from spec_metadata.sh>
last_updated_by: <from spec_metadata.sh>
---

# Research: <topic>

**Date**: <date>
**Researcher**: <researcher>
**Git commit**: <git_commit>
**Branch**: <branch>
**Repository**: <repository>

## Research question
<original question>

## Summary
<high-level answer describing what exists>

## Detailed findings

### <Component / area>
- What exists and how it works (`path/to/file.ext:123`)
- How it connects to other components

## Code references
- `path/to/file.ext:123` — what's there
- `other/file.ext:45-67` — what that block does

## Architecture / patterns
<current patterns and conventions found>

## Historical context (from thoughts/)
<relevant earlier notes, if any, with their paths>

## Related research
<links to other documents under thoughts/research/>

## Open questions
<anything still unresolved>
```

## Step 8 — Optional GitHub permalinks

If `gh` is installed and the commit is pushed (on the default branch or already on the remote), replace local references with permalinks:

```bash
gh repo view --json owner,name
# https://github.com/<owner>/<repo>/blob/<commit>/<file>#L<line>
```

Skip this step entirely if `gh` is unavailable or the work is unpushed.

## Step 9 — Present and follow up

- Give the user a concise summary plus the document path and key `path:line` references.
- For follow-ups, append to the same document instead of starting a new file: bump `last_updated`/`last_updated_by`, add a `last_updated_note`, and add a `## Follow-up <date>` section.

## Bundled helper

- `scripts/spec_metadata.sh` — prints the metadata block for the frontmatter. Execute it; don't reimplement it.
