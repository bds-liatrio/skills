"""Behavior tests for the sdd-linear `assess-linear-sdd-state.py` assessor.

The assessor is the deterministic phase router for the Linear-backed SDD
workflow: it consumes the state snapshot produced by the linear-project-manager
sub-agent and returns the SDD phase + detailed state. These tests drive it
through its CLI (JSON snapshot on stdin, JSON decision on stdout), mirroring the
state coverage of the base SDD `assess-sdd-state.py` test suite.
"""

from __future__ import annotations

import json

from conftest import requires, run_script

SKILL = "sdd-linear"
SCRIPT = "assess-linear-sdd-state.py"


def decide(snapshot: dict) -> dict:
    proc = run_script(SKILL, SCRIPT, stdin=json.dumps(snapshot))
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


# Reusable building blocks for "later phase" snapshots.
SPEC = {"identifier": "ENG-1", "description_present": True}
DONE = {"state": "Done", "type": "completed"}
AUDIT_PASS = {"present": True, "status": "PASS"}


@requires("python3")
def test_s1_start_when_no_spec_issue() -> None:
    result = decide({})
    assert result["phase"] == 1
    assert result["detailed_state"] == "S1_START"
    assert result["spec"] is None


@requires("python3")
def test_s1_questions_when_scratch_questions_file_present() -> None:
    result = decide({"questions_file_present": True})
    assert result["phase"] == 1
    assert result["detailed_state"] == "S1_QUESTIONS"


@requires("python3")
def test_s1_when_issue_exists_but_description_missing() -> None:
    result = decide({"spec_issue": {"identifier": "ENG-1", "description_present": False}})
    assert result["phase"] == 1
    assert result["detailed_state"] == "S1_START"


@requires("python3")
def test_s2_start_when_task_list_attachment_missing() -> None:
    result = decide({"spec_issue": SPEC, "task_list_attachment_present": False})
    assert result["phase"] == 2
    assert result["detailed_state"] == "S2_START"


@requires("python3")
def test_s2_parents_done_when_no_subissues_yet() -> None:
    result = decide(
        {"spec_issue": SPEC, "task_list_attachment_present": True, "subissues": []}
    )
    assert result["phase"] == 2
    assert result["detailed_state"] == "S2_PARENTS_DONE"


@requires("python3")
def test_s2_subtasks_done_when_audit_missing() -> None:
    result = decide(
        {
            "spec_issue": SPEC,
            "task_list_attachment_present": True,
            "subissues": [{"state": "Todo", "type": "unstarted"}],
            "audit": {"present": False, "status": None},
        }
    )
    assert result["phase"] == 2
    assert result["detailed_state"] == "S2_SUBTASKS_DONE"


@requires("python3")
def test_s2_audit_failed_on_fail_status() -> None:
    result = decide(
        {
            "spec_issue": SPEC,
            "task_list_attachment_present": True,
            "subissues": [DONE],
            "audit": {"present": True, "status": "FAIL"},
        }
    )
    assert result["phase"] == 2
    assert result["detailed_state"] == "S2_AUDIT_FAILED"


@requires("python3")
def test_s2_audit_failed_on_unknown_status() -> None:
    # A present-but-unverified audit must not advance the workflow.
    result = decide(
        {
            "spec_issue": SPEC,
            "task_list_attachment_present": True,
            "subissues": [DONE],
            "audit": {"present": True, "status": None},
        }
    )
    assert result["phase"] == 2
    assert result["detailed_state"] == "S2_AUDIT_FAILED"


@requires("python3")
def test_s3_midflight_when_a_subissue_is_incomplete() -> None:
    result = decide(
        {
            "spec_issue": SPEC,
            "task_list_attachment_present": True,
            "subissues": [DONE, {"state": "In Progress", "type": "started"}],
            "audit": AUDIT_PASS,
        }
    )
    assert result["phase"] == 3
    assert result["detailed_state"] == "S3_MIDFLIGHT"


@requires("python3")
def test_s4_start_when_all_done_and_validation_missing() -> None:
    result = decide(
        {
            "spec_issue": SPEC,
            "task_list_attachment_present": True,
            "subissues": [DONE, DONE],
            "audit": AUDIT_PASS,
            "validation": {"present": False, "status": None},
        }
    )
    assert result["phase"] == 4
    assert result["detailed_state"] == "S4_START"


@requires("python3")
def test_s4_failed_when_validation_fails() -> None:
    result = decide(
        {
            "spec_issue": SPEC,
            "task_list_attachment_present": True,
            "subissues": [DONE],
            "audit": AUDIT_PASS,
            "validation": {"present": True, "status": "FAIL"},
        }
    )
    assert result["phase"] == 4
    assert result["detailed_state"] == "S4_FAILED"


@requires("python3")
def test_s4_complete_when_validation_passes() -> None:
    result = decide(
        {
            "spec_issue": SPEC,
            "task_list_attachment_present": True,
            "subissues": [DONE],
            "audit": AUDIT_PASS,
            "validation": {"present": True, "status": "PASS"},
        }
    )
    assert result["phase"] == 4
    assert result["detailed_state"] == "S4_COMPLETE"


@requires("python3")
def test_canceled_subissue_counts_as_terminal() -> None:
    # A canceled executable task should not block progression to validation.
    result = decide(
        {
            "spec_issue": SPEC,
            "task_list_attachment_present": True,
            "subissues": [DONE, {"state": "Canceled", "type": "canceled"}],
            "audit": AUDIT_PASS,
            "validation": {"present": False, "status": None},
        }
    )
    assert result["phase"] == 4
    assert result["detailed_state"] == "S4_START"
