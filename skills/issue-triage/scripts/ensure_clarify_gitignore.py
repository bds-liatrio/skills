#!/usr/bin/env python3
"""Append ``.issue-triage/`` to an existing ``.gitignore`` if missing.

Usage: python3 ensure_clarify_gitignore.py [--repo-root PATH]
Prints: no-gitignore | already-present | appended
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ENTRY = ".issue-triage/"


def _ignored(text: str) -> bool:
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and line.rstrip("/") == ".issue-triage":
            return True
    return False


def ensure(repo_root: Path) -> str:
    path = repo_root / ".gitignore"
    if not path.is_file():
        return "no-gitignore"
    text = path.read_text(encoding="utf-8")
    if _ignored(text):
        return "already-present"
    sep = "" if text.endswith("\n") or text == "" else "\n"
    path.write_text(f"{text}{sep}{ENTRY}\n", encoding="utf-8")
    return "appended"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = p.parse_args(argv)
    root = args.repo_root.resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    try:
        print(ensure(root))
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
