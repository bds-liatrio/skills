"""Behavior tests for ``scripts/sync_upstream_skills.py``.

The sync script reads a catalog (``upstream-skills.toml``), clones each listed
upstream repo, and vendors the skill folder into ``<repo>/skills/<name>/``,
recording provenance in ``upstream-skills.lock.json``. Tests point ``repo`` at a
local ``file://`` clone so the script never touches the network, and exercise it
through its CLI (files + stdout + exit code out), never its internals.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import make_skill_repo, run_repo_script


def write_catalog(root: Path, *entries: str) -> Path:
    catalog = root / "upstream-skills.toml"
    catalog.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return catalog


def entry(name: str, repo: Path | str, *, path: str | None = None,
          ref: str | None = None) -> str:
    repo_val = repo.as_uri() if isinstance(repo, Path) else repo
    lines = ["[[skill]]", f'name = "{name}"', f'repo = "{repo_val}"']
    if path is not None:
        lines.append(f'path = "{path}"')
    if ref is not None:
        lines.append(f'ref = "{ref}"')
    return "\n".join(lines)


def sync(repo_root: Path, *args: str):
    return run_repo_script(
        "sync_upstream_skills.py", *args, cwd=repo_root,
        env={"CATALOG": str(repo_root / "upstream-skills.toml")},
    )


def test_vendors_skill_folder_verbatim(tmp_path: Path) -> None:
    upstream, _sha = make_skill_repo(tmp_path / "upstream", "agent-browser")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    write_catalog(repo_root, entry("agent-browser", upstream, path="skills/agent-browser"))

    proc = sync(repo_root)

    assert proc.returncode == 0, proc.stderr
    vendored = repo_root / "skills" / "agent-browser" / "SKILL.md"
    assert vendored.is_file(), f"expected vendored SKILL.md; stdout={proc.stdout}"
    assert "name: agent-browser" in vendored.read_text(encoding="utf-8")


def test_copies_upstream_license_into_vendored_folder(tmp_path: Path) -> None:
    upstream, _sha = make_skill_repo(
        tmp_path / "upstream", "agent-browser", license_text="Apache License 2.0\n"
    )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    write_catalog(repo_root, entry("agent-browser", upstream, path="skills/agent-browser"))

    proc = sync(repo_root)

    assert proc.returncode == 0, proc.stderr
    license_file = repo_root / "skills" / "agent-browser" / "LICENSE"
    assert license_file.is_file(), "expected upstream LICENSE copied into vendored folder"
    assert "Apache" in license_file.read_text(encoding="utf-8")


def read_lock(repo_root: Path) -> dict:
    return json.loads((repo_root / "upstream-skills.lock.json").read_text(encoding="utf-8"))


def test_records_provenance_in_lockfile(tmp_path: Path) -> None:
    upstream, sha = make_skill_repo(tmp_path / "upstream", "agent-browser")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    write_catalog(repo_root, entry("agent-browser", upstream, path="skills/agent-browser"))

    proc = sync(repo_root)

    assert proc.returncode == 0, proc.stderr
    rec = read_lock(repo_root)["skills"]["agent-browser"]
    assert rec["commit"] == sha
    assert rec["path"] == "skills/agent-browser"
    assert rec["repo"] == upstream.as_uri()
    assert isinstance(rec["synced_at"], str) and rec["synced_at"]
    assert isinstance(rec.get("license"), str) and rec["license"]


def test_auto_detects_skill_folder_when_path_omitted(tmp_path: Path) -> None:
    upstream, _sha = make_skill_repo(tmp_path / "upstream", "agent-browser")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    write_catalog(repo_root, entry("agent-browser", upstream))  # no path

    proc = sync(repo_root)

    assert proc.returncode == 0, proc.stderr
    assert (repo_root / "skills" / "agent-browser" / "SKILL.md").is_file()
    assert read_lock(repo_root)["skills"]["agent-browser"]["path"] == "skills/agent-browser"


def test_fails_when_frontmatter_name_mismatches_catalog(tmp_path: Path) -> None:
    upstream, _sha = make_skill_repo(tmp_path / "upstream", "real-name")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    write_catalog(repo_root, entry("agent-browser", upstream, path="skills/real-name"))

    proc = sync(repo_root)

    assert proc.returncode != 0
    assert "name" in (proc.stderr + proc.stdout).lower()
    assert not (repo_root / "skills" / "agent-browser").exists(), "must not vendor on mismatch"


def test_second_run_with_unchanged_upstream_is_a_noop(tmp_path: Path) -> None:
    upstream, _sha = make_skill_repo(tmp_path / "upstream", "agent-browser")
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    write_catalog(repo_root, entry("agent-browser", upstream, path="skills/agent-browser"))

    assert sync(repo_root).returncode == 0
    lock_before = (repo_root / "upstream-skills.lock.json").read_text(encoding="utf-8")
    skill_before = (repo_root / "skills" / "agent-browser" / "SKILL.md").read_text(encoding="utf-8")

    assert sync(repo_root).returncode == 0

    assert (repo_root / "upstream-skills.lock.json").read_text(encoding="utf-8") == lock_before
    assert (repo_root / "skills" / "agent-browser" / "SKILL.md").read_text(encoding="utf-8") == skill_before


def test_rejects_non_permissive_license(tmp_path: Path) -> None:
    gpl = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n"
    upstream, _sha = make_skill_repo(
        tmp_path / "upstream", "copyleft-skill", license_text=gpl
    )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    write_catalog(repo_root, entry("copyleft-skill", upstream, path="skills/copyleft-skill"))

    proc = sync(repo_root)

    assert proc.returncode != 0
    assert "license" in (proc.stderr + proc.stdout).lower()
    assert not (repo_root / "skills" / "copyleft-skill").exists(), "must not vendor non-permissive"
