"""Behavior tests for the sdd-linear `install-linear-agent.sh` script.

The script provisions the bundled `linear-project-manager` sub-agent
definition into a target agent-definitions directory. It must be idempotent
(skip an existing agent) and non-destructive unless `--force` is given.
"""

from __future__ import annotations

from pathlib import Path

from conftest import parse_kv, requires, run_script

SKILL = "sdd-linear"
SCRIPT = "install-linear-agent.sh"
AGENT_FILE = "linear-project-manager.md"


@requires("bash")
def test_installs_into_empty_dest(tmp_path: Path) -> None:
    dest = tmp_path / "agents"

    proc = run_script(SKILL, SCRIPT, "--dest", str(dest))

    assert proc.returncode == 0, proc.stderr
    kv = parse_kv(proc.stdout)
    assert kv["status"] == "installed"
    target = dest / AGENT_FILE
    assert target.is_file()
    assert "name: linear-project-manager" in target.read_text(encoding="utf-8")


@requires("bash")
def test_is_idempotent_and_non_destructive(tmp_path: Path) -> None:
    dest = tmp_path / "agents"
    dest.mkdir()
    target = dest / AGENT_FILE
    target.write_text("custom user content\n", encoding="utf-8")

    proc = run_script(SKILL, SCRIPT, "--dest", str(dest))

    assert proc.returncode == 0, proc.stderr
    assert parse_kv(proc.stdout)["status"] == "exists"
    # Existing agent is left untouched.
    assert target.read_text(encoding="utf-8") == "custom user content\n"


@requires("bash")
def test_force_overwrites_existing(tmp_path: Path) -> None:
    dest = tmp_path / "agents"
    dest.mkdir()
    target = dest / AGENT_FILE
    target.write_text("custom user content\n", encoding="utf-8")

    proc = run_script(SKILL, SCRIPT, "--dest", str(dest), "--force")

    assert proc.returncode == 0, proc.stderr
    assert parse_kv(proc.stdout)["status"] == "forced"
    assert "name: linear-project-manager" in target.read_text(encoding="utf-8")
