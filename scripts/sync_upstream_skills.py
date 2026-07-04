#!/usr/bin/env python3
"""Vendor upstream skills declared in ``upstream-skills.toml`` into this repo.

Reads the catalog, clones each listed upstream repo, copies its skill folder
into ``<repo>/skills/<name>/`` so the skill is installable via
``npx skills add SystemFiles/skills --skill <name>``, and records provenance in
``upstream-skills.lock.json``.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

LOCK_VERSION = 1


def resolve_repo_url(repo: str) -> str:
    """Map a catalog ``repo`` value to a git-cloneable URL.

    Full URLs (including ``file://``) and scp-style git URLs pass through;
    the ``owner/repo`` shorthand expands to a GitHub HTTPS URL.
    """
    if "://" in repo or repo.startswith("git@"):
        return repo
    return f"https://github.com/{repo}"


def load_catalog(catalog_path: Path) -> list[dict]:
    data = tomllib.loads(catalog_path.read_text(encoding="utf-8"))
    return data.get("skill", [])


def clone(url: str, ref: str | None, dest: Path) -> None:
    args = ["git", "clone", "--depth", "1"]
    if ref:
        args += ["--branch", ref]
    args += [url, str(dest)]
    subprocess.run(args, check=True, capture_output=True, text=True)


def git_head(checkout: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return proc.stdout.strip()


def copy_attribution(checkout: Path, dest: Path) -> None:
    """Copy top-level LICENSE/NOTICE/COPYING files into the vendored folder.

    Retaining these preserves attribution when republishing third-party skills.
    A file the skill folder already ships is left untouched.
    """
    for root_file in sorted(checkout.iterdir()):
        if not root_file.is_file():
            continue
        if not root_file.name.upper().startswith(("LICENSE", "NOTICE", "COPYING")):
            continue
        target = dest / root_file.name
        if not target.exists():
            shutil.copy2(root_file, target)


def detect_license(dest: Path) -> str:
    """Best-effort SPDX id from a vendored license file; ``unknown`` if unsure."""
    for candidate in sorted(dest.iterdir()):
        if candidate.is_file() and candidate.name.upper().startswith(("LICENSE", "COPYING")):
            return spdx_from_text(candidate.read_text(encoding="utf-8", errors="ignore"))
    return "unknown"


def spdx_from_text(text: str) -> str:
    lowered = text.lower()
    if "apache license" in lowered and "2.0" in lowered:
        return "Apache-2.0"
    if "mit license" in lowered or "permission is hereby granted, free of charge" in lowered:
        return "MIT"
    if "redistribution and use" in lowered:
        return "BSD"
    if "mozilla public license" in lowered:
        return "MPL-2.0"
    if "gnu affero general public license" in lowered:
        return "AGPL"
    if "gnu general public license" in lowered:
        return "GPL"
    return "unknown"


# Copyleft licenses this repo will not republish through skills.sh.
NON_PERMISSIVE_LICENSES = {"GPL", "AGPL", "LGPL"}


def ensure_permissive(name: str, license_id: str) -> None:
    if license_id in NON_PERMISSIVE_LICENSES:
        raise SystemExit(
            f"sync: '{name}' upstream license {license_id} is not permissive; "
            f"refusing to vendor. Remove it from the catalog."
        )


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read_frontmatter_name(skill_md: Path) -> str | None:
    """Return the ``name`` from a SKILL.md YAML frontmatter block, or None."""
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None
    for line in match.group(1).splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def find_skill_path(checkout: Path, name: str) -> str:
    """Locate the skill folder within a checkout when the catalog omits ``path``.

    Prefers ``skills/<name>/``, then a root-level ``SKILL.md``, then a unique
    ``SKILL.md`` anywhere. Raises if the folder is ambiguous.
    """
    if (checkout / "skills" / name / "SKILL.md").is_file():
        return f"skills/{name}"
    if (checkout / "SKILL.md").is_file():
        return "."
    matches = [p for p in checkout.rglob("SKILL.md") if ".git" not in p.parts]
    if len(matches) == 1:
        return matches[0].parent.relative_to(checkout).as_posix()
    raise SystemExit(
        f"sync: cannot locate skill folder for '{name}'; set 'path' in the catalog"
    )


def dir_fingerprint(root: Path) -> dict[str, bytes]:
    """Map of relative path -> file bytes, for content-equality comparisons."""
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def vendor_skill(entry: dict, repo_root: Path, prev_lock: dict[str, dict]) -> dict:
    name = entry["name"]
    catalog_repo = entry["repo"]
    url = resolve_repo_url(catalog_repo)
    dest = repo_root / "skills" / name
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        checkout = workdir / "checkout"
        clone(url, entry.get("ref"), checkout)
        commit = git_head(checkout)
        path = entry.get("path") or find_skill_path(checkout, name)
        fm_name = read_frontmatter_name(checkout / path / "SKILL.md")
        if fm_name != name:
            raise SystemExit(
                f"sync: '{name}' upstream frontmatter name is {fm_name!r}; "
                f"it must match the catalog name '{name}'"
            )
        stage = workdir / "stage"
        shutil.copytree(checkout / path, stage, ignore=shutil.ignore_patterns(".git"))
        copy_attribution(checkout, stage)
        license_id = detect_license(stage)
        ensure_permissive(name, license_id)

        prev = prev_lock.get(name)
        already_current = (
            dest.exists()
            and prev is not None
            and prev.get("commit") == commit
            and dir_fingerprint(stage) == dir_fingerprint(dest)
        )
        if already_current:
            return prev

        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(stage, dest)
    return {
        "repo": catalog_repo,
        "source_url": url,
        "path": path,
        "ref": entry.get("ref"),
        "commit": commit,
        "license": license_id,
        "synced_at": now_iso(),
    }


def read_existing_lock(repo_root: Path) -> dict[str, dict]:
    path = repo_root / "upstream-skills.lock.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8")).get("skills", {})
    return {}


def write_lock(repo_root: Path, records: dict[str, dict]) -> None:
    lock = {"version": LOCK_VERSION, "skills": dict(sorted(records.items()))}
    path = repo_root / "upstream-skills.lock.json"
    path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    catalog_path = Path(os.environ.get("CATALOG") or (Path.cwd() / "upstream-skills.toml"))
    repo_root = catalog_path.parent
    prev_lock = read_existing_lock(repo_root)
    records: dict[str, dict] = {}
    for entry in load_catalog(catalog_path):
        records[entry["name"]] = vendor_skill(entry, repo_root, prev_lock)
    write_lock(repo_root, records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
