# Clarify log

Path: `.issue-triage/<owner>__<repo>-<N>-clarify.md`

Per-question shape (mandatory):
[clarify-question-template.md](clarify-question-template.md).

```markdown
# Issue triage clarify — <owner/repo>#<N>
round: 1 / 4

## Round 1
### Q1 — <seal-checklist gap>
Why: <what would force an implementing agent to guess>
- **A)** <option> — <rationale>
- **B)** <option> — <rationale>
- **C)** <option> — <rationale>
- **D)** Other — user specifies
Recommended: <A|B|C|D> — <one-line why>
Answer: _pending_
```

Chat: header + current `## Round K` only (questions use the question template).
Resume: skip non-`_pending_` answers. Delete log after seal.
