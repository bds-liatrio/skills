#!/usr/bin/env python3
"""Validate a sealed Issue body against the issue-triage skeleton.

Exit 0 on success. Exit 1 with messages on stderr when the body fails the
schema. Used by ``issue_ops seal`` and by offline tests/evals.

Usage:
  validate_sealed_body.py <body.md>
  validate_sealed_body.py --stdin
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = (
    "Goals",
    "Non-goals",
    "Functional Requirements",
    "Constraints",
    "Assumptions",
    "Size",
    "User Acceptance Criteria",
    "Testable / Verifiable",
    "Original Ask",
)

SIZE_RE = re.compile(
    r"^## Size\s*\n(?P<size>XS|S|M|L|XL)\s+[—\-]\s+\S",
    re.MULTILINE,
)
H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def validate(body: str) -> list[str]:
    """Return a list of human-readable errors (empty = valid)."""
    errors: list[str] = []
    if not body.strip():
        return ["body is empty"]

    headings = H2_RE.findall(body)
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            errors.append(f"missing required section: ## {section}")

    if "Original Ask" in headings:
        if headings[-1] != "Original Ask":
            errors.append("## Original Ask must be the last ## heading")
        # Require a horizontal rule before Original Ask
        oa_match = re.search(r"^## Original Ask\s*$", body, re.MULTILINE)
        if oa_match:
            before = body[: oa_match.start()]
            if not re.search(r"^---\s*$", before, re.MULTILINE):
                errors.append("## Original Ask must be preceded by a --- rule")

    if "Size" in headings and not SIZE_RE.search(body):
        errors.append(
            "## Size must look like: <XS|S|M|L|XL> — <one-line rationale>"
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Path to sealed body markdown")
    parser.add_argument(
        "--stdin", action="store_true", help="Read body from stdin"
    )
    args = parser.parse_args(argv)

    if args.stdin:
        body = sys.stdin.read()
    elif args.path:
        body = Path(args.path).read_text(encoding="utf-8")
    else:
        parser.error("provide a path or --stdin")

    errors = validate(body)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
