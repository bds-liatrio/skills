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

Before doing any work, confirm all three. If any is missing, stop and tell the user how to resolve it.

1. **Base `sdd` skill installed.** This wrapper reads the base skill's phase references for methodology. Locate them at `{{skill_dir}}/../sdd/references/` (sibling skill). If that path does not exist, locate the installed skill whose frontmatter `name` is `sdd` (canonical: `~/.agents/skills/sdd/`). If `sdd` is not installed, instruct: `npx skills add liatrio-labs/spec-driven-workflow --skill sdd`.
2. **`linear-project-manager` sub-agent available.** It is the *sole* interface to Linear; you MUST delegate every Linear read and write to it and never call Linear MCP tools directly from this orchestrator. This agent is **bundled with the skill** at `{{skill_dir}}/agents/linear-project-manager.md`. If the harness already exposes a `linear-project-manager` sub-agent, use it as-is. If it does not, provision the bundled one (it is idempotent and will not overwrite an existing agent unless `--force`):

   ```bash
   {{skill_dir}}/scripts/install-linear-agent.sh
   ```

   By default it installs into `~/.agents/agents/` (the canonical location many tools symlink to). Pass `--dest ~/.cursor/agents` or `--dest ~/.claude/agents` to target a specific harness that does not read the canonical location. After provisioning, the harness may need to reload before the sub-agent is invocable.
3. **Linear reachable through the sub-agent.** A trivial read (e.g. list teams) confirms connectivity.

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

State lives in Linear, so the sub-agent gathers it and a bundled deterministic script makes the phase decision. Do not eyeball the phase — run the assessor.

1. **Resolve the spec issue.** Prefer an identifier supplied with the invocation (e.g. `ENG-123`). Otherwise delegate a search to the sub-agent by feature title and the `sdd` label. If a local scratch questions file exists (see adapter) for a feature with no spec issue yet, treat that feature as the target.
2. **Fetch a state snapshot** via the sub-agent: issue description presence (the spec), labels, workflow state, sub-issues with their states, and the task-list / audit / validation artifacts (presence plus their PASS/FAIL status comments). Assemble these into the snapshot JSON documented in the adapter.
3. **Run the deterministic assessor** on that snapshot and route by its output. It mirrors the base SDD assessor's phase logic, so the most error-prone decision is testable rather than guessed:

   ```bash
   echo '<snapshot-json>' | python3 {{skill_dir}}/scripts/assess-linear-sdd-state.py
   ```

   It prints `{ "phase", "detailed_state", "action_required", "recommendation" }`. Artifacts are the source of truth; the `sdd:phase-N` label is only a hint. The phase rules below are the same logic in prose for when the script cannot run.

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

After determining the phase, read **two** references and apply them together:

1. The matching base-SDD phase reference (methodology):
   - **Phase 1:** `{{skill_dir}}/../sdd/references/sdd-1-generate-spec.md`
   - **Phase 2:** `{{skill_dir}}/../sdd/references/sdd-2-generate-task-list-from-spec.md`
   - **Phase 3:** `{{skill_dir}}/../sdd/references/sdd-3-manage-tasks.md`
   - **Phase 4:** `{{skill_dir}}/../sdd/references/sdd-4-validate-spec-implementation.md`
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

`<suggested natural-language reply>`

You can also continue in a new chat if you want to keep context lean; this skill will reassess state from Linear (the spec issue, its sub-issues, attachments, comments, and labels). Provide the spec issue identifier so the reassessment can resolve it quickly.
```

Use a blank line between every distinct part of the handoff. Suggested replies include:

- `Continue SDD with task planning.`
- `Generate the sub-tasks.`
- `Continue SDD with implementation.`
- `Continue SDD with validation.`
- `Start SDD for a new feature.`

Do not label the handoff as a generic next-request section. Do not put the suggested reply before the likely next phase action. Do not compress the handoff into adjacent lines. Do not refer users to slash-style phase invocations or reference filenames for continuation; this router reassesses Linear state on the next invocation and loads the correct reference.
