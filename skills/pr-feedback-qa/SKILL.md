---
name: pr-feedback-qa
description: >-
  Work through PR or file-based review feedback one item at a time. For each
  item, offer Address, Skip, or GitHub Issue. Persist Q&A under
  .scratch/pr-feedback-qa as JSON so a session can resume. Use when the user
  wants to disposition multi-model review feedback, PR review comments, or a
  review markdown file with skip/track/address decisions and a final summary
  table.
compatibility: Requires authenticated gh CLI for PR input and GitHub Issue creation
---

# PR feedback Q&A

Disposition review findings one at a time. Templates: [references/qa-template.md](references/qa-template.md). Session JSON: [references/session-schema.json](references/session-schema.json). Session helper: `$SKILL_DIR/scripts/session_log.py`.

`$SKILL_DIR` is the absolute path of the directory containing this `SKILL.md`. Set it in the *same* command you run — shell state does not survive between tool calls.

## Hard rules

1. **Plan mode first.** If not in Plan mode, ask the user to switch (use the mode-switch tool when available). Stop. Do not load feedback or ask dispositions until Plan mode is active.
2. Stay on the current item until Address, Skip, or GitHub Issue is chosen.
3. After a clarifying answer, ask the same disposition prompt again.
4. Do not implement fixes, edit source, or resolve PR review threads in this skill.
5. Create GitHub issues only after the summary table and explicit user confirmation.
6. Never commit `.scratch/` files.

## Steps

### 1. Plan mode gate

Use the Plan-mode prompt in the template. Stop until Plan mode is on.

### 2. Resolve input

Accept one source:

- **File** — local review markdown (or similar).
- **PR** — `owner/repo#N` or URL. Fetch review bodies, inline comments, and conversation comments with `gh`. Keep author and URL on each finding. Deduplicate repeats. Keep conflicting advice as separate items.

### 3. Session

Ask: new persisted session, resume matching `.scratch/pr-feedback-qa/*.json`, or ephemeral (no file).

Persisted path: `.scratch/pr-feedback-qa/<slug>.json`.

```bash
SKILL_DIR=<absolute path to this skill's directory>

python3 "$SKILL_DIR/scripts/session_log.py" ensure-gitignore --repo-root .
python3 "$SKILL_DIR/scripts/session_log.py" init --repo-root . --slug <slug> --source-type file|pr --source <path-or-pr>
python3 "$SKILL_DIR/scripts/session_log.py" resume --repo-root . --slug <slug>
```

On every decision or clarification, write the session with `session_log.py record`. Ephemeral runs keep state in chat only.

### 4. Normalize items

Build an ordered list of findings. Number them `1..N`. Write findings into the session before the first question.

### 5. One item at a time

For each undecided item, follow the item prompt in the template:

- Short summary of the finding.
- Numbered fix options. Always include **Other (describe)**.
- Disposition: **A** Address, **S** Skip, **I** GitHub Issue.

Reply forms: `A1`, `S`, `I`, or a clarifying question.

Record:

| Disposition | Store |
| --- | --- |
| Address | Selected fix (or custom text) |
| Skip | Reason if given |
| GitHub Issue | Preferred fix if given; label `bug` and/or `enhancement` |

Do not advance until decided.

### 6. Summary

After the last item, show the decision summary table from the template. Persist it.

```bash
SKILL_DIR=<absolute path to this skill's directory>
python3 "$SKILL_DIR/scripts/session_log.py" summary --repo-root . --slug <slug>
```

### 7. GitHub issues (queued only)

List queued Issue items. Wait for confirmation. Then create each with `gh issue create`, apply `bug` / `enhancement`, link the PR or file source, and note the preferred fix. Write issue URLs back into the session.

Parent + sub-issues are allowed when the user asked for that shape.

## Anti-patterns

- Starting Q&A outside Plan mode
- Asking two items in one message
- Advancing after a clarification without a new disposition answer
- Creating issues before confirmation
- Silent implementation of Address items
