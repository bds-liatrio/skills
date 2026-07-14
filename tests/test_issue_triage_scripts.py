"""Offline behavior tests for issue-triage scripts (mock_gh fixtures)."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import SKILLS_DIR, requires, run_script

SKILL = "issue-triage"
FIXTURES = SKILLS_DIR / SKILL / "evals" / "fixtures"
SCRIPTS = SKILLS_DIR / SKILL / "scripts"
MOCK_GH = SCRIPTS / "mock_gh.py"


def _copy_fixture(name: str, dest: Path) -> Path:
    src = FIXTURES / name
    shutil.copytree(src, dest)
    return dest


def _env(fixture_dir: Path) -> dict[str, str]:
    return {
        "ISSUE_TRIAGE_FIXTURE_DIR": str(fixture_dir),
        "ISSUE_TRIAGE_GH": " ".join(
            shlex.quote(part) for part in (sys.executable, str(MOCK_GH))
        ),
    }


def _ops(fixture_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_script(SKILL, "issue_ops.py", *args, env=_env(fixture_dir))


def _journal(fixture_dir: Path) -> list[dict]:
    path = fixture_dir / "gh-journal.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _mutations(fixture_dir: Path) -> list[dict]:
    return [e for e in _journal(fixture_dir) if e.get("mutated")]


VALID_BODY = """\
## Goals
G

## Non-goals
N

## Functional Requirements
1. F

## Constraints
C

## Assumptions
A

## Size
S — one slice

## User Acceptance Criteria
- [ ] U

## Testable / Verifiable
1. T

---

## Original Ask

### Summary
original
"""


@requires("python3")
def test_validate_sealed_body_ok(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text(VALID_BODY, encoding="utf-8")
    proc = run_script(SKILL, "validate_sealed_body.py", str(body))
    assert proc.returncode == 0, proc.stderr
    assert "ok" in proc.stdout


@requires("python3")
def test_validate_missing_section(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text("## Goals\n\nonly goals\n", encoding="utf-8")
    proc = run_script(SKILL, "validate_sealed_body.py", str(body))
    assert proc.returncode == 1
    assert "missing required section" in proc.stderr


@requires("python3")
def test_validate_original_ask_not_last(tmp_path: Path) -> None:
    text = VALID_BODY.rstrip() + "\n\n## Extra\nnope\n"
    body = tmp_path / "body.md"
    body.write_text(text, encoding="utf-8")
    proc = run_script(SKILL, "validate_sealed_body.py", str(body))
    assert proc.returncode == 1
    assert "Original Ask must be the last" in proc.stderr


@requires("python3")
def test_validate_missing_rule(tmp_path: Path) -> None:
    text = VALID_BODY.replace("---\n\n## Original Ask", "## Original Ask")
    body = tmp_path / "body.md"
    body.write_text(text, encoding="utf-8")
    proc = run_script(SKILL, "validate_sealed_body.py", str(body))
    assert proc.returncode == 1
    assert "preceded by a ---" in proc.stderr


@requires("python3")
def test_validate_bad_size(tmp_path: Path) -> None:
    text = VALID_BODY.replace("S — one slice", "medium somehow")
    body = tmp_path / "body.md"
    body.write_text(text, encoding="utf-8")
    proc = run_script(SKILL, "validate_sealed_body.py", str(body))
    assert proc.returncode == 1
    assert "## Size must look like" in proc.stderr


@requires("python3")
def test_preflight_pass(tmp_path: Path) -> None:
    fx = _copy_fixture("happy", tmp_path / "happy")
    proc = _ops(fx, "preflight", "--repo", "example/petclinic", "--issue", "10")
    assert proc.returncode == 0, proc.stderr
    assert "preflight ok" in proc.stdout
    assert _mutations(fx) == []


@requires("python3")
def test_preflight_in_progress(tmp_path: Path) -> None:
    fx = _copy_fixture("in-progress", tmp_path / "ip")
    proc = _ops(fx, "preflight", "--repo", "example/petclinic", "--issue", "12")
    assert proc.returncode == 1
    assert "in-progress" in proc.stderr
    assert _mutations(fx) == []


@requires("python3")
def test_preflight_open_pr(tmp_path: Path) -> None:
    fx = _copy_fixture("open-pr", tmp_path / "opr")
    proc = _ops(fx, "preflight", "--repo", "example/petclinic", "--issue", "13")
    assert proc.returncode == 1
    assert "open non-draft PR" in proc.stderr
    assert _mutations(fx) == []


@requires("python3")
def test_preflight_draft_pr_ok(tmp_path: Path) -> None:
    fx = _copy_fixture("draft-pr", tmp_path / "dpr")
    proc = _ops(fx, "preflight", "--repo", "example/petclinic", "--issue", "15")
    assert proc.returncode == 0, proc.stderr


@requires("python3")
def test_seal_and_handoff(tmp_path: Path) -> None:
    fx = _copy_fixture("happy", tmp_path / "happy")
    body = fx / "sealed-body.md"
    assert body.exists()
    seal = _ops(
        fx,
        "seal",
        "--repo",
        "example/petclinic",
        "--issue",
        "10",
        "--body-file",
        str(body),
        "--size",
        "S",
    )
    assert seal.returncode == 0, seal.stderr
    state = json.loads((fx / "state.json").read_text(encoding="utf-8"))
    issue = state["issues"]["10"]
    assert "ready" in [L["name"] for L in issue["labels"]]
    assert "size/S" in [L["name"] for L in issue["labels"]]
    assert "## Goals" in issue["body"]
    assert "## Original Ask" in issue["body"]

    hand = _ops(fx, "handoff", "--repo", "example/petclinic", "--issue", "10")
    assert hand.returncode == 0, hand.stderr
    assert "## Summary" in hand.stdout
    assert "https://github.com/example/petclinic/issues/10" in hand.stdout
    assert "auto-impl eligible" in hand.stdout

    # Body + labels applied in a single issue edit (no partial-seal window)
    issue_edits = [
        e
        for e in _journal(fx)
        if e.get("allowed") and e.get("argv", [])[:2] == ["issue", "edit"]
    ]
    assert len(issue_edits) == 1
    edit_argv = issue_edits[0]["argv"]
    assert "--body-file" in edit_argv
    assert "--add-label" in edit_argv

    # No comments / creates in journal
    for entry in _journal(fx):
        argv = entry["argv"]
        assert argv[:2] not in (["issue", "create"], ["issue", "comment"], ["pr", "create"])


@requires("python3")
def test_seal_rejects_invalid_body(tmp_path: Path) -> None:
    fx = _copy_fixture("happy", tmp_path / "happy")
    bad = tmp_path / "bad.md"
    bad.write_text("## Goals\nonly\n", encoding="utf-8")
    proc = _ops(
        fx,
        "seal",
        "--repo",
        "example/petclinic",
        "--issue",
        "10",
        "--body-file",
        str(bad),
        "--size",
        "S",
    )
    assert proc.returncode == 1
    assert _mutations(fx) == []


@requires("python3")
def test_mock_refuses_forbidden_ops(tmp_path: Path) -> None:
    fx = _copy_fixture("happy", tmp_path / "happy")
    env = _env(fx)
    for args in (
        ["issue", "create", "--title", "x"],
        ["issue", "comment", "10", "--body", "nope"],
        ["pr", "create", "--title", "x"],
        ["issue", "edit", "10", "--repo", "example/petclinic", "--add-assignee", "bob"],
    ):
        proc = run_script(SKILL, "mock_gh.py", *args, env=env)
        assert proc.returncode == 2, (args, proc.stderr)
        assert "refused" in proc.stderr


@requires("python3")
def test_mock_refuses_repo_mismatch_on_edit(tmp_path: Path) -> None:
    fx = _copy_fixture("happy", tmp_path / "happy")
    before = json.loads((fx / "state.json").read_text(encoding="utf-8"))["issues"]["10"][
        "body"
    ]
    body = tmp_path / "body.md"
    body.write_text("should not write", encoding="utf-8")
    proc = run_script(
        SKILL,
        "mock_gh.py",
        "issue",
        "edit",
        "10",
        "--repo",
        "other/repo",
        "--body-file",
        str(body),
        env=_env(fx),
    )
    assert proc.returncode == 2
    assert "repo mismatch" in proc.stderr
    after = json.loads((fx / "state.json").read_text(encoding="utf-8"))
    assert after["issues"]["10"]["body"] == before
    assert _mutations(fx) == []


@requires("python3")
def test_seal_only_named_issue(tmp_path: Path) -> None:
    fx = _copy_fixture("scope-discipline", tmp_path / "scope")
    body = tmp_path / "sealed.md"
    body.write_text(VALID_BODY, encoding="utf-8")
    # Seal #14; #99 body must stay untouched
    before = json.loads((fx / "state.json").read_text(encoding="utf-8"))["issues"]["99"][
        "body"
    ]
    proc = _ops(
        fx,
        "seal",
        "--repo",
        "example/petclinic",
        "--issue",
        "14",
        "--body-file",
        str(body),
        "--size",
        "XS",
    )
    assert proc.returncode == 0, proc.stderr
    after = json.loads((fx / "state.json").read_text(encoding="utf-8"))
    assert after["issues"]["99"]["body"] == before
    assert "ready" in [L["name"] for L in after["issues"]["14"]["labels"]]
