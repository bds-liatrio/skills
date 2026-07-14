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
    r"^## Size\s*\n(?P<size>XS|S|M|L|XL)\s+[—\u2013\-]\s+\S",
    re.MULTILINE,
)
H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def _headings_outside_fences(body: str) -> list[tuple[str, int]]:
    """Return (heading_text, char_offset) for ## headings outside fenced code blocks."""
    defenced = FENCE_RE.sub(lambda m: "\n" * m.group().count("\n"), body)
    return [(m.group(1), m.start()) for m in H2_RE.finditer(defenced)]


def validate(body: str) -> list[str]:
    """Return a list of human-readable errors (empty = valid)."""
    errors: list[str] = []
    if not body.strip():
        return ["body is empty"]

    heading_pairs = _headings_outside_fences(body)
    headings = [h for h, _ in heading_pairs]

    for section in REQUIRED_SECTIONS:
        if section not in headings:
            errors.append(f"missing required section: ## {section}")

    # Enforce canonical section ordering
    req_positions = []
    for section in REQUIRED_SECTIONS:
        if section in headings:
            req_positions.append((headings.index(section), section))
    sorted_positions = sorted(req_positions, key=lambda x: x[0])
    expected_order = [s for _, s in sorted_positions]
    canonical_present = [s for s in REQUIRED_SECTIONS if s in headings]
    if expected_order != canonical_present:
        errors.append(
            f"section order must match skeleton: {', '.join(REQUIRED_SECTIONS)}"
        )

    # Enforce non-empty content in each required section (except Original Ask)
    defenced = FENCE_RE.sub(lambda m: "\n" * m.group().count("\n"), body)
    for i, (heading, offset) in enumerate(heading_pairs):
        if heading not in REQUIRED_SECTIONS or heading == "Original Ask":
            continue
        # Content runs from end of heading line to next heading or end
        line_end = defenced.index("\n", offset) if "\n" in defenced[offset:] else len(defenced)
        if i + 1 < len(heading_pairs):
            next_offset = heading_pairs[i + 1][1]
        else:
            next_offset = len(defenced)
        content = defenced[line_end:next_offset].strip()
        # Strip horizontal rules from content check
        content = re.sub(r"^---\s*$", "", content, flags=re.MULTILINE).strip()
        if not content:
            errors.append(f"## {heading} has no content")

    if "Original Ask" in headings:
        if headings[-1] != "Original Ask":
            errors.append("## Original Ask must be the last ## heading")
        # Require --- immediately before ## Original Ask (adjacent, not anywhere earlier)
        oa_match = re.search(r"^## Original Ask\s*$", defenced, re.MULTILINE)
        if oa_match:
            before = defenced[: oa_match.start()].rstrip("\n")
            lines_before = before.split("\n")
            # Walk backwards past blank lines to find the last non-blank line
            last_nonblank = ""
            for line in reversed(lines_before):
                if line.strip():
                    last_nonblank = line.strip()
                    break
            if last_nonblank != "---":
                errors.append("## Original Ask must be immediately preceded by a --- rule")

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
