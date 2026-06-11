"""Behavior tests for the sync-upstream `sync-context` script.

The script consolidates the deterministic detection/classification steps
of the sync-upstream skill: detect VCS, locate the upstream remote and
default branch, fetch it, and classify the integration strategy.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from conftest import GIT_ENV, commit_file, git, init_repo, parse_kv, requires, run_script

SKILL = "sync-upstream"
SCRIPT = "sync-context"


def make_fork_with_upstream(tmp_path: Path) -> tuple[Path, Path]:
    """Create an `upstream` repo and a `fork` clone that tracks it.

    Returns (fork, upstream). The fork has a remote named `upstream`
    pointing at the upstream repo.
    """
    upstream = init_repo(tmp_path / "upstream")
    commit_file(upstream, "README.md", "v1\n", "feat: initial")

    fork = tmp_path / "fork"
    git(tmp_path, "clone", str(upstream), str(fork))
    git(fork, "remote", "add", "upstream", str(upstream))
    return fork, upstream


def test_fast_forward_when_no_fork_only_commits(tmp_path: Path) -> None:
    fork, upstream = make_fork_with_upstream(tmp_path)
    # Upstream advances; fork has no commits of its own.
    commit_file(upstream, "README.md", "v2\n", "feat: upstream advance")

    proc = run_script(SKILL, SCRIPT, cwd=fork)

    assert proc.returncode == 0, proc.stderr
    kv = parse_kv(proc.stdout)
    assert kv["vcs"] == "git"
    assert kv["upstream_remote"] == "present"
    assert kv["default_branch"] == "main"
    assert kv["default_branch_source"] == "git"
    assert kv["fork_only_commits"] == "0"
    assert kv["strategy"] == "fast-forward"


def test_rebase_when_mutable_fork_only_commits(tmp_path: Path) -> None:
    fork, upstream = make_fork_with_upstream(tmp_path)
    # Fork has its own commit on top of upstream; upstream did not move.
    commit_file(fork, "fork.txt", "mine\n", "feat: fork-only work")

    proc = run_script(SKILL, SCRIPT, cwd=fork)

    assert proc.returncode == 0, proc.stderr
    kv = parse_kv(proc.stdout)
    assert kv["fork_only_commits"] == "1"
    assert kv["strategy"] == "rebase"


def test_absent_upstream_reports_absent_and_exits_nonzero(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "solo")
    commit_file(repo, "README.md", "v1\n", "feat: initial")

    proc = run_script(SKILL, SCRIPT, cwd=repo)

    assert proc.returncode == 1
    kv = parse_kv(proc.stdout)
    assert kv["vcs"] == "git"
    assert kv["upstream_remote"] == "absent"


@requires("jj")
def test_detects_jj_vcs(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "jjrepo")
    commit_file(repo, "README.md", "v1\n", "feat: initial")
    subprocess.run(
        ["jj", "git", "init", "--colocate"],
        cwd=str(repo),
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    )

    proc = run_script(SKILL, SCRIPT, cwd=repo)

    kv = parse_kv(proc.stdout)
    assert kv["vcs"] == "jj"
    # No upstream remote configured -> reported absent, nonzero exit.
    assert kv["upstream_remote"] == "absent"
    assert proc.returncode == 1
