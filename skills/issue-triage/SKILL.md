---
name: issue-triage
description: >-
  Turn a rough GitHub Issue into an agent-executable sealed Issue body with
  ready + size labels so a Cloud Agent can implement from the body alone.
  Use when the user explicitly invokes issue triage, asks to seal an Issue,
  elaborate an agent-executable GitHub Issue spec, apply ready/size labels,
  or run the GitHub spec-bridge triage flow.
disable-model-invocation: true
---

# Goal / Intent

The output of this skill should:

- **Idea → Sealed Issue**: Convert a rough GitHub issue into a complete, agent-executable issue body. Seal it only when an implementing agent can ship using the body alone, without any further clarification.

**What is Unacceptable:**

- Vague requirements → unclear acceptance criteria, constraints, or goals
- Missing functional requirements → gaps in implementation coverage
- Inadequate technical considerations → architectural conflicts during implementation
- Unverifiable → Implementation cannot be verified against some deterministic gate
- Oversized issues → unmanageable task breakdown and loss of incremental progress

## Context management

When doing research, codebase exploration, or heavier github operations (like issue gathering and classification analysis), launch subagents to handle the work and report back to the parent.

## Prerequisites

1. Invoker names a single target Issue (`owner/repo#N` or URL). Touch **only** that
   Issue. You can still get context from other issues if needed to help answer questions during the initial exploratory phase.
2. `gh` CLI authenticated.
3. Working directory is the subject repository

If any prerequisite fails, stop and tell the user how to fix it.

## GitHub surface (mandatory)

All GitHub reads/writes go through [`scripts/issue_ops.py`](scripts/issue_ops.py).

**Do not invent ad-hoc mutating `gh` commands.**

```bash
python3 {{skill_dir}}/scripts/issue_ops.py view --repo <owner/repo> --issue <N>
python3 {{skill_dir}}/scripts/issue_ops.py preflight --repo <owner/repo> --issue <N>
python3 {{skill_dir}}/scripts/issue_ops.py ensure-labels --repo <owner/repo>
python3 {{skill_dir}}/scripts/issue_ops.py seal --repo <owner/repo> --issue <N> \
  --body-file <sealed.md> --size <XS|S|M|L|XL>
python3 {{skill_dir}}/scripts/issue_ops.py handoff --repo <owner/repo> --issue <N>
```

Validate a draft without writing:

```bash
python3 {{skill_dir}}/scripts/validate_sealed_body.py <sealed.md>
```

## Seal checklist (fail closed)

Do **not** seal until the body will contain all of (in this order):

1. Goals
2. Non-goals
3. Functional Requirements
4. Constraints
5. Assumptions (explicit invented defaults)
6. Size (t-shirt + one-line heuristic rationale)
7. User Acceptance Criteria
8. Testable / Verifiable

No “ask the human” TODOs in the sealed body.

Canonical skeleton: [references/sealed-body-skeleton.md](references/sealed-body-skeleton.md).
Sizing map: [references/sizing-heuristics.md](references/sizing-heuristics.md).

## Step 1 — Load Issue + preflight

Run `view`, then `preflight`. If preflight exits nonzero, **stop immediately**:
no clarify rounds, no draft, no writes. Tell the user why (in-progress and/or
open non-draft PR).

Snapshot the **current** body from `view` — that snapshot becomes
`## Original Ask` at seal time.

## Step 2 — Repo-grounded sufficiency

Before asking questions:
1. Scan the repo for existing hooks: config, templates, controllers, tests, docs, message bundles, similar features.
2. Cite concrete paths in a short sufficiency note.

**Fail closed**: do not invent surfaces that a quick look would disprove.

## Step 3 — Clarifying rounds

Persist Q&A in `.issue-triage/<owner>__<repo>-<N>-clarify.md` so an interrupted
agent can resume. Log shell: [references/clarify-log-template.md](references/clarify-log-template.md).
Every question: [references/clarify-question-template.md](references/clarify-question-template.md).

1. `python3 {{skill_dir}}/scripts/ensure_clarify_gitignore.py --repo-root .`
   (appends `.issue-triage/` if `.gitignore` exists; never create `.gitignore`)
2. If the log exists → resume (skip answered items; announce resume). Else create it.
3. Ask with those templates (file + chat). Chat = header + current round only.
   Cap **4** rounds; stop early when the checklist can be filled without guessing.
4. After each answer batch, update the log. Fold answers into the draft.
   Delete the log after successful seal.

## Step 4 — Size

Map scope using [references/sizing-heuristics.md](references/sizing-heuristics.md).
Put the result in the body as:

```markdown
## Size
S — <one-line heuristic rationale>
```

Pass the same size to `issue_ops seal --size …`.

## Step 5 — Draft sealed body

Build the full body locally from the skeleton. Run `validate_sealed_body.py`
before asking for approval.

**Original Ask hygiene:**

1. Place `## Original Ask` at the **bottom** of the Issue body.
2. Precede it with a markdown horizontal rule (`---`).
3. Do NOT preserve the ask as a comment-only backup.

## Step 6 — Human confirm

Present:

- Full sealed body draft
- Proposed labels: `ready` + `size/<…>`
- Sufficiency note (brief) and round count used

**Wait for explicit approval** (“write it”, “seal it”, “approve”). Never silent
overwrite.

## Step 7 — Seal write-back (after approval)

```bash
python3 {{skill_dir}}/scripts/issue_ops.py seal --repo <owner/repo> --issue <N> \
  --body-file <sealed.md> --size <SIZE>
```

## Step 8 — Handoff

```bash
python3 {{skill_dir}}/scripts/issue_ops.py handoff --repo <owner/repo> --issue <N>
```

Relay that Summary and Issue URL to the user. 

## Anti-patterns

- Sealing without `preflight`, or continuing after a failed preflight
- Ad-hoc `gh issue edit` / `gh label create` instead of `issue_ops`
- Creating a new Issue, opening/editing a PR, or writing Issue comments
- Changing assignee, project, milestone, issue type, custom fields, or relationships
- Mutating any Issue the invoker did not name
- Implementation / source changes during triage
- Silent GitHub mutation before approval
- Not following the [references/sealed-body-skeleton.md](references/sealed-body-skeleton.md)
- Size label without `## Size` rationale in the body
- Clarifying only in chat / re-asking answered log items / inventing a `.gitignore` just for `.issue-triage/`
