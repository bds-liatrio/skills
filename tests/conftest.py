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
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
SCRIPTS_DIR = ROOT / "scripts"

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
               stdin: str | None = None,
               env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run ``skills/<skill>/scripts/<script>`` as a subprocess."""
    script_path = SKILLS_DIR / skill / "scripts" / script
    run_env = {**GIT_ENV}
    if env:
        run_env.update({k: str(v) for k, v in env.items()})
    # Prefer the current interpreter for *.py so uv-managed deps apply.
    cmd: list[str]
    if script_path.suffix == ".py":
        cmd = [sys.executable, str(script_path), *args]
    else:
        cmd = [str(script_path), *args]
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=run_env,
        input=stdin,
        capture_output=True,
        text=True,
    )


def run_repo_script(script: str, *args: str, cwd: Path | None = None,
                    stdin: str | None = None,
                    env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a top-level ``scripts/<script>`` via the current interpreter.

    Uses ``sys.executable`` so the script runs under the same (uv-managed)
    environment as the test suite, giving it access to dev dependencies like
    PyYAML. ``env`` entries are layered on top of the isolated git env.
    """
    script_path = SCRIPTS_DIR / script
    run_env = {**GIT_ENV}
    if env:
        run_env.update({k: str(v) for k, v in env.items()})
    return subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=str(cwd) if cwd else None,
        env=run_env,
        input=stdin,
        capture_output=True,
        text=True,
    )


def make_skill_repo(path: Path, name: str, *, description: str = "A test skill.",
                    license_text: str | None = "MIT License\n",
                    skill_subdir: str | None = None,
                    extra_files: dict[str, str] | None = None) -> tuple[Path, str]:
    """Create a throwaway git repo containing one skill folder.

    Returns ``(repo_path, commit_sha)``. Tests clone this via a ``file://`` URL
    so the sync script never touches the network. ``skill_subdir`` defaults to
    ``skills/<name>`` to mirror the common upstream layout.
    """
    repo = init_repo(path)
    rel = skill_subdir if skill_subdir is not None else f"skills/{name}"
    skill_dir = repo / rel
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nBody.\n",
        encoding="utf-8",
    )
    if license_text is not None:
        (repo / "LICENSE").write_text(license_text, encoding="utf-8")
    for file_rel, content in (extra_files or {}).items():
        target = repo / file_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", f"add {name}")
    sha = git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, sha


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
