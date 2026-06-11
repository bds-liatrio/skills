"""Behavior tests for the jj-case-insensitive-clone-fix `diagnose` script
and the shared dedup logic in `lib.sh` (also used by `jj-clone`).
"""

from __future__ import annotations

from pathlib import Path

from conftest import git, init_repo, run_script

SKILL = "jj-case-insensitive-clone-fix"


def test_stdin_detects_case_only_collision() -> None:
    proc = run_script(
        SKILL, "diagnose", "--stdin",
        stdin="MergeMasterToDevelop\nMergeMastertoDevelop\nmain\n",
    )

    assert proc.returncode == 1
    assert "MergeMasterToDevelop" in proc.stdout
    assert "MergeMastertoDevelop" in proc.stdout


def test_stdin_no_collision_exits_zero() -> None:
    proc = run_script(
        SKILL, "diagnose", "--stdin",
        stdin="main\ndevelop\nfeature/x\n",
    )

    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_url_mode_clean_remote(tmp_path: Path) -> None:
    upstream = init_repo(tmp_path / "upstream")
    (upstream / "README.md").write_text("v1\n", encoding="utf-8")
    git(upstream, "add", "README.md")
    git(upstream, "commit", "-m", "feat: initial")
    git(upstream, "branch", "develop")

    proc = run_script(SKILL, "diagnose", str(upstream))

    assert proc.returncode == 0, proc.stderr


def test_url_mode_detects_packed_collision(tmp_path: Path) -> None:
    # Case-colliding refs cannot exist as loose files on a case-insensitive
    # filesystem, but they can coexist inside packed-refs -- which is exactly
    # the on-remote situation that breaks `jj git clone`. Inject them there so
    # the test is reliable on macOS APFS and Linux alike.
    upstream = init_repo(tmp_path / "upstream")
    (upstream / "README.md").write_text("v1\n", encoding="utf-8")
    git(upstream, "add", "README.md")
    git(upstream, "commit", "-m", "feat: initial")
    git(upstream, "pack-refs", "--all")
    head = git(upstream, "rev-parse", "HEAD").stdout.strip()

    packed = upstream / ".git" / "packed-refs"
    with packed.open("a", encoding="utf-8") as fh:
        fh.write(f"{head} refs/heads/Release\n")
        fh.write(f"{head} refs/heads/release\n")

    proc = run_script(SKILL, "diagnose", str(upstream))

    assert proc.returncode == 1, proc.stdout
    assert "Release" in proc.stdout
    assert "release" in proc.stdout


def test_jj_clone_help_still_works_after_refactor() -> None:
    # jj-clone now sources lib.sh; make sure that wiring didn't break startup.
    proc = run_script(SKILL, "jj-clone", "--help")

    assert proc.returncode == 0
    assert "Usage: jj-clone" in proc.stdout
