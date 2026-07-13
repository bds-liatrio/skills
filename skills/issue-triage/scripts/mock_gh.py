#!/usr/bin/env python3
"""Fixture-backed ``gh`` stub for offline issue-triage tests and evals.

Set ``ISSUE_TRIAGE_GH`` to this script (e.g. ``python3 …/mock_gh.py``) and
``ISSUE_TRIAGE_FIXTURE_DIR`` to a directory containing ``state.json``. Every
invocation appends to ``gh-journal.json``. Only allowlisted ``gh`` shapes
succeed; everything else exits 2.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

EDIT_FLAGS = {"--repo", "--body-file", "--add-label", "--remove-label"}


def fixture_dir() -> Path:
    raw = os.environ.get("ISSUE_TRIAGE_FIXTURE_DIR")
    if not raw:
        print("ISSUE_TRIAGE_FIXTURE_DIR is required", file=sys.stderr)
        raise SystemExit(2)
    return Path(raw)


def state_path(root: Path) -> Path:
    return root / "state.json"


def journal_path(root: Path) -> Path:
    return root / "gh-journal.json"


def load_state(root: Path) -> dict[str, Any]:
    path = state_path(root)
    if not path.exists():
        print(f"missing fixture state: {path}", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(root: Path, state: dict[str, Any]) -> None:
    state_path(root).write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def append_journal(root: Path, entry: dict[str, Any]) -> None:
    path = journal_path(root)
    entries: list[dict[str, Any]] = []
    if path.exists():
        entries = json.loads(path.read_text(encoding="utf-8"))
    entries.append(entry)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


def refuse(argv: list[str], reason: str) -> int:
    append_journal(
        fixture_dir(),
        {"argv": argv, "allowed": False, "reason": reason, "mutated": False},
    )
    print(f"mock_gh refused: {reason}", file=sys.stderr)
    return 2


def label_names(issue: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in issue.get("labels") or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return names


def set_labels(issue: dict[str, Any], names: list[str]) -> None:
    issue["labels"] = [{"name": n} for n in sorted(set(names))]


def parse_repo(argv: list[str]) -> str | None:
    if "--repo" in argv:
        i = argv.index("--repo")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


def parse_json_fields(argv: list[str]) -> list[str] | None:
    if "--json" not in argv:
        return None
    i = argv.index("--json")
    if i + 1 >= len(argv):
        return []
    return [f.strip() for f in argv[i + 1].split(",") if f.strip()]


def check_forbidden(argv: list[str]) -> str | None:
    if argv[:2] == ["issue", "create"] or argv[:2] == ["pr", "create"]:
        return "creating issues/PRs is forbidden"
    if argv[:2] == ["issue", "comment"]:
        return "issue comments are forbidden"
    if argv[:2] == ["pr", "edit"]:
        return "editing PRs is forbidden"
    if any(
        flag in argv
        for flag in (
            "--add-assignee",
            "--remove-assignee",
            "--add-project",
            "--remove-project",
            "--milestone",
        )
    ):
        return "assignee/project/milestone mutation forbidden"
    return None


def handle(argv: list[str]) -> int:
    root = fixture_dir()
    if not argv:
        return refuse(argv, "empty argv")

    reason = check_forbidden(argv)
    if reason:
        return refuse(argv, reason)

    state = load_state(root)
    mutated = False
    result_stdout = ""

    if argv[:2] == ["issue", "view"]:
        try:
            number = int(argv[2])
        except (IndexError, ValueError):
            return refuse(argv, "issue view requires issue number")
        repo = parse_repo(argv)
        issue = (state.get("issues") or {}).get(str(number))
        if not issue:
            return refuse(argv, f"unknown issue {number}")
        if repo and state.get("repo") and repo != state["repo"]:
            return refuse(argv, f"repo mismatch: {repo}")
        fields = parse_json_fields(argv) or [
            "number",
            "title",
            "body",
            "labels",
            "url",
            "assignees",
            "projectItems",
        ]
        payload: dict[str, Any] = {f: issue.get(f) for f in fields}
        if "labels" in payload:
            payload["labels"] = [{"name": n} for n in label_names(issue)]
        if "assignees" in payload and payload["assignees"] is None:
            payload["assignees"] = []
        if "projectItems" in payload and payload["projectItems"] is None:
            payload["projectItems"] = []
        result_stdout = json.dumps(payload)

    elif argv[:2] == ["label", "list"]:
        names = list(state.get("labels_available") or [])
        result_stdout = json.dumps([{"name": n} for n in names])

    elif argv[:2] == ["label", "create"]:
        try:
            name = argv[2]
        except IndexError:
            return refuse(argv, "label create requires name")
        available = list(state.get("labels_available") or [])
        if name not in available:
            available.append(name)
            state["labels_available"] = available
            mutated = True
            save_state(root, state)

    elif argv[:2] == ["issue", "edit"]:
        try:
            number = int(argv[2])
        except (IndexError, ValueError):
            return refuse(argv, "issue edit requires issue number")
        issue = (state.get("issues") or {}).get(str(number))
        if not issue:
            return refuse(argv, f"unknown issue {number}")

        # Validate flags before mutating
        i = 3
        while i < len(argv):
            tok = argv[i]
            if not tok.startswith("--"):
                return refuse(argv, f"unexpected issue edit arg: {tok}")
            if tok not in EDIT_FLAGS:
                return refuse(argv, f"forbidden issue edit flag: {tok}")
            if i + 1 >= len(argv):
                return refuse(argv, f"missing value for {tok}")
            i += 2

        if "--body-file" in argv:
            bf = Path(argv[argv.index("--body-file") + 1])
            issue["body"] = bf.read_text(encoding="utf-8")
            mutated = True

        names = label_names(issue)
        if "--add-label" in argv:
            for lab in argv[argv.index("--add-label") + 1].split(","):
                lab = lab.strip()
                if lab and lab not in names:
                    names.append(lab)
            mutated = True
        if "--remove-label" in argv:
            remove = {
                x.strip()
                for x in argv[argv.index("--remove-label") + 1].split(",")
                if x.strip()
            }
            names = [n for n in names if n not in remove]
            mutated = True

        set_labels(issue, names)
        state.setdefault("issues", {})[str(number)] = issue
        if mutated:
            save_state(root, state)

    elif argv[:2] == ["pr", "list"]:
        fields = parse_json_fields(argv) or [
            "number",
            "isDraft",
            "state",
            "closingIssuesReferences",
        ]
        prs = [{f: pr.get(f) for f in fields} for pr in state.get("pull_requests") or []]
        result_stdout = json.dumps(prs)

    else:
        return refuse(argv, f"unrecognized command: {' '.join(argv)}")

    append_journal(
        root,
        {"argv": argv, "allowed": True, "reason": None, "mutated": mutated},
    )
    if result_stdout:
        print(result_stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "gh":
        args = args[1:]
    return handle(args)


if __name__ == "__main__":
    raise SystemExit(main())
