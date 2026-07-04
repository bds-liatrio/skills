"""Behavior tests for ``scripts/capture_project_skills.py``.

The capture script reconciles skills a project installed (its ``skills-lock.json``,
enriched from the global ``~/.agents/.skill-lock.json``) into this repo's
``upstream-skills.toml`` catalog. Tests point every lockfile/catalog at temp
files via env overrides and drive the script through its CLI.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from conftest import run_repo_script


def write_json(path: Path, obj: dict) -> Path:
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def project_lock(path: Path, skills: dict) -> Path:
    return write_json(path, {"version": 1, "skills": skills})


def global_lock(path: Path, skills: dict) -> Path:
    return write_json(path, {"version": 3, "skills": skills})


def make_catalog(path: Path, body: str = "") -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def read_entries(catalog: Path) -> list[dict]:
    return tomllib.loads(catalog.read_text(encoding="utf-8")).get("skill", [])


def capture(*args: str, plock: Path | None = None, glock: Path | None = None,
            catalog: Path | None = None, stdin: str | None = None,
            cwd: Path | None = None):
    env: dict[str, str] = {}
    if plock is not None:
        env["PROJECT_LOCK"] = str(plock)
    if glock is not None:
        env["SKILL_LOCK"] = str(glock)
    if catalog is not None:
        env["CATALOG"] = str(catalog)
    return run_repo_script("capture_project_skills.py", *args, cwd=cwd, stdin=stdin, env=env)


def test_appends_new_github_skill_from_project_lock(tmp_path: Path) -> None:
    plock = project_lock(tmp_path / "skills-lock.json", {
        "agent-browser": {"source": "vercel-labs/agent-browser",
                          "sourceType": "github", "computedHash": "x"},
    })
    glock = global_lock(tmp_path / "global.json", {
        "agent-browser": {"source": "vercel-labs/agent-browser", "sourceType": "github",
                          "sourceUrl": "https://github.com/vercel-labs/agent-browser",
                          "skillPath": "skills/agent-browser", "skillFolderHash": "y"},
    })
    catalog = make_catalog(tmp_path / "upstream-skills.toml")

    proc = capture("--yes", plock=plock, glock=glock, catalog=catalog)

    assert proc.returncode == 0, proc.stderr
    entries = read_entries(catalog)
    assert any(e["name"] == "agent-browser" and e["repo"] == "vercel-labs/agent-browser"
               for e in entries), f"catalog={catalog.read_text()}"


def test_enriches_path_from_global_lock_or_leaves_unset(tmp_path: Path) -> None:
    plock = project_lock(tmp_path / "skills-lock.json", {
        "with-path": {"source": "o/with-path", "sourceType": "github", "computedHash": "a"},
        "no-path": {"source": "o/no-path", "sourceType": "github", "computedHash": "b"},
    })
    glock = global_lock(tmp_path / "global.json", {
        "with-path": {"source": "o/with-path", "sourceType": "github",
                     "sourceUrl": "https://github.com/o/with-path",
                     "skillPath": "skills/with-path", "skillFolderHash": "y"},
    })
    catalog = make_catalog(tmp_path / "upstream-skills.toml")

    proc = capture("--yes", plock=plock, glock=glock, catalog=catalog)

    assert proc.returncode == 0, proc.stderr
    by_name = {e["name"]: e for e in read_entries(catalog)}
    assert by_name["with-path"]["path"] == "skills/with-path"
    assert "path" not in by_name["no-path"]


def test_dry_run_reports_without_writing(tmp_path: Path) -> None:
    plock = project_lock(tmp_path / "skills-lock.json", {
        "agent-browser": {"source": "vercel-labs/agent-browser",
                          "sourceType": "github", "computedHash": "x"},
    })
    glock = global_lock(tmp_path / "global.json", {})
    catalog = make_catalog(tmp_path / "upstream-skills.toml")

    proc = capture("--dry-run", plock=plock, glock=glock, catalog=catalog)

    assert proc.returncode == 0, proc.stderr
    assert catalog.read_text(encoding="utf-8") == "", "dry-run must not write"
    assert read_entries(catalog) == []
    assert "agent-browser" in proc.stdout


def test_skips_skills_already_declared(tmp_path: Path) -> None:
    plock = project_lock(tmp_path / "skills-lock.json", {
        "agent-browser": {"source": "vercel-labs/agent-browser",
                          "sourceType": "github", "computedHash": "x"},
    })
    glock = global_lock(tmp_path / "global.json", {})
    catalog = make_catalog(
        tmp_path / "upstream-skills.toml",
        '[[skill]]\nname = "agent-browser"\nrepo = "vercel-labs/agent-browser"\n',
    )

    proc = capture("--yes", plock=plock, glock=glock, catalog=catalog)

    assert proc.returncode == 0, proc.stderr
    assert [e["name"] for e in read_entries(catalog)] == ["agent-browser"]
    assert "already declared" in proc.stdout


def test_local_source_skipped_and_reported_as_promote_candidate(tmp_path: Path) -> None:
    plock = project_lock(tmp_path / "skills-lock.json", {
        "my-local": {"source": "../my-local-skills", "sourceType": "local", "computedHash": "z"},
    })
    glock = global_lock(tmp_path / "global.json", {})
    catalog = make_catalog(tmp_path / "upstream-skills.toml")

    proc = capture("--yes", plock=plock, glock=glock, catalog=catalog)

    assert proc.returncode == 0, proc.stderr
    assert read_entries(catalog) == [], "local skills are out of scope for the catalog"
    assert "my-local" in proc.stdout
    assert "promote" in proc.stdout.lower()


def test_all_mode_reads_only_global_lock(tmp_path: Path) -> None:
    plock = project_lock(tmp_path / "skills-lock.json", {
        "project-only": {"source": "o/project-only", "sourceType": "github", "computedHash": "p"},
    })
    glock = global_lock(tmp_path / "global.json", {
        "global-skill": {"source": "o/global-skill", "sourceType": "github",
                        "sourceUrl": "https://github.com/o/global-skill",
                        "skillPath": "skills/global-skill", "skillFolderHash": "g"},
    })
    catalog = make_catalog(tmp_path / "upstream-skills.toml")

    proc = capture("--all", "--yes", plock=plock, glock=glock, catalog=catalog)

    assert proc.returncode == 0, proc.stderr
    assert {e["name"] for e in read_entries(catalog)} == {"global-skill"}


def test_interactive_yes_then_no(tmp_path: Path) -> None:
    plock = project_lock(tmp_path / "skills-lock.json", {
        "skill-a": {"source": "o/skill-a", "sourceType": "github", "computedHash": "a"},
        "skill-b": {"source": "o/skill-b", "sourceType": "github", "computedHash": "b"},
    })
    glock = global_lock(tmp_path / "global.json", {})
    catalog = make_catalog(tmp_path / "upstream-skills.toml")

    proc = capture(plock=plock, glock=glock, catalog=catalog, stdin="y\nn\n")

    assert proc.returncode == 0, proc.stderr
    assert {e["name"] for e in read_entries(catalog)} == {"skill-a"}


def test_interactive_all_accepts_remaining(tmp_path: Path) -> None:
    plock = project_lock(tmp_path / "skills-lock.json", {
        "skill-a": {"source": "o/skill-a", "sourceType": "github", "computedHash": "a"},
        "skill-b": {"source": "o/skill-b", "sourceType": "github", "computedHash": "b"},
        "skill-c": {"source": "o/skill-c", "sourceType": "github", "computedHash": "c"},
    })
    glock = global_lock(tmp_path / "global.json", {})
    catalog = make_catalog(tmp_path / "upstream-skills.toml")

    proc = capture(plock=plock, glock=glock, catalog=catalog, stdin="a\n")

    assert proc.returncode == 0, proc.stderr
    assert {e["name"] for e in read_entries(catalog)} == {"skill-a", "skill-b", "skill-c"}
