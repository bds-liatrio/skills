#!/usr/bin/env python3
"""Reconcile a project's installed skills into ``upstream-skills.toml``.

A project-scoped analog of the chezmoi ``sync-skills-registry.sh`` reconcile:
read the skills a project installed (its ``skills-lock.json``), enrich their
provenance from the global ``~/.agents/.skill-lock.json``, and append any not
already declared to this repo's catalog. From there the CI sync vendors them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path


def load_lock_skills(path: str | None) -> dict[str, dict]:
    if path and Path(path).is_file():
        return json.loads(Path(path).read_text(encoding="utf-8")).get("skills", {})
    return {}


def declared_names(catalog: Path) -> set[str]:
    if catalog.is_file():
        data = tomllib.loads(catalog.read_text(encoding="utf-8"))
        return {e.get("name") for e in data.get("skill", [])}
    return set()


def shareable_repo(source: str, source_type: str, source_url: str | None) -> str | None:
    """Return an ``owner/repo`` or URL to pin, or None for local/unsourced skills."""
    if source_type in {"local", "path", "file"}:
        return None
    if "/" in source and "://" not in source and not source.startswith((".", "/")):
        return source
    url = (source_url or source).removesuffix(".git")
    return url or None


def format_entry(name: str, repo: str, path: str | None) -> str:
    lines = ["", "[[skill]]", f'name = "{name}"', f'repo = "{repo}"']
    if path:
        lines.append(f'path = "{path}"')
    return "\n".join(lines) + "\n"


def prompt_confirm(display: str) -> str:
    """Ask whether to add one entry; returns 'y', 'n', 'a', or 'q'. EOF -> quit."""
    while True:
        sys.stdout.write(f'Add "{display}"? [y]es/[n]o/[a]ll/[q]uit (default no): ')
        sys.stdout.flush()
        line = sys.stdin.readline()
        if line == "":
            return "q"
        answer = line.strip().lower()
        if answer in ("y", "yes"):
            return "y"
        if answer in ("", "n", "no"):
            return "n"
        if answer in ("a", "all"):
            return "a"
        if answer in ("q", "quit"):
            return "q"
        print("Please answer y, n, a, or q.")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", help="path to a project containing skills-lock.json")
    parser.add_argument("-y", "--yes", action="store_true", help="add all candidates without prompts")
    parser.add_argument("-n", "--dry-run", action="store_true", help="report only; write nothing")
    parser.add_argument("--all", dest="all_", action="store_true",
                        help="capture every skill in the global lock (machine-wide)")
    return parser.parse_args(argv)


def resolve_source_skills(args: argparse.Namespace,
                          global_skills: dict[str, dict]) -> dict[str, dict]:
    """Machine-wide (--all) reads the global lock; otherwise the project lock."""
    if args.all_:
        return global_skills
    project_lock_path = os.environ.get("PROJECT_LOCK")
    if not project_lock_path and args.project:
        project_lock_path = str(Path(args.project) / "skills-lock.json")
    return load_lock_skills(project_lock_path)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    catalog = Path(os.environ.get("CATALOG") or (Path.cwd() / "upstream-skills.toml"))
    global_skills = load_lock_skills(
        os.environ.get("SKILL_LOCK") or str(Path.home() / ".agents" / ".skill-lock.json")
    )
    source_skills = resolve_source_skills(args, global_skills)
    existing = declared_names(catalog)

    added = 0
    accept_all = args.yes
    for name in sorted(source_skills):
        entry = source_skills[name]
        source_type = entry.get("sourceType", "")
        repo = shareable_repo(entry.get("source", ""), source_type, entry.get("sourceUrl"))
        if repo is None:
            print(f"capture: skip '{name}' — {source_type or 'unsourced'} install has no "
                  f"shareable git source; candidate for the promote-to-authored flow "
                  f"(out of scope here).")
            continue
        if name in existing:
            print(f"capture: skip '{name}' — already declared in the catalog.")
            continue

        path = (global_skills.get(name) or {}).get("skillPath")
        display = f"{repo} (name={name}" + (f", path={path})" if path else ")")

        if args.dry_run:
            print(f"capture: would add: {display}")
            added += 1
            continue
        if not accept_all:
            reply = prompt_confirm(display)
            if reply == "q":
                print("capture: quit — skipping remaining candidates.")
                break
            if reply == "n":
                print(f"capture: declined: {display}")
                continue
            if reply == "a":
                accept_all = True

        with catalog.open("a", encoding="utf-8") as handle:
            handle.write(format_entry(name, repo, path))
        existing.add(name)
        print(f"capture: added: {display}")
        added += 1

    verb = "would add" if args.dry_run else "added"
    print(f"capture: {added} {verb}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
