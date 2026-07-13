#!/usr/bin/env python3
"""Sole GitHub surface for the issue-triage skill.

Subcommands:
  view          Read the named issue (JSON on stdout)
  preflight     Fail closed if in-progress or open non-draft linked PR
  ensure-labels Bootstrap ready + size/* taxonomy
  seal          Validate body, overwrite body, apply ready + size/*
  handoff       Print Summary + Issue URL (no writes)

All ``gh`` calls go through ``ISSUE_TRIAGE_GH`` (default: ``gh``). For offline
tests/evals, point that at ``scripts/mock_gh.py`` and set
``ISSUE_TRIAGE_FIXTURE_DIR``.

Agents must not invent ad-hoc mutating ``gh`` calls — use this CLI only.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_sealed_body.py"
TAXONOMY = ("ready", "size/XS", "size/S", "size/M", "size/L", "size/XL")
VALID_SIZES = ("XS", "S", "M", "L", "XL")


def gh_cmd() -> list[str]:
    raw = os.environ.get("ISSUE_TRIAGE_GH", "gh")
    # Allow "python3 /path/to/mock_gh.py" style values
    return shlex.split(raw)


def run_gh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    cmd = [*gh_cmd(), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        sys.stderr.write(proc.stderr or proc.stdout or f"gh failed: {cmd}\n")
        raise SystemExit(proc.returncode or 1)
    return proc


def label_names(issue: dict) -> list[str]:
    names = []
    for item in issue.get("labels") or []:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return names


def cmd_view(repo: str, issue: int) -> int:
    proc = run_gh(
        "issue",
        "view",
        str(issue),
        "--repo",
        repo,
        "--json",
        "number,title,body,labels,url,assignees,projectItems",
    )
    print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    return 0


def cmd_preflight(repo: str, issue: int) -> int:
    proc = run_gh(
        "issue",
        "view",
        str(issue),
        "--repo",
        repo,
        "--json",
        "number,title,body,labels,url",
    )
    data = json.loads(proc.stdout)
    names = {n.lower() for n in label_names(data)}
    if "in-progress" in names:
        print(
            f"preflight blocked: issue #{issue} has label 'in-progress'",
            file=sys.stderr,
        )
        return 1

    pr_proc = run_gh(
        "pr",
        "list",
        "--repo",
        repo,
        "--json",
        "number,isDraft,state,closingIssuesReferences",
    )
    prs = json.loads(pr_proc.stdout or "[]")
    blockers = []
    for pr in prs:
        state = str(pr.get("state") or "").upper()
        if state not in {"OPEN", "OPENED"}:
            continue
        if pr.get("isDraft") is True:
            continue
        refs = pr.get("closingIssuesReferences") or []
        for ref in refs:
            num = ref.get("number") if isinstance(ref, dict) else ref
            if int(num) == issue:
                blockers.append(pr.get("number"))
                break
    if blockers:
        print(
            f"preflight blocked: open non-draft PR(s) linked to "
            f"#{issue}: {', '.join(f'#{n}' for n in blockers)}",
            file=sys.stderr,
        )
        return 1

    print("preflight ok")
    return 0


def cmd_ensure_labels(repo: str) -> int:
    proc = run_gh("label", "list", "--repo", repo, "--json", "name")
    existing = {item["name"] for item in json.loads(proc.stdout or "[]")}
    for name in TAXONOMY:
        if name not in existing:
            run_gh("label", "create", name, "--repo", repo)
            print(f"created label: {name}")
        else:
            print(f"label exists: {name}")
    return 0


def cmd_seal(repo: str, issue: int, body_file: Path, size: str) -> int:
    if size not in VALID_SIZES:
        print(f"invalid size: {size} (want {VALID_SIZES})", file=sys.stderr)
        return 1
    if not body_file.is_file():
        print(f"body file not found: {body_file}", file=sys.stderr)
        return 1

    # Validate sealed body before any mutation
    val = subprocess.run(
        [sys.executable, str(VALIDATOR), str(body_file)],
        capture_output=True,
        text=True,
    )
    if val.returncode != 0:
        sys.stderr.write(val.stderr)
        return 1

    # Confirm issue exists / is the named one
    view = run_gh(
        "issue",
        "view",
        str(issue),
        "--repo",
        repo,
        "--json",
        "number,labels",
    )
    data = json.loads(view.stdout)
    if int(data["number"]) != issue:
        print("issue number mismatch", file=sys.stderr)
        return 1

    cmd_ensure_labels(repo)

    run_gh(
        "issue",
        "edit",
        str(issue),
        "--repo",
        repo,
        "--body-file",
        str(body_file),
    )

    # Remove conflicting size/* then add ready + size
    current = label_names(data)
    conflicting = [n for n in current if n.startswith("size/") and n != f"size/{size}"]
    if conflicting:
        run_gh(
            "issue",
            "edit",
            str(issue),
            "--repo",
            repo,
            "--remove-label",
            ",".join(conflicting),
        )

    run_gh(
        "issue",
        "edit",
        str(issue),
        "--repo",
        repo,
        "--add-label",
        f"ready,size/{size}",
    )
    print(f"sealed #{issue} with ready,size/{size}")
    return 0


def cmd_handoff(repo: str, issue: int) -> int:
    proc = run_gh(
        "issue",
        "view",
        str(issue),
        "--repo",
        repo,
        "--json",
        "number,title,labels,url",
    )
    data = json.loads(proc.stdout)
    names = label_names(data)
    size_labels = [n for n in names if n.startswith("size/")]
    size = size_labels[0].removeprefix("size/") if size_labels else "?"
    ready = "ready" in names
    auto = ready and size in ("XS", "S")
    eligibility = "auto-impl eligible" if auto else "human-steered"
    print("## Summary")
    print(f"- Issue: #{data['number']} — {data['title']}")
    print(f"- Size: {size}")
    print(f"- Labels: {', '.join(names) if names else '(none)'}")
    print(f"- Eligibility: {eligibility}")
    print()
    print(f"Issue URL: {data['url']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_view = sub.add_parser("view", help="Read issue JSON")
    p_view.add_argument("--repo", required=True)
    p_view.add_argument("--issue", type=int, required=True)

    p_pre = sub.add_parser("preflight", help="Gate: in-progress / open PR")
    p_pre.add_argument("--repo", required=True)
    p_pre.add_argument("--issue", type=int, required=True)

    p_lab = sub.add_parser("ensure-labels", help="Bootstrap taxonomy labels")
    p_lab.add_argument("--repo", required=True)

    p_seal = sub.add_parser("seal", help="Write sealed body + ready/size labels")
    p_seal.add_argument("--repo", required=True)
    p_seal.add_argument("--issue", type=int, required=True)
    p_seal.add_argument("--body-file", type=Path, required=True)
    p_seal.add_argument("--size", required=True, choices=VALID_SIZES)

    p_hand = sub.add_parser("handoff", help="Print Summary + Issue URL")
    p_hand.add_argument("--repo", required=True)
    p_hand.add_argument("--issue", type=int, required=True)

    args = parser.parse_args(argv)

    if args.command == "view":
        return cmd_view(args.repo, args.issue)
    if args.command == "preflight":
        return cmd_preflight(args.repo, args.issue)
    if args.command == "ensure-labels":
        return cmd_ensure_labels(args.repo)
    if args.command == "seal":
        return cmd_seal(args.repo, args.issue, args.body_file, args.size)
    if args.command == "handoff":
        return cmd_handoff(args.repo, args.issue)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
