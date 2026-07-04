"""Consistency guard for vendored upstream skills.

Keeps three artifacts in agreement: ``upstream-skills.toml`` (intent),
``upstream-skills.lock.json`` (resolved provenance), and the committed
``skills/<name>/`` folders. Also asserts each vendored skill retains an upstream
license file so attribution is preserved when republishing via skills.sh.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "upstream-skills.toml"
LOCK = ROOT / "upstream-skills.lock.json"
SKILLS_DIR = ROOT / "skills"


def catalog_names() -> set[str]:
    if not CATALOG.is_file():
        return set()
    data = tomllib.loads(CATALOG.read_text(encoding="utf-8"))
    return {e["name"] for e in data.get("skill", [])}


def lock_skills() -> dict[str, dict]:
    if not LOCK.is_file():
        return {}
    return json.loads(LOCK.read_text(encoding="utf-8")).get("skills", {})


def has_license(folder: Path) -> bool:
    return any(
        child.is_file() and child.name.upper().startswith(("LICENSE", "NOTICE", "COPYING"))
        for child in folder.iterdir()
    )


def test_catalog_and_lock_agree() -> None:
    assert catalog_names() == set(lock_skills()), (
        "upstream-skills.toml and upstream-skills.lock.json disagree; "
        "run `make sync-upstream-skills`"
    )


@pytest.mark.parametrize("name", sorted(lock_skills()), ids=lambda n: n)
def test_vendored_skill_present_with_license_and_provenance(name: str) -> None:
    folder = SKILLS_DIR / name
    assert (folder / "SKILL.md").is_file(), f"{name}: vendored SKILL.md missing"
    assert has_license(folder), f"{name}: vendored skill must retain an upstream license file"
    record = lock_skills()[name]
    for field in ("repo", "commit", "license", "synced_at"):
        assert record.get(field), f"{name}: lock entry missing '{field}'"
