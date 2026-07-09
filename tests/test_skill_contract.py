"""Static contract test for the skills.sh catalog.

Validates that every ``skills/<name>/SKILL.md`` has a YAML frontmatter block with
non-empty ``name`` and ``description`` fields, that skill names are unique, and
that each skill directory name matches its frontmatter ``name``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"

# Skills expected to be present in this repository.
EXPECTED_SKILLS = {
    "agentsmd-generator",
    "jj-case-insensitive-clone-fix",
    "lavish-safe",
    "research_codebase",
    "sdd-linear",
    "sync-upstream",
    "taskfile-automation",
    "work-breakdown",
}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def skill_md_paths() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match, f"{path}: missing YAML frontmatter block (expected leading '---')"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict), f"{path}: frontmatter is not a YAML mapping"
    return data


def test_skills_directory_exists() -> None:
    assert SKILLS_DIR.is_dir(), "skills/ directory must exist"


def test_expected_skills_present() -> None:
    found = {p.parent.name for p in skill_md_paths()}
    missing = EXPECTED_SKILLS - found
    assert not missing, f"missing expected skills: {sorted(missing)}"


@pytest.mark.parametrize("skill_md", skill_md_paths(), ids=lambda p: p.parent.name)
def test_frontmatter_has_name_and_description(skill_md: Path) -> None:
    data = parse_frontmatter(skill_md)
    name = data.get("name")
    description = data.get("description")
    assert isinstance(name, str) and name.strip(), f"{skill_md}: 'name' is missing or empty"
    assert isinstance(description, str) and description.strip(), (
        f"{skill_md}: 'description' is missing or empty"
    )


@pytest.mark.parametrize("skill_md", skill_md_paths(), ids=lambda p: p.parent.name)
def test_directory_name_matches_frontmatter_name(skill_md: Path) -> None:
    data = parse_frontmatter(skill_md)
    assert data.get("name") == skill_md.parent.name, (
        f"{skill_md}: frontmatter name '{data.get('name')}' "
        f"does not match directory '{skill_md.parent.name}'"
    )


def test_skill_names_are_unique() -> None:
    names = [parse_frontmatter(p).get("name") for p in skill_md_paths()]
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, f"duplicate skill names: {dupes}"
