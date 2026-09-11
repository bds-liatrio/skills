"""Offline tests for pr-feedback-qa session_log.py."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_script

SKILL = "pr-feedback-qa"


def _run(repo: Path, *args: str, stdin: str | None = None):
    return run_script(
        SKILL,
        "session_log.py",
        *args,
        cwd=repo,
        stdin=stdin,
    )


def _init(repo: Path, slug: str = "pr-55") -> Path:
    (repo / ".gitignore").write_text("# keep\n", encoding="utf-8")
    proc = _run(
        repo,
        "init",
        "--repo-root",
        str(repo),
        "--slug",
        slug,
        "--source-type",
        "file",
        "--source",
        "review.md",
    )
    assert proc.returncode == 0, proc.stderr
    path = Path(proc.stdout.strip())
    assert path.is_file()
    return path


def _findings() -> list[dict]:
    return [
        {
            "id": 1,
            "title": "Test DB wipe",
            "summary": "Tests can wipe Analytics DB.",
            "sources": [{"kind": "file", "ref": "review.md", "author": None}],
            "fix_options": ["Separate schema", "Other (describe)"],
        },
        {
            "id": 2,
            "title": "BOM",
            "summary": "UTF-8 BOM drops metrics.",
            "sources": [{"kind": "file", "ref": "review.md", "author": None}],
            "fix_options": ["utf-8-sig", "Other (describe)"],
        },
    ]


def test_ensure_gitignore_appends(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    proc = _run(repo, "ensure-gitignore", "--repo-root", str(repo))
    assert proc.returncode == 0
    assert proc.stdout.strip() == "appended"
    text = (repo / ".gitignore").read_text(encoding="utf-8")
    assert ".scratch/" in text
    proc2 = _run(repo, "ensure-gitignore", "--repo-root", str(repo))
    assert proc2.stdout.strip() == "already-present"


def test_init_resume_roundtrip(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = _init(repo)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["slug"] == "pr-55"
    assert data["source"]["type"] == "file"
    assert data["status"] == "in_progress"

    resume = _run(repo, "resume", "--repo-root", str(repo), "--slug", "pr-55")
    assert resume.returncode == 0, resume.stderr
    assert json.loads(resume.stdout)["slug"] == "pr-55"


def test_record_summary_and_issue(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init(repo)
    findings_file = tmp_path / "findings.json"
    findings_file.write_text(json.dumps(_findings()), encoding="utf-8")
    setf = _run(
        repo,
        "set-findings",
        "--repo-root",
        str(repo),
        "--slug",
        "pr-55",
        "--findings-file",
        str(findings_file),
    )
    assert setf.returncode == 0, setf.stderr

    r1 = _run(
        repo,
        "record",
        "--repo-root",
        str(repo),
        "--slug",
        "pr-55",
        stdin=json.dumps(
            {
                "finding_id": 1,
                "disposition": "address",
                "fix_choice": "A1",
                "notes": "schema + localhost",
            }
        ),
    )
    assert r1.returncode == 0, r1.stderr

    cl = _run(
        repo,
        "clarify",
        "--repo-root",
        str(repo),
        "--slug",
        "pr-55",
        "--finding-id",
        "2",
        "--question",
        "Why BOM?",
        "--answer",
        "utf-8 keeps the mark",
    )
    assert cl.returncode == 0, cl.stderr

    r2 = _run(
        repo,
        "record",
        "--repo-root",
        str(repo),
        "--slug",
        "pr-55",
        stdin=json.dumps(
            {
                "finding_id": 2,
                "disposition": "github_issue",
                "fix_choice": "A1",
                "labels": ["bug"],
            }
        ),
    )
    assert r2.returncode == 0, r2.stderr

    sm = _run(repo, "summary", "--repo-root", str(repo), "--slug", "pr-55")
    assert sm.returncode == 0, sm.stderr
    assert "| 1 | Address |" in sm.stdout
    assert "| 2 | GitHub Issue |" in sm.stdout
    assert "**Queued GitHub issues:** 1" in sm.stdout

    session = json.loads(
        _run(repo, "resume", "--repo-root", str(repo), "--slug", "pr-55").stdout
    )
    assert session["status"] == "summary_ready"
    assert session["summary"]["markdown"]
    assert len(session["clarifications"]) == 1

    issue = _run(
        repo,
        "add-issue",
        "--repo-root",
        str(repo),
        "--slug",
        "pr-55",
        "--finding-id",
        "2",
        "--url",
        "https://github.com/example/repo/issues/9",
        "--number",
        "9",
        "--title",
        "BOM follow-up",
    )
    assert issue.returncode == 0, issue.stderr
    session2 = json.loads(
        _run(repo, "resume", "--repo-root", str(repo), "--slug", "pr-55").stdout
    )
    assert session2["status"] == "issues_created"
    assert session2["github_issues"][0]["number"] == 9


def test_malformed_session_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    bad = repo / ".scratch" / "pr-feedback-qa" / "bad.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not-json", encoding="utf-8")
    proc = _run(repo, "resume", "--repo-root", str(repo), "--slug", "bad")
    assert proc.returncode == 1
    assert "malformed JSON" in proc.stderr


def test_init_refuses_existing_without_force(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init(repo)
    again = _run(
        repo,
        "init",
        "--repo-root",
        str(repo),
        "--slug",
        "pr-55",
        "--source-type",
        "pr",
        "--source",
        "owner/repo#1",
    )
    assert again.returncode == 1
    assert "session exists" in again.stderr
