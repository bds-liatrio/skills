"""Static contract test for the skills.sh catalog.

Validates that every ``skills/<name>/SKILL.md`` has a YAML frontmatter block with
non-empty ``name`` and ``description`` fields, that skill names are unique, that
each skill directory name matches its frontmatter ``name``, and that authored
skills address their bundled files through the ``$SKILL_DIR`` anchor.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
LOCK = ROOT / "upstream-skills.lock.json"

# Authored skills that must remain present (vendored ones are covered by
# tests/test_upstream_catalog.py).
EXPECTED_SKILLS = {
    "agentsmd-generator",
    "issue-triage",
    "bro",
    "jj-case-insensitive-clone-fix",
    "lavish-safe",
    "pr-feedback-qa",
    "research_codebase",
    "sdd-linear",
    "sdd-qa",
    "sync-upstream",
    "taskfile-automation",
    "visual-explain",
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


def test_agent_plugin_manifest_present() -> None:
    """Root plugin.json marks this catalog as an Agent Plugin for Cursor."""
    manifest_path = ROOT / "plugin.json"
    assert manifest_path.is_file(), "plugin.json must exist at repo root"
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "plugin.json must be a JSON object"
    assert data.get("$schema") == (
        "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    ), "plugin.json must declare the Agent Plugins 1.0.0 schema"
    name = data.get("name")
    description = data.get("description")
    assert isinstance(name, str) and name.strip(), "plugin.json: 'name' required"
    assert isinstance(description, str) and description.strip(), (
        "plugin.json: 'description' required"
    )


# --- Bundled-path convention -------------------------------------------------
#
# Installed skills run from an install directory that is *not* the subject
# repo's cwd, so a bundled helper can only be addressed by absolute path. The
# catalog convention is a model-filled ``SKILL_DIR`` assigned inline in the same
# command as the invocation (shell state does not persist across tool calls):
#
#     SKILL_DIR=<absolute path to this skill's directory>
#     python3 "$SKILL_DIR/scripts/thing.py" --flag
#
# The two patterns this rejects both silently break once installed:
# ``{{skill_dir}}`` (nothing substitutes it) and a bare ``scripts/thing``
# (resolves against the subject repo).

SHELL_LANGS = {"bash", "sh", "shell", "zsh", "console"}
FENCE_RE = re.compile(r"^(?P<indent>[ \t]*)```(?P<lang>[\w-]*)\n(?P<body>.*?)^(?P=indent)```",
                      re.DOTALL | re.MULTILINE)
TEMPLATE_SKILL_DIR_RE = re.compile(r"\{\{\s*skill_dir\s*\}\}", re.IGNORECASE)
BARE_SCRIPTS_RE = re.compile(r"(?<![\w/$\"'.-])(?:\./)?scripts/")
SKILL_DIR_USE_RE = re.compile(r"\$\{?SKILL_DIR\b")
SKILL_DIR_SET_RE = re.compile(r"^\s*SKILL_DIR=", re.MULTILINE)
SKILL_DIR_REF_RE = re.compile(r"\$\{?SKILL_DIR\}?/([\w./-]*)")


def vendored_names() -> set[str]:
    if not LOCK.is_file():
        return set()
    return set(json.loads(LOCK.read_text(encoding="utf-8")).get("skills", {}))


def authored_markdown() -> list[Path]:
    """Every markdown file under an authored (non-vendored) skill."""
    vendored = vendored_names()
    return sorted(
        p
        for p in SKILLS_DIR.glob("*/**/*.md")
        if p.relative_to(SKILLS_DIR).parts[0] not in vendored
    )


def shell_blocks(text: str) -> list[str]:
    return [
        m.group("body")
        for m in FENCE_RE.finditer(text)
        if m.group("lang").lower() in SHELL_LANGS
    ]


def md_id(path: Path) -> str:
    return str(path.relative_to(SKILLS_DIR))


@pytest.mark.parametrize("md", authored_markdown(), ids=md_id)
def test_no_template_skill_dir_placeholder(md: Path) -> None:
    """``{{skill_dir}}`` is not part of any SKILL.md contract; nothing expands it."""
    text = md.read_text(encoding="utf-8")
    assert not TEMPLATE_SKILL_DIR_RE.search(text), (
        f"{md_id(md)}: uses the '{{{{skill_dir}}}}' placeholder, which nothing substitutes. "
        "Use an inline 'SKILL_DIR=<absolute path to this skill's directory>' "
        'assignment plus "$SKILL_DIR/..." instead.'
    )


@pytest.mark.parametrize("md", authored_markdown(), ids=md_id)
def test_shell_blocks_do_not_invoke_bare_relative_scripts(md: Path) -> None:
    """Bare ``scripts/...`` resolves against the subject repo, not the install dir."""
    for block in shell_blocks(md.read_text(encoding="utf-8")):
        offender = BARE_SCRIPTS_RE.search(block)
        assert offender is None, (
            f"{md_id(md)}: shell block references a bare relative "
            f"'{block[offender.start():].splitlines()[0].strip()}'. "
            'Anchor bundled helpers as "$SKILL_DIR/scripts/..." with an inline '
            "SKILL_DIR= assignment in the same command."
        )


@pytest.mark.parametrize("md", authored_markdown(), ids=md_id)
def test_shell_blocks_using_skill_dir_also_set_it(md: Path) -> None:
    """Shell state does not persist across tool calls, so each block must set it."""
    for block in shell_blocks(md.read_text(encoding="utf-8")):
        if SKILL_DIR_USE_RE.search(block) and not SKILL_DIR_SET_RE.search(block):
            pytest.fail(
                f"{md_id(md)}: shell block uses $SKILL_DIR without assigning it in the "
                "same block. Prefix the block with "
                "'SKILL_DIR=<absolute path to this skill's directory>'."
            )


@pytest.mark.parametrize("md", authored_markdown(), ids=md_id)
def test_skill_dir_references_resolve_to_bundled_files(md: Path) -> None:
    """Every ``$SKILL_DIR/<path>`` must name something the skill actually ships."""
    skill_dir = SKILLS_DIR / md.relative_to(SKILLS_DIR).parts[0]
    for rel in SKILL_DIR_REF_RE.findall(md.read_text(encoding="utf-8")):
        if not rel or ".." in rel:
            continue
        assert (skill_dir / rel).exists(), (
            f"{md_id(md)}: references '$SKILL_DIR/{rel}', which the skill does not bundle"
        )
