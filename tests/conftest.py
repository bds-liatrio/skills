"""Shared helpers for skill-script tests.

These tests exercise bundled skill scripts through their command-line
interface (arguments in, stdout / exit code out), running them as
subprocesses against throwaway git repositories. They deliberately avoid
asserting on script internals so they survive script refactors.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"

# Isolate git from the developer's global/system config so tests are
# deterministic regardless of the host environment.
GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "Test User",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test User",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    # Keep credential / pager prompts from ever blocking a subprocess.
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_PAGER": "cat",
}


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        env=GIT_ENV,
        check=True,
        capture_output=True,
        text=True,
    )


def init_repo(path: Path, initial_branch: str = "main") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", f"--initial-branch={initial_branch}")
    return path


def commit_file(repo: Path, name: str, content: str, message: str) -> None:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message)


def run_script(skill: str, script: str, *args: str, cwd: Path | None = None,
               stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run ``skills/<skill>/scripts/<script>`` as a subprocess."""
    script_path = SKILLS_DIR / skill / "scripts" / script
    return subprocess.run(
        [str(script_path), *args],
        cwd=str(cwd) if cwd else None,
        env=GIT_ENV,
        input=stdin,
        capture_output=True,
        text=True,
    )


def parse_kv(stdout: str) -> dict[str, str]:
    """Parse ``key=value`` lines emitted by a script into a dict."""
    result: dict[str, str] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def requires(tool: str):
    """Skip marker for tests that need an optional CLI tool on PATH."""
    return pytest.mark.skipif(
        shutil.which(tool) is None, reason=f"{tool} not installed"
    )
