---
name: sdd-linear
description: "Run the Liatrio Spec-Driven Development (SDD) workflow with Linear as the system of record instead of docs/specs. Use when the user explicitly invokes SDD on Linear (e.g. /sdd-linear) and wants the spec persisted as a Linear issue, the task-list definition as an attachment, executable tasks as Linear sub-issues, and audits/proofs/validation as attachments, comments, and labels — all via the linear-project-manager sub-agent. NOTE: explicit-invocation only; this skill is not auto-triggered, and it wraps (does not replace) the base sdd skill."
disable-model-invocation: true
---

# Spec-Driven Workflow Orchestrator (Linear-backed)

You are the orchestrator for the Spec-Driven Development (SDD) workflow, configured to use **Linear** as the persistence layer. This skill is a thin wrapper over the base `sdd` skill: it reuses the base skill's methodology (roles, gates, audit logic, validation rubric) and only swaps the storage/IO layer from `docs/specs/` markdown files to Linear issues, sub-issues, attachments, comments, and labels.

Determine the current lifecycle phase from Linear, then load and follow the single matching base-SDD phase reference, applying the Linear storage adapter on top of it.

## Context Verification Marker

This wrapper adds one marker on top of the base SDD phase markers. Begin every response with the wrapper marker first, then the active base-SDD phase marker(s), in the order they were introduced.

The marker for this wrapper is: 🔗

So a Phase 2 response begins `🔗SDD2️⃣ …`, a Phase 3 response begins `🔗SDD3️⃣ …`, and so on. If either marker disappears, the agent has lost critical instructions — stop and reload the references.

## Prerequisites

Before doing any work, confirm all three. Resolve them with the minimum number of calls — do not spend the user's tokens hunting. If any is missing, stop and tell the user how to resolve it.

1. **Base `sdd` skill installed.** This wrapper reads the base skill's phase references for methodology. The wrapper and the base skill are frequently installed in *different* roots (e.g. this wrapper project-locally while the base is global), so the sibling path is not guaranteed. Resolve the base directory with **one shell command**, not a file glob — glob/file-search tools are typically scoped to the workspace and silently miss absolute paths under `$HOME`:

   ```bash
   for d in "{{skill_dir}}/../sdd" "$HOME/.agents/skills/sdd" "$HOME/.claude/skills/sdd" "$HOME/.cursor/skills/sdd" "$HOME/.codex/skills/sdd"; do
     if [ -f "$d/references/sdd-3-manage-tasks.md" ]; then (cd "$d" && pwd); break; fi
   done
   ```

   Use the single printed path as the base skill dir (call it `$SDD`) for all Reference Routing below. If nothing prints, `sdd` is not installed — stop and instruct: `npx skills add liatrio-labs/spec-driven-workflow --skill sdd`.

2. **`linear-project-manager` sub-agent reachable.** It is the *sole* interface to Linear; you MUST delegate every Linear read and write to it and never call Linear MCP tools directly from this orchestrator. The definition is **bundled** at `{{skill_dir}}/agents/linear-project-manager.md`. Make it reachable, then invoke it **by name** — resolve this in order:

   1. **Invoke the named sub-agent directly (normal path).** If the harness exposes a `linear-project-manager` sub-agent, delegate to it by name — e.g. `/linear-project-manager <task>`, "use the linear-project-manager subagent to …", or your harness's named-sub-agent call. Cursor, Claude Code, and Codex each register any `*.md` under their agents directory (`~/.cursor/agents/` and `.cursor/agents/`, plus the `.claude`/`.codex` equivalents) as a name-addressable sub-agent that inherits the parent's MCP tools, so once the file is installed it is callable by name — do **not** proxy it through a generic sub-agent. The bundled definition is not `readonly`, so it can perform Linear writes.
   2. **Provision, then invoke by name.** If no `linear-project-manager` sub-agent is registered yet, install the bundled definition into the harness agents directory, then invoke it by name as in step 1. The installer is idempotent (won't overwrite without `--force`); a freshly added agent may only become selectable in a new session/after a reload:

      ```bash
      {{skill_dir}}/scripts/install-linear-agent.sh                          # auto-detects installed harness agent dirs
      {{skill_dir}}/scripts/install-linear-agent.sh --dest ~/.cursor/agents  # or target one explicitly
      ```

   3. **Generic sub-agent + file reference (fallback only).** Only if the harness genuinely cannot register or invoke custom-named sub-agents, delegate to its general-purpose/exploration sub-agent and begin the prompt with `Read and adopt the agent definition at {{skill_dir}}/agents/linear-project-manager.md, then: <task>`. Let that sub-agent read the file in its own context — **never paste the agent definition into the delegation prompt**, which re-spends those tokens on every call — and run it non-readonly so it keeps MCP/tool access.

3. **Linear reachable.** Do not make a dedicated probe call — the first state-snapshot delegation in State Assessment doubles as the connectivity check.

## Skill Contract

This skill manages one SDD phase per invocation unless the loaded phase explicitly requires a smaller checkpoint. It must:

1. Resolve exactly one target Linear spec issue (or determine that a new one must be created).
2. Assess that issue's Linear state before routing.
3. Select exactly one phase, load the matching base-SDD phase reference, and load the Linear storage adapter.
4. Execute the phase instructions — routing all persistence through Linear per the adapter — or stop at a required approval gate.
5. Tell the user the selected spec issue (identifier + URL), detected state, current phase, the phase reference path, the Linear artifacts created or updated, and the next recommended natural-language request.

If multiple candidate spec issues match and the user request does not clearly identify one, ask which to continue before writing. If the selection is unambiguous, state why.

## Delegation Rule (non-negotiable)

All Linear access goes through the `linear-project-manager` sub-agent. The sub-agent is **stateless per invocation** and does not see this conversation, so every delegation must carry full context: the Linear team/project, the spec issue identifier, the exact content to write (Markdown), and precisely what to return (identifiers, URLs, states, labels, attachment/comment confirmations). Capture everything it returns into your working context and surface identifiers/URLs to the user.

See `{{skill_dir}}/references/linear-storage-adapter.md` for the delegation request templates and the full artifact mapping.

## State Assessment (Linear)

State lives in Linear, so the sub-agent gathers it and a bundled deterministic script makes the phase decision. Do not eyeball the phase — run the assessor. Keep startup to roughly one local pointer read plus one snapshot delegation; the steps below are ordered to stop as early as possible.

1. **Resolve the spec issue cheaply — stop at the first hit, in this order:**
   1. An identifier supplied with the invocation (e.g. `SYK-15`).
   2. The local pointer file `docs/specs/.sdd-linear.json` (this skill writes it on every handoff; see the adapter). Read it directly — it records the active `team`, `spec_issue`, `url`, and `last_phase`, so a fresh "continue" chat resolves the target with no Linear call at all.
   3. A local scratch questions file (Phase 1 in flight, no spec issue yet) — treat that feature as the target.
   4. Only if 1–3 all miss, delegate **one** search to the sub-agent, scoped to the resolved/likely team, for the `sdd` label or the feature title.

   Never reconstruct the identifier by reading prior chat transcripts or grepping session history — it is slow, token-heavy, and unreliable. If 1–4 all fail, ask the user for the identifier instead of searching blindly.

2. **Fetch the state snapshot in a single delegation.** Ask the sub-agent to return the state **already shaped as the assessor's JSON schema** (documented in the adapter), using the compact `subissue_counts` form when the feature has many sub-issues so it never enumerates them. This one call is also the Linear connectivity check. Do **not** split discovery, snapshot, and task-list retrieval into separate round-trips: the task-list body is only needed once the phase is confirmed, and only by the phases that consume it.

3. **Run the deterministic assessor** on that snapshot and route by its output. It mirrors the base SDD assessor's phase logic, so the most error-prone decision is testable rather than guessed:

   ```bash
   echo '<snapshot-json>' | python3 {{skill_dir}}/scripts/assess-linear-sdd-state.py
   ```

   Pipe the sub-agent's JSON straight in; do not hand-edit it, and do not read the script's source into context — just run it. It prints `{ "phase", "detailed_state", "action_required", "recommendation" }`. Artifacts are the source of truth; the `sdd:phase-N` label is only a hint. The phase rules below are the same logic in prose for when the script cannot run.

## Phase Rules

- **Phase 1 — Spec Generation**
  - **Condition:** No spec issue exists yet, or the spec issue exists but its description (the spec body) is missing/incomplete, or a clarification questions round is unanswered.
  - **Action:** Gather context, run the clarification check, and write the spec into the Linear issue description.

- **Phase 2 — Task List Generation and Audit**
  - **Condition:** The spec issue description is complete, but the task-list attachment is missing, or executable sub-issues have not been created, or the planning audit has not been generated and passed.
  - **Action:** Produce the task-list definition (attachment), create executable sub-issues after approval, and run the mandatory planning audit gate.

- **Phase 3 — Task Implementation**
  - **Condition:** Spec, task-list attachment, and a passing audit all exist, and one or more executable sub-issues are not yet `Done`.
  - **Action:** Implement each task, set sub-issue states, and attach proof artifacts to each completed sub-issue.

- **Phase 4 — Validation**
  - **Condition:** All executable sub-issues are `Done` and validation is missing or failing.
  - **Action:** Validate code against the spec using proof artifacts; attach the validation report and post its PASS/FAIL summary.

## Reference Routing

Only **after** the assessor has reported the phase, read **two** references and apply them together (loading them earlier wastes context on a phase you may not be in):

1. The matching base-SDD phase reference (methodology), under the `$SDD` base dir resolved in Prerequisite 1:
   - **Phase 1:** `$SDD/references/sdd-1-generate-spec.md`
   - **Phase 2:** `$SDD/references/sdd-2-generate-task-list-from-spec.md`
   - **Phase 3:** `$SDD/references/sdd-3-manage-tasks.md`
   - **Phase 4:** `$SDD/references/sdd-4-validate-spec-implementation.md`
2. The Linear storage adapter (IO override): `{{skill_dir}}/references/linear-storage-adapter.md`

**Precedence:** Follow the base phase reference for *what to think about and what quality gates to enforce*. Whenever it instructs a filesystem action under `docs/specs/`, do **not** perform it — perform the mapped Linear operation from the adapter instead. The single exception is the Phase 1 clarification questions file, which stays on the filesystem and is deleted at the end of spec generation (see adapter). Ignore the base skill's `[NN]` sequence numbers and numbered directories; the Linear issue identifier replaces them.

## User-Facing Reporting

When beginning or handing off work, state the phase and selected spec in plain language:

```markdown
Current SDD phase: Phase N — <phase name>
Selected spec: <Linear identifier + URL> (or `none yet — a new spec issue will be created`)
Phase reference: `<chosen base-SDD phase reference path>` + Linear storage adapter
Detected state: <state summary from the Linear snapshot>
Selection reason: <why this spec/phase was selected>
```

When a phase creates or updates Linear artifacts, include the affected identifiers/URLs (spec issue, sub-issues, attachments, comments, labels, state transitions), any approval gate reached, the audit/validation outcome when applicable, and a `How to Continue the SDD Workflow` handoff using this exact spacing pattern:

```markdown
## How to Continue the SDD Workflow

Likely next phase action: <what the skill will do next, or that the current workflow is complete>

To continue the workflow in this chat, reply with:

`<suggested natural-language reply, with the spec identifier baked in>`

You can also continue in a new chat to keep context lean; this skill reassesses state from Linear and will resolve the target instantly from the local pointer file (`docs/specs/.sdd-linear.json`) it just wrote. Including the identifier in your reply makes that resolution a single step.
```

Use a blank line between every distinct part of the handoff. Always bake the resolved spec identifier into the suggested reply so the next run skips straight to the snapshot. Suggested replies include:

- `Continue SDD with task planning for SYK-15.`
- `Generate the sub-tasks for SYK-15.`
- `Continue SDD with implementation for SYK-15.`
- `Continue SDD with validation for SYK-15.`
- `Start SDD for a new feature.`

Do not label the handoff as a generic next-request section. Do not put the suggested reply before the likely next phase action. Do not compress the handoff into adjacent lines. Do not refer users to slash-style phase invocations or reference filenames for continuation; this router reassesses Linear state on the next invocation and loads the correct reference.
