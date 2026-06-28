#!/usr/bin/env python3
"""Deterministic SDD phase assessor for the Linear-backed workflow.

This is the Linear analog of the base SDD `assess-sdd-state.py`. The base
script scans `docs/specs/` on the filesystem; this one cannot talk to Linear
directly (all Linear access is delegated to the `linear-project-manager`
sub-agent). Instead it consumes a **state snapshot** the sub-agent produces and
applies the same phase-routing logic, so the most error-prone decision (which
SDD phase are we in?) is deterministic and unit-testable rather than left to
the model.

Input: a JSON snapshot, read from a file argument or stdin. Schema:

    {
      "spec_issue": {                  // omit/null if no spec issue exists yet
        "identifier": "ENG-123",
        "description_present": true,   // spec body written into the issue
        "labels": ["sdd", "sdd:phase-2"],
        "state": "In Progress"
      },
      "questions_file_present": false, // local scratch questions file exists,
                                       // spec issue not yet created
      "task_list_attachment_present": true,
      "subissues": [                   // executable tasks (flat)
        {"identifier": "ENG-124", "state": "Done", "type": "completed"},
        {"identifier": "ENG-125", "state": "In Progress", "type": "started"}
      ],
      "audit":      {"present": true,  "status": "PASS"},  // status: PASS|FAIL|null
      "validation": {"present": false, "status": null}
    }

Sub-issue progress may be supplied two ways; pick whichever is cheaper for the
sub-agent to assemble:

  * `subissues`: the explicit per-task list shown above. Use it when the task
    set is small or you need the identifiers anyway.
  * `subissue_counts`: a compact `{ "total": N, "terminal": M }` summary. Use it
    for large features so the sub-agent never has to enumerate every sub-issue
    (it only needs to count how many exist and how many are completed/canceled).
    When present, `subissue_counts` is authoritative and `subissues` is ignored.

Output: JSON describing the resolved phase, detailed state, and next action,
mirroring the base assessor's vocabulary.
"""

from __future__ import annotations

import json
import sys

# Linear workflow-state categories/names that count as a terminal (no longer
# blocking) executable task. Prefer the state `type` (category) when present;
# fall back to the display name.
TERMINAL_TYPES = {"completed", "canceled", "cancelled"}
TERMINAL_NAMES = {"done", "completed", "complete", "canceled", "cancelled", "closed"}


def _is_terminal(subissue: dict) -> bool:
    state_type = str(subissue.get("type") or "").strip().lower()
    if state_type:
        return state_type in TERMINAL_TYPES
    return str(subissue.get("state") or "").strip().lower() in TERMINAL_NAMES


def _passed(section: dict | None) -> bool:
    """True only when a present artifact explicitly reports a PASS status."""
    if not section or not section.get("present"):
        return False
    return str(section.get("status") or "").strip().upper() == "PASS"


def _subissue_progress(snapshot: dict) -> tuple[bool, int]:
    """Return ``(any_exist, incomplete_count)`` for the executable sub-issues.

    Accepts either the compact ``subissue_counts`` summary (authoritative when
    present) or the explicit ``subissues`` list. The compact form lets the
    sub-agent report a large feature as ``{"total": 50, "terminal": 49}``
    instead of enumerating every sub-issue.
    """
    counts = snapshot.get("subissue_counts")
    if isinstance(counts, dict) and counts.get("total") is not None:
        total = int(counts.get("total") or 0)
        terminal = int(counts.get("terminal") or 0)
        return total > 0, max(total - terminal, 0)

    subissues = snapshot.get("subissues") or []
    incomplete = [s for s in subissues if not _is_terminal(s)]
    return bool(subissues), len(incomplete)


def assess(snapshot: dict) -> dict:
    """Map a Linear state snapshot to an SDD phase recommendation."""
    spec = snapshot.get("spec_issue") or {}
    identifier = spec.get("identifier")
    description_present = bool(spec.get("description_present"))

    audit = snapshot.get("audit") or {}
    validation = snapshot.get("validation") or {}
    has_subissues, incomplete_subissues = _subissue_progress(snapshot)

    result: dict = {
        "spec": identifier,
        "phase": 0,
        "detailed_state": "",
        "action_required": "",
    }

    # Phase 1: no spec issue yet, or the issue exists without a spec body.
    if not identifier or not description_present:
        result["phase"] = 1
        if snapshot.get("questions_file_present"):
            result["detailed_state"] = "S1_QUESTIONS"
            result["action_required"] = "Answer Clarification Questions (Phase 1)"
        else:
            result["detailed_state"] = "S1_START"
            result["action_required"] = "Generate Spec (Phase 1)"
        return _finish(result)

    # Phase 2: spec exists; task-list definition (attachment) missing.
    if not snapshot.get("task_list_attachment_present"):
        result["phase"] = 2
        result["detailed_state"] = "S2_START"
        result["action_required"] = "Generate Task List (Phase 2)"
        return _finish(result)

    # Phase 2: task-list exists but executable sub-issues not created yet
    # (analog of the base skill's parent-tasks-with-TBD state).
    if not has_subissues:
        result["phase"] = 2
        result["detailed_state"] = "S2_PARENTS_DONE"
        result["action_required"] = "Review Parent Tasks & Generate Sub-tasks (Phase 2)"
        return _finish(result)

    # Phase 2: sub-issues exist but no audit yet.
    if not audit.get("present"):
        result["phase"] = 2
        result["detailed_state"] = "S2_SUBTASKS_DONE"
        result["action_required"] = "Generate Planning Audit (Phase 2)"
        return _finish(result)

    # Phase 2: audit present but not passing (FAIL or unknown status).
    if not _passed(audit):
        result["phase"] = 2
        result["detailed_state"] = "S2_AUDIT_FAILED"
        result["action_required"] = "Fix Planning Audit Failures (Phase 2)"
        return _finish(result)

    # Audit passed -> planning complete. Decide implementation vs validation.
    if incomplete_subissues:
        result["phase"] = 3
        result["detailed_state"] = "S3_MIDFLIGHT"
        result["action_required"] = "Implement Tasks (Phase 3)"
        return _finish(result)

    if not validation.get("present"):
        result["phase"] = 4
        result["detailed_state"] = "S4_START"
        result["action_required"] = "Validate Implementation (Phase 4)"
        return _finish(result)

    if not _passed(validation):
        result["phase"] = 4
        result["detailed_state"] = "S4_FAILED"
        result["action_required"] = "Fix Validation Failures (Phase 4)"
        return _finish(result)

    result["phase"] = 4
    result["detailed_state"] = "S4_COMPLETE"
    result["action_required"] = "Validation Complete. Start next feature (Phase 1)"
    return _finish(result)


def _finish(result: dict) -> dict:
    target = result["spec"] or "no spec issue yet"
    result["recommendation"] = (
        f"Phase {result['phase']}: {result['action_required']} for {target}"
    )
    return result


def main(argv: list[str]) -> int:
    raw = ""
    if len(argv) > 1 and argv[1] not in ("-", "--stdin"):
        with open(argv[1], "r", encoding="utf-8") as handle:
            raw = handle.read()
    else:
        raw = sys.stdin.read()

    try:
        snapshot = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON snapshot: {exc}"}), file=sys.stderr)
        return 2

    print(json.dumps(assess(snapshot), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
