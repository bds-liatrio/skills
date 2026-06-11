"""Behavior tests for the agentsmd-generator `repo-inventory` script.

The script gathers the deterministic Phase 1 inventory: language/package
manager signals, automation runners and their targets, CI files, env-file
hints, and a best-effort directory tree.
"""

from __future__ import annotations

from pathlib import Path

from conftest import git, init_repo, parse_kv, requires, run_script

SKILL = "agentsmd-generator"
SCRIPT = "repo-inventory"


def split_csv(value: str) -> set[str]:
    return {item for item in value.split(",") if item}


def test_detects_python_and_package_manager(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (repo / "uv.lock").write_text("", encoding="utf-8")

    proc = run_script(SKILL, SCRIPT, cwd=repo)

    assert proc.returncode == 0, proc.stderr
    kv = parse_kv(proc.stdout)
    assert "python" in split_csv(kv.get("languages", ""))
    assert "uv" in split_csv(kv.get("package_managers", ""))


def test_detects_javascript_typescript_and_npm(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    (repo / "package.json").write_text("{}\n", encoding="utf-8")
    (repo / "tsconfig.json").write_text("{}\n", encoding="utf-8")
    (repo / "package-lock.json").write_text("{}\n", encoding="utf-8")

    kv = parse_kv(run_script(SKILL, SCRIPT, cwd=repo).stdout)

    langs = split_csv(kv.get("languages", ""))
    assert {"javascript", "typescript"} <= langs
    assert "npm" in split_csv(kv.get("package_managers", ""))


def test_extracts_makefile_help_targets(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    (repo / "Makefile").write_text(
        "build: ## Build the project\n\techo build\n"
        "test: ## Run tests\n\techo test\n",
        encoding="utf-8",
    )

    kv = parse_kv(run_script(SKILL, SCRIPT, cwd=repo).stdout)

    assert "make" in split_csv(kv.get("runners", ""))
    assert {"build", "test"} <= split_csv(kv.get("make_targets", ""))


def test_detects_ci_and_env_files(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (repo / ".env.example").write_text("KEY=\n", encoding="utf-8")
    (repo / "config").mkdir()

    kv = parse_kv(run_script(SKILL, SCRIPT, cwd=repo).stdout)

    assert ".github/workflows/ci.yml" in split_csv(kv.get("ci_files", ""))
    env_files = split_csv(kv.get("env_files", ""))
    assert ".env.example" in env_files
    assert "config/" in env_files


def test_emits_tree_section(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    (repo / "README.md").write_text("# hi\n", encoding="utf-8")

    out = run_script(SKILL, SCRIPT, cwd=repo).stdout

    assert "[tree]" in out
    assert "README.md" in out
