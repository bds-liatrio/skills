# Linear Storage Adapter

This is an internal reference loaded by `SKILL.md` alongside the active base-SDD phase reference. It is the **translation layer** that redirects every SDD artifact from the filesystem (`docs/specs/`) to Linear.

Read this together with the base phase reference. The base reference tells you *what to produce and which gates to enforce*. This adapter tells you *where it goes in Linear and how to put it there*.

## How to use this adapter

For the active phase:

1. Follow the base-SDD phase reference for methodology, roles, quality bars, and gates.
2. Every time the base reference says to read or write a file under `docs/specs/`, stop and perform the mapped Linear operation in the table below instead.
3. Delegate the Linear operation to the `linear-project-manager` sub-agent using the request templates here.
4. Two — and only two — things stay on the local filesystem: the Phase 1 clarification questions file (an SDD *artifact*; deleted at the end of spec generation, see Phase 1 overrides) and the spec pointer file (a non-authoritative *cache* that speeds up startup, see "Local spec pointer" below). Linear remains the system of record; neither local file is.
5. Ignore base-SDD `[NN]` sequence numbers and numbered spec directories. The Linear issue identifier (e.g. `ENG-123`) is the spec's identity.

## Artifact mapping

| Base SDD artifact (filesystem) | Linear target | Status / state signal |
| --- | --- | --- |
| Spec document `[NN]-spec-[feature].md` | The spec **issue** itself; spec body = issue **description** (Markdown) | Label `sdd:phase-1` while drafting; `sdd:planning-ready` once spec is approved |
| Clarification questions `[NN]-questions-[N]-[feature].md` | **Stays on the local filesystem** at the standard SDD path; ephemeral scratch, deleted at end of Phase 1 | n/a |
| Task-list definition `[NN]-tasks-[feature].md` (parent tasks, proof artifacts, relevant files) | **Attachment** on the spec issue, titled `tasks-[feature].md` | Label `sdd:phase-2` |
| Executable sub-tasks (leaf tasks like 1.1, 1.2) | One **sub-issue** of the spec issue per executable task | Sub-issue workflow state (see state mapping) |
| Planning audit `[NN]-audit-[feature].md` | **Attachment** on the spec issue, titled `audit-[feature].md`, **plus** a status comment | Comment `SDD audit: PASS` / `SDD audit: FAIL (...)` + label `sdd:audit-pass` or `sdd:audit-fail` |
| Proof artifacts `[NN]-task-[TT]-proofs.md` | **Attachment** on the matching sub-issue, titled `task-[TT]-proofs.md`, **plus** a summary comment on that sub-issue | Sub-issue → `Done` once proofs attached |
| Validation report `[NN]-validation-[feature].md` | **Attachment** on the spec issue, titled `validation-[feature].md`, **plus** a status comment | Comment `SDD validation: PASS` / `SDD validation: FAIL (...)` + label `sdd:validated` or `sdd:validation-fail` |

### Task state mapping

The base skill's checkbox states map to Linear sub-issue workflow states:

| SDD checkbox | Linear sub-issue state |
| --- | --- |
| `[ ]` not started | `Todo` (or team backlog/unstarted equivalent) |
| `[~]` in progress | `In Progress` |
| `[x]` complete | `Done` |

Resolve exact state names against the issue's team workflow via the sub-agent; names and IDs are team-specific.

### Phase label scheme

Apply one `sdd:phase-N` label to the spec issue to hint the current phase (`sdd:phase-1` … `sdd:phase-4`), plus the status labels above. Labels are a hint only — the presence and PASS/FAIL of artifacts is the source of truth for state assessment.

### Local spec pointer (startup accelerator)

To make a fresh "continue" invocation resolve its target without searching Linear (or, worse, grepping prior chat transcripts), this skill keeps a tiny pointer file at `docs/specs/.sdd-linear.json`:

```json
{
  "team": "Sykesdev",
  "spec_issue": "SYK-15",
  "url": "https://linear.app/sykesdev/issue/SYK-15/...",
  "last_phase": 3,
  "updated_at": "2026-06-28T17:02:00Z"
}
```

Rules for the pointer:

- **It is a cache, never the source of truth.** Linear always wins. If the pointer disagrees with the live snapshot (e.g. the issue was deleted or advanced elsewhere), trust Linear and rewrite the pointer.
- **Write it whenever the active spec changes or a phase hands off:** on spec-issue creation (Phase 1), and at the end of every phase, refresh `spec_issue`, `url`, `last_phase`, and `updated_at`.
- **Read it first** during State Assessment step 1 (after an explicit invocation identifier, before any Linear search).
- It is safe to git-ignore; it holds no secrets, only public issue identifiers/URLs. Do not block on whether it is committed.

## Delegation contract

The `linear-project-manager` sub-agent is stateless and cannot see this conversation. Each delegation must include: target team and/or project, the spec issue identifier (once known), the exact Markdown content, and the exact data to return. Use these request templates (adapt fields to what the current Linear MCP exposes — the sub-agent discovers capabilities at runtime).

- **Resolve / search spec issue:** "In team `<TEAM>`, find the issue for feature `<feature>` (search title and the `sdd` label). Return identifier, URL, state, labels, description, and sub-issues with their states."
- **Create spec issue:** "In team `<TEAM>` (project `<PROJECT>` if given), create an issue titled `<title>` with this Markdown description: `<spec body>`. Add label `sdd`. Return identifier and URL."
- **Update spec description:** "Update issue `<ID>` description to this Markdown: `<spec body>`. Return confirmation."
- **Create executable sub-issues:** "Under parent issue `<ID>`, create these sub-issues in `Todo`, in order: `<list of task titles + one-line descriptions>`. Return each sub-issue's identifier, title, and URL."
- **Transition a sub-issue:** "Move sub-issue `<ID>` to `<Todo|In Progress|Done>`. Return resulting state."
- **Post a comment:** "On issue `<ID>`, post this comment (Markdown): `<text>`. Return confirmation + URL."
- **Set labels:** "On issue `<ID>`, set labels `<labels>` (create them if absent). Return applied labels."
- **Attach a document:** see the attachment fallback below.
- **State snapshot (single startup call):** "For issue `<ID>`: report whether the description is present, its labels and workflow state, which of the task-list / audit / validation artifacts exist (attachments or `SDD …` status comments) with the audit and validation PASS/FAIL status, and the executable sub-issue progress. **Return the result as a single JSON object in exactly the assessor schema below.** For sub-issue progress, prefer the compact `subissue_counts` form (`total` plus `terminal` = count whose state type is `completed`/`canceled`) so you do not enumerate every sub-issue; list individual `subissues` only when there are just a few or the identifiers are needed." This one delegation replaces separate discovery/snapshot/task-list calls — do not also fetch the task-list body here; that happens later, per phase.

Always read the sub-agent's final report and record the returned identifiers/URLs before continuing.

### Snapshot for the deterministic assessor

Have the sub-agent emit this JSON directly (so you pipe it straight into `{{skill_dir}}/scripts/assess-linear-sdd-state.py` with no hand-editing — see `SKILL.md` → State Assessment). The script applies the same phase logic as the base SDD assessor, so phase routing stays deterministic and tested:

```json
{
  "spec_issue": { "identifier": "ENG-123", "description_present": true, "labels": ["sdd", "sdd:phase-2"], "state": "In Progress" },
  "questions_file_present": false,
  "task_list_attachment_present": true,
  "subissue_counts": { "total": 50, "terminal": 12 },
  "audit": { "present": true, "status": "PASS" },
  "validation": { "present": false, "status": null }
}
```

Sub-issue progress accepts either form; pick the cheaper one:

- `subissue_counts` (preferred for many sub-issues): `{ "total": N, "terminal": M }`, where `terminal` counts sub-issues whose state `type` is `completed`/`canceled`. The sub-agent just counts — no enumeration. Authoritative when present.
- `subissues` (when few, or you need identifiers): the explicit list, e.g. `[{ "identifier": "ENG-124", "state": "Done", "type": "completed" }, …]`.

Notes: omit `spec_issue` (or its `identifier`) when no spec issue exists yet; `status` is `PASS`, `FAIL`, or `null`; for the list form a sub-issue counts as finished when its state `type` is `completed`/`canceled` (display-name fallback when `type` is absent). A present-but-unverified audit (`status: null`) does not advance the workflow.

## Attachment capability and fallback chain

The sub-agent's core, guaranteed capabilities are issues, sub-issues, descriptions, comments, labels, and state transitions. File attachment / upload support depends on what the Linear MCP currently exposes. For every artifact mapped to an "attachment" (task-list, audit, proofs, validation), delegate with this fallback chain and record which tier was used:

1. **Attachment (preferred):** Ask the sub-agent to attach the Markdown document to the issue/sub-issue with the specified title. If the MCP supports file upload or document attachment, use it.
2. **Linear document (if supported):** Create a Linear document holding the Markdown and link it to the issue.
3. **Comment (always-available fallback):** Post the full Markdown as a dedicated comment whose first line is a clear title, e.g. `SDD task-list (tasks-[feature].md)` / `SDD audit (audit-[feature].md)` / `SDD proofs (task-[TT]-proofs.md)` / `SDD validation (validation-[feature].md)`.

Always also post the short PASS/FAIL **status comment** for audit and validation regardless of which tier stored the full document, so state assessment never needs to parse attachment contents.

## Per-phase IO overrides

### Phase 1 — Spec generation (with base `sdd-1-generate-spec.md`)

- **Skip** all `docs/specs/` directory creation and the spec `.md` file write. Do not create numbered spec directories.
- **Target selection:** Before writing anything to Linear, confirm the destination Linear **team** (and **project** if the user wants one). Ask the user if not provided; do not guess on writes.
- **Clarification questions (filesystem exception):** When the base reference requires a questions round, write the questions file to the standard SDD path `docs/specs/[NN]-spec-[feature-name]/[NN]-questions-[N]-[feature-name].md` (use a local scratch sequence number; `01` if none exist). Point the user to it and stop for answers exactly as base SDD does. This file is ephemeral scratch.
- **Spec persistence:** Once the spec is approved, create the Linear spec issue with the full spec Markdown as the issue **description** (or update the description if the issue already exists). Title the issue with the feature name. Apply labels `sdd` and `sdd:phase-1`. Immediately write the spec pointer file `docs/specs/.sdd-linear.json` (team, `spec_issue`, `url`, `last_phase: 1`, `updated_at`) so later invocations resolve this spec without a search.
- **Cleanup:** After the spec issue exists and the user has approved the spec, delete the scratch questions file and remove the now-empty `docs/specs/[NN]-spec-[feature-name]/` scratch directory. The spec issue description is now the single source of truth.
- **Report** the spec issue identifier + URL and hand off to Phase 2.

### Phase 2 — Task list and audit (with base `sdd-2-generate-task-list-from-spec.md`)

- The base skill is two-stage: parent tasks first (with `TBD` sub-tasks), then sub-tasks after explicit user approval. Preserve both stages and the approval gate.
- **Parent tasks + proof artifacts + relevant files** live in the **task-list definition document**, stored as the `tasks-[feature].md` attachment on the spec issue (use the fallback chain). Do **not** create one sub-issue per parent task — the hierarchy is flat.
- **Executable sub-tasks** become **sub-issues** of the spec issue, one per leaf task, created only **after** the user approves sub-task generation. Use the sub-task title (e.g. `1.2 <description>`) as the sub-issue title and put the sub-task detail in the sub-issue description. Create them in `Todo`. Keep the full task-list document (the attachment) as the authoritative grouped plan; the sub-issues are the executable units.
- **Planning audit:** Produce the audit per the base reference. Store the full report as the `audit-[feature].md` attachment on the spec issue, post the `SDD audit: PASS/FAIL` status comment, and set `sdd:audit-pass` / `sdd:audit-fail`. Honor the base skill's remediation approval gate and re-audit loop. Do **not** advance to Phase 3 while any REQUIRED gate fails.
- Set label `sdd:phase-2`; on a passing audit, the spec is implementation-ready.

### Phase 3 — Implementation (with base `sdd-3-manage-tasks.md`)

- Implementation still happens in the **code repository** with real commits; only the SDD bookkeeping moves to Linear. Preserve the base skill's first-run git/workspace hygiene checks (verify a git repo, run `git status` before first changes, stop on unrelated dirty/untracked work, add ignore rules).
- **Pre-work:** Confirm the audit passed (status comment / label) before implementing. If not, return to Phase 2.
- **Per executable task = one sub-issue.** At the start of a task, transition its sub-issue `Todo → In Progress`. On completion, transition `→ Done`.
- **Proof artifacts:** Create the proof Markdown per the base reference, but instead of writing it under `docs/specs/.../[NN]-proofs/`, attach it to the matching sub-issue as `task-[TT]-proofs.md` (fallback chain) and post a short summary comment on that sub-issue that states what the task proves. The proof must exist in Linear **before** you mark the sub-issue `Done`.
- **Commits:** Follow the base commit discipline (one commit per task minimum, conventional format, proofs created before commit). Reference the Linear identifier so Linear auto-links the work: include the spec/sub-issue identifier in the branch name and commit message (e.g. branch `eng-123-<feature>`, commit trailer `Refs ENG-123`). Replace the base skill's `Related to T# in Spec NN` line with the Linear identifier reference.
- Set label `sdd:phase-3` while implementing.

### Phase 4 — Validation (with base `sdd-4-validate-spec-implementation.md`)

- **Inputs:** The spec = the issue description; the task list = the `tasks-[feature].md` attachment; proof artifacts = the per-sub-issue attachments/comments; relevant files + commits = the code repo (`git log`).
- **Auto-discovery:** Replace "scan `docs/specs/`" with resolving the spec issue whose sub-issues are all `Done` and whose validation is missing or failing. If several qualify and the user did not name one, ask.
- **Validation report:** Produce it per the base rubric and gates. Store the full report as the `validation-[feature].md` attachment on the spec issue, post the `SDD validation: PASS/FAIL` status comment, and set `sdd:validated` / `sdd:validation-fail`.
- **Transition:** On PASS, move the spec issue to the team's review/done equivalent (e.g. `In Review` or `Done`) per the user's workflow; set `sdd:phase-4`. On FAIL, keep it open and report the failing gates. Do not transition to a closed state on FAIL.

## Reporting from this adapter

Whenever you report Linear changes, always surface concrete identifiers and URLs: the spec issue, any created/updated sub-issues with their new states, attachment/comment confirmations (and which fallback tier was used), labels applied, and the audit/validation PASS/FAIL outcome. This keeps the workflow auditable without re-querying Linear.

Before handing off, refresh the spec pointer file `docs/specs/.sdd-linear.json` with the current `spec_issue`, `url`, `last_phase`, and `updated_at`. This is what lets the next invocation — especially in a fresh chat — skip straight to the snapshot instead of searching.
