"""Behavior tests for ``scripts/validate_evals.py``.

Validates skill-creator ``evals/evals.json`` contracts (schema + fixture paths)
through the CLI. Uses throwaway skill trees under ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import run_repo_script


def write_skill(
    root: Path,
    name: str,
    *,
    evals: dict | None = None,
    fixtures: dict[str, str] | None = None,
) -> Path:
    skill = root / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: test\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    if evals is not None:
        evals_dir = skill / "evals"
        evals_dir.mkdir()
        (evals_dir / "evals.json").write_text(
            json.dumps(evals, indent=2) + "\n", encoding="utf-8"
        )
    for rel, content in (fixtures or {}).items():
        path = skill / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return skill


def valid_evals(name: str = "demo") -> dict:
    return {
        "skill_name": name,
        "evals": [
            {
                "id": 1,
                "name": "happy",
                "prompt": "Do the thing.",
                "expected_output": "Thing done.",
                "files": ["evals/fixtures/in.md"],
                "expectations": ["Produces the thing"],
            }
        ],
    }


def validate(repo_root: Path, *args: str):
    return run_repo_script(
        "validate_evals.py",
        *args,
        cwd=repo_root,
        env={"SKILLS_DIR": str(repo_root / "skills")},
    )


def test_passes_valid_evals_tree(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "demo",
        evals=valid_evals(),
        fixtures={"evals/fixtures/in.md": "# input\n"},
    )

    proc = validate(tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert "demo" in proc.stdout


def test_fails_when_fixture_path_missing(tmp_path: Path) -> None:
    write_skill(tmp_path, "demo", evals=valid_evals())

    proc = validate(tmp_path)

    assert proc.returncode != 0
    assert "evals/fixtures/in.md" in proc.stderr or "evals/fixtures/in.md" in proc.stdout


def test_fails_when_skill_name_mismatches_directory(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "demo",
        evals=valid_evals("other"),
        fixtures={"evals/fixtures/in.md": "x\n"},
    )

    proc = validate(tmp_path)

    assert proc.returncode != 0
    assert "skill_name" in (proc.stderr + proc.stdout).lower() or "other" in (
        proc.stderr + proc.stdout
    )


def test_fails_on_duplicate_eval_ids(tmp_path: Path) -> None:
    data = valid_evals()
    data["evals"].append(
        {
            "id": 1,
            "prompt": "Again.",
            "expected_output": "Nope.",
            "expectations": ["x"],
        }
    )
    write_skill(tmp_path, "demo", evals=data)

    proc = validate(tmp_path)

    assert proc.returncode != 0


def test_fails_when_evals_dir_lacks_evals_json(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "demo")
    (skill / "evals").mkdir()

    proc = validate(tmp_path)

    assert proc.returncode != 0


def test_skips_skills_without_evals_dir(tmp_path: Path) -> None:
    write_skill(tmp_path, "no-evals")

    proc = validate(tmp_path)

    assert proc.returncode == 0, proc.stderr


def test_filters_to_named_skill(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "demo",
        evals=valid_evals(),
        fixtures={"evals/fixtures/in.md": "x\n"},
    )
    write_skill(
        tmp_path,
        "broken",
        evals=valid_evals("broken"),  # missing fixture → would fail if scanned
    )

    proc = validate(tmp_path, "demo")

    assert proc.returncode == 0, proc.stderr
    assert "demo" in proc.stdout


def test_list_prints_skills_with_evals_json(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "demo",
        evals=valid_evals(),
        fixtures={"evals/fixtures/in.md": "x\n"},
    )
    write_skill(tmp_path, "no-evals")
    write_skill(
        tmp_path,
        "other",
        evals=valid_evals("other"),
        fixtures={"evals/fixtures/in.md": "x\n"},
    )

    proc = validate(tmp_path, "--list")

    assert proc.returncode == 0, proc.stderr
    names = proc.stdout.splitlines()
    assert names == ["demo", "other"]


def test_list_ids_prints_eval_ids_for_skill(tmp_path: Path) -> None:
    data = valid_evals()
    data["evals"].append(
        {
            "id": 2,
            "name": "second",
            "prompt": "Do more.",
            "expected_output": "More done.",
            "expectations": ["Produces more"],
        }
    )
    write_skill(
        tmp_path,
        "demo",
        evals=data,
        fixtures={"evals/fixtures/in.md": "x\n"},
    )

    proc = validate(tmp_path, "--list-ids", "demo")

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["1", "2"]


def test_list_ids_requires_skill_name(tmp_path: Path) -> None:
    proc = validate(tmp_path, "--list-ids")
    assert proc.returncode != 0
