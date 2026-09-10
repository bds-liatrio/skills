---
name: sdd-qa
description: "Ask SDD spec clarification questions ONE-by-ONE and write decisions back to the questions file. Slash-command only."
disable-model-invocation: true
---

# SDD Q&A

Ask questions from the spec questions file ONE-by-ONE. Write each decision and any extra context back to the question file. Formats: [references/qa-format.md](references/qa-format.md).

`$SKILL_DIR` is the absolute path of the directory containing this `SKILL.md`. Set it in the *same* command you run — shell state does not survive between tool calls.

## Hard rules

1. **Plan mode first.** If not in Plan mode, ask the user to switch (use the mode-switch tool when available). Stop. Do not resolve the questions file or ask questions until Plan mode is active.
2. Ask **one** unanswered question at a time. Wait.
3. Clarifying questions mid-flow: answer them; do **not** advance until they pick.
4. On a clear choice: write the decision into the file, then ask the next.

## Steps

### 1. Plan mode gate

Use the Plan-mode prompt in [references/qa-format.md](references/qa-format.md). Stop until Plan mode is on.

### 2. Resolve the file

```bash
SKILL_DIR=<absolute path to this skill's directory>
python3 "$SKILL_DIR/scripts/find-questions.py" <spec-or-glob>
```

`<spec-or-glob>` = user arg, path, `01`, feature slug, or glob like `01*questions.md`. Cwd = workspace root. If 0 or >1 matches, ask which file.

### 3. Run the loop

1. Read `$SKILL_DIR/references/qa-format.md` — follow its response + file-write formats exactly.
2. Find the first unanswered question (no `**Decision:**`, or all options still `[ ]`).
3. Ask **only that question**. Wait.
4. On a clear choice: write decision + context into the file, then ask the next.
5. After the last answer: write a decision summary table (see reference).
