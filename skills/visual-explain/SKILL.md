---
name: visual-explain
description: >-
  Generates a rich, interactive local HTML explanation of a diff, branch, PR,
  or uncommitted changes with Background, Intuition, Code walkthrough, and Quiz
  sections. Use before creating a PR, when reviewing a change, or any time a
  human wants to deeply understand what changed and why — especially phrases
  like "explain this diff", "visual explain", "walk me through this PR", or
  "what did this branch do".
argument-hint: "[pr-number | range | ref | uncommitted] [no quiz]"
---

# Visual Explain

Transform a code change into a self-contained HTML page that teaches what
changed and why: background on the surrounding system, the intuition behind the
change, a guided code walkthrough, and an optional comprehension quiz.

Adapted from `cw-explain` in
[sighup/claude-workflow](https://github.com/sighup/claude-workflow)
(no SPDX license published upstream at copy time). Deliverable is a **local**
HTML file under `.lavish/` — not a hosted Claude Code artifact.

## Overview

Act as a senior technical writer / educator:

- Explain changes to readers unfamiliar with the system, without dumbing them down
- Build intuition with concrete examples, toy data, and manipulable diagrams
- Walk through code in an order that makes sense to a human, not to `git diff`
- Test comprehension with substantive (not gotcha) quiz questions

## Critical Constraints

- **NEVER** modify source code — read-only toward the repository
- **NEVER** write outputs outside `.lavish/` (unless the user names another path)
- **NEVER** act as a pipeline gate — produce no verdict, create no tasks, block nothing
- **NEVER** pass the parent session's own summary of the change to an explainer
  child — the child works from the diff and repository alone
- **NEVER** embed credentials or secrets in the artifact — redact and warn
- **ALWAYS** produce a single self-contained HTML file — inline CSS and JS, no
  external assets, fonts, or CDNs
- **ALWAYS** exit early when the resolved diff is empty
- **ALWAYS** verify the staged file with the Step 5 checks before reporting done
- **ALWAYS** report the local HTML path as the deliverable

## Process

> If spawned as the explainer child with resolved parameters, skip Steps 1–5
> and execute the [Authoring Protocol](#authoring-protocol-explainer-child) only.

### Step 1: Resolve the Input

Resolution rules: [input-resolution.md](references/input-resolution.md).

| Invocation | Mode | Diff source |
|------------|------|-------------|
| (default) | Branch | `git diff <base>...HEAD` |
| `42` / `#42` | Pull request | `gh pr diff 42` + `gh pr view 42` |
| "uncommitted" | Working tree | `git diff HEAD` |
| `abc123..def456` or `<ref>` | Range / ref | `git diff <range>` |

**Quiz**: on by default; off when the user says "no quiz" / "skip the quiz".

**Early exit**: empty diff → report mode and stop.

### Step 2: Scope the Change

```bash
git diff <base>...HEAD --stat
git diff <base>...HEAD --name-only
git log <base>...HEAD --oneline
```

Capture total diff line count from `--stat` for walkthrough sizing.

In jj-colocated repos, the same `git diff` / `git log` commands work against the
underlying git store. Prefer them over inventing jj-only diff plumbing unless
git is unavailable.

### Step 3: Fix the Output Path

Write under `.lavish/` (local scratch; do not commit):

```bash
mkdir -p .lavish
```

Default path: `.lavish/explain-{slug}/explain-{slug}.html`, where `{slug}`
comes from the branch name, PR number (`pr-42`), or topic (lowercase, hyphens).

If the subject project already has a relevant spec / validation / review doc,
collect those paths for the child (Background anchoring). Do not require a
`docs/specs/` layout.

### Step 4: Spawn the Explainer Child (optional)

Prefer an isolated subagent when available. Prompt carries resolved parameters
only — no narrative about what the change "is":

```
Task({
  description: "Explain: {slug}",
  prompt: "You are the explainer child — execute the Authoring Protocol from the visual-explain skill. Parameters: mode={mode}; diff command={command}; base={base}; diff size={N files, N lines}; output path={path}; quiz={on|off}; context docs={paths | none}. Author the HTML file from the diff and repository alone, then report the file path and sections generated."
})
```

If `Task` is unavailable, or the user wants to watch authoring, run the
Authoring Protocol inline.

### Step 5: Verify, Then Deliver

Child completion is a claim, not proof. Check the file:

```bash
grep -c '<style>' <output-file>                          # ≥ 1
grep -c '<script>' <output-file>                         # ≥ 1
grep -cE 'id="(background|intuition|code|quiz)"' <output-file>   # 4 (3 if quiz off)
grep -cE '(src|href)="https?://' <output-file>           # must be 0
```

On failure, fix or re-instruct with the specific check that failed.

Deliverable is the local HTML path. Open it when useful:

```bash
open <output-file>   # macOS; xdg-open on Linux
```

Optional: if the user wants annotation / review loops, hand off to `lavish-safe`
on the same file — do not upload or publish.

## Authoring Protocol (explainer child)

1. **Read the change**: run the diff command; group files into logical clusters
   (feature core, tests, config, docs). For diffs > 1500 lines, deep-walk
   representative files and summarize the rest.
2. **Gather background**: parallel explore subagents when available — system
   context (how touched modules fit) and prior behavior (what the code did
   before). Read any provided context docs. Use LSP references/calls when available.
3. **Author the artifact**: write self-contained HTML to the output path per
   [explanation-template.md](references/explanation-template.md).
4. **Report**: output path, sections generated, redactions — nothing else.

## Output Requirements

```
VISUAL-EXPLAIN COMPLETE
=======================
Artifact: .lavish/explain-{slug}/explain-{slug}.html
Input mode: [branch | pr #N | uncommitted | range]
Diff size: N files, N lines
Sections: Background, Intuition, Code[, Quiz]
```

Do not run `gh pr create` — PR creation stays a human step.

## References

| Document | Contents |
|----------|----------|
| [explanation-template.md](references/explanation-template.md) | HTML contract: sections, diagrams, micro-interactions, quiz, style |
| [explanation-stylesheet.css](references/explanation-stylesheet.css) | Canonical `<style>` — copy verbatim |
| [explanation-script.js](references/explanation-script.js) | Canonical `<script>` — TOC scroll-spy + quiz; fill in `QUESTIONS` |
| [input-resolution.md](references/input-resolution.md) | Argument shapes, mode precedence, diff commands |

## Attribution

Pedagogy, HTML contract, stylesheet, and quiz script adapted from
`plugin/skills/cw-explain` in
[sighup/claude-workflow](https://github.com/sighup/claude-workflow).
This catalog variant drops Claude Code `Artifact` publishing and
`docs/specs/` staging in favor of local `.lavish/` HTML.
