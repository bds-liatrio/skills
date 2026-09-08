#!/usr/bin/env python3
"""Validate skill-creator ``evals/evals.json`` contracts under ``skills/``.

Checks schema shape (skill_name, eval ids, prompt/expected_output/expectations)
and that every ``files`` entry exists relative to the skill root. Skills without
an ``evals/`` directory are skipped. Optional positional args filter to named
skills. Exit 0 on success; non-zero with diagnostics on stderr otherwise.

Override the skills root with ``SKILLS_DIR`` (tests).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def skills_dir() -> Path:
    override = os.environ.get("SKILLS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "skills"


def discover(root: Path, names: list[str] | None) -> list[Path]:
    if names:
        return [root / n for n in names]
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))


def require_str(value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: must be a non-empty string")


def validate_evals_json(skill_dir: Path, data: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{skill_dir.name}: evals.json root must be an object"]

    skill_name = data.get("skill_name")
    require_str(skill_name, f"{skill_dir.name}: skill_name", errors)
    if isinstance(skill_name, str) and skill_name.strip() and skill_name != skill_dir.name:
        errors.append(
            f"{skill_dir.name}: skill_name {skill_name!r} does not match directory name"
        )

    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append(f"{skill_dir.name}: evals must be a non-empty array")
        return errors

    seen_ids: set[int] = set()
    for i, item in enumerate(evals):
        prefix = f"{skill_dir.name}: evals[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        eid = item.get("id")
        if not isinstance(eid, int):
            errors.append(f"{prefix}: id must be an integer")
        elif eid in seen_ids:
            errors.append(f"{prefix}: duplicate id {eid}")
        else:
            seen_ids.add(eid)

        if "name" in item:
            require_str(item.get("name"), f"{prefix}: name", errors)
        require_str(item.get("prompt"), f"{prefix}: prompt", errors)
        require_str(item.get("expected_output"), f"{prefix}: expected_output", errors)

        files = item.get("files", [])
        if files is None:
            files = []
        if not isinstance(files, list):
            errors.append(f"{prefix}: files must be an array")
        else:
            for j, rel in enumerate(files):
                if not isinstance(rel, str) or not rel.strip():
                    errors.append(f"{prefix}: files[{j}] must be a non-empty string")
                    continue
                path = skill_dir / rel
                if not path.is_file():
                    errors.append(f"{prefix}: missing file {rel}")

        expectations = item.get("expectations", [])
        if expectations is None:
            expectations = []
        if not isinstance(expectations, list):
            errors.append(f"{prefix}: expectations must be an array")
        else:
            for j, exp in enumerate(expectations):
                if not isinstance(exp, str) or not exp.strip():
                    errors.append(f"{prefix}: expectations[{j}] must be a non-empty string")

    return errors


def validate_skill(skill_dir: Path) -> list[str]:
    if not skill_dir.is_dir():
        return [f"{skill_dir.name}: skill directory not found"]

    evals_dir = skill_dir / "evals"
    if not evals_dir.is_dir():
        return []

    evals_path = evals_dir / "evals.json"
    if not evals_path.is_file():
        return [f"{skill_dir.name}: evals/ exists but evals/evals.json is missing"]

    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{skill_dir.name}: evals.json is not valid JSON: {exc}"]

    return validate_evals_json(skill_dir, data)


def list_eval_skills(root: Path) -> list[str]:
    names: list[str] = []
    for skill_dir in discover(root, None):
        if (skill_dir / "evals" / "evals.json").is_file():
            names.append(skill_dir.name)
    return names


def list_eval_ids(skill_dir: Path) -> list[int]:
    path = skill_dir / "evals" / "evals.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    evals = data.get("evals")
    if not isinstance(evals, list):
        return []
    ids: list[int] = []
    for item in evals:
        if isinstance(item, dict) and isinstance(item.get("id"), int):
            ids.append(item["id"])
    return ids


def main(argv: list[str]) -> int:
    root = skills_dir()
    if not root.is_dir():
        print(f"skills directory not found: {root}", file=sys.stderr)
        return 2

    args = argv[1:]
    if args == ["--list"]:
        for name in list_eval_skills(root):
            print(name)
        return 0

    if args and args[0] == "--list-ids":
        if len(args) != 2:
            print("usage: validate_evals.py --list-ids <skill>", file=sys.stderr)
            return 2
        skill_dir = root / args[1]
        evals_path = skill_dir / "evals" / "evals.json"
        if not evals_path.is_file():
            print(f"{args[1]}: evals/evals.json not found", file=sys.stderr)
            return 1
        for eid in list_eval_ids(skill_dir):
            print(eid)
        return 0

    names = args or None
    skills = discover(root, names)
    if names and not skills:
        print("no skills specified", file=sys.stderr)
        return 2

    all_errors: list[str] = []
    checked = 0
    for skill_dir in skills:
        errors = validate_skill(skill_dir)
        if not (skill_dir / "evals").is_dir() and not names:
            continue
        if (skill_dir / "evals").is_dir() or names:
            if (skill_dir / "evals").is_dir():
                checked += 1
            all_errors.extend(errors)
            if not errors and (skill_dir / "evals").is_dir():
                print(f"ok  {skill_dir.name}")

    if names:
        for name in names:
            skill_dir = root / name
            if not (skill_dir / "evals").is_dir() and skill_dir.is_dir():
                # Named skill with no evals/: treat as soft skip with note
                print(f"skip {name} (no evals/)", file=sys.stderr)

    if all_errors:
        for err in all_errors:
            print(err, file=sys.stderr)
        return 1

    if checked == 0 and not names:
        print("ok  (no skills with evals/)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
