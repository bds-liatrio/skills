"""Behavior tests for the research_codebase `spec_metadata.sh` script.

The script prints the deterministic frontmatter metadata block (date,
researcher, git_commit, branch, repository, last_updated*) for a research
document. It is self-contained and bundled with the skill, replacing the
previously-external `hack/spec_metadata.sh`.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import commit_file, git, init_repo, run_script

SKILL = "research_codebase"
SCRIPT = "spec_metadata.sh"


def parse_yaml_kv(stdout: str) -> dict[str, str]:
    """Parse ``key: value`` frontmatter lines (avoids YAML date coercion)."""
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        if ": " in line:
            key, _, value = line.partition(": ")
            result[key.strip()] = value.strip()
        elif line.endswith(":"):
            result[line[:-1].strip()] = ""
    return result


def test_reports_commit_branch_and_researcher(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    git(repo, "config", "user.name", "Test User")
    commit_file(repo, "README.md", "v1\n", "feat: initial")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()

    proc = run_script(SKILL, SCRIPT, cwd=repo)

    assert proc.returncode == 0, proc.stderr
    kv = parse_yaml_kv(proc.stdout)
    assert kv["git_commit"] == head
    assert kv["branch"] == "main"
    assert kv["researcher"] == "Test User"
    assert kv["last_updated_by"] == "Test User"


def test_date_fields_are_iso_formatted(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    commit_file(repo, "README.md", "v1\n", "feat: initial")

    kv = parse_yaml_kv(run_script(SKILL, SCRIPT, cwd=repo).stdout)

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}", kv["date"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", kv["last_updated"])


def test_repository_from_origin_url(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    commit_file(repo, "README.md", "v1\n", "feat: initial")
    git(repo, "remote", "add", "origin", "git@github.com:acme/widgets.git")

    kv = parse_yaml_kv(run_script(SKILL, SCRIPT, cwd=repo).stdout)

    assert kv["repository"] == "widgets"


def test_detached_head_reported_honestly(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "proj")
    commit_file(repo, "a.txt", "1\n", "feat: a")
    commit_file(repo, "b.txt", "2\n", "feat: b")
    first = git(repo, "rev-parse", "HEAD~1").stdout.strip()
    git(repo, "checkout", "--detach", first)

    kv = parse_yaml_kv(run_script(SKILL, SCRIPT, cwd=repo).stdout)

    # Detached HEAD should not be reported as the literal branch "HEAD".
    assert kv["branch"] != "HEAD"
    assert kv["git_commit"] == first
