#!/usr/bin/env python3
"""Stream human-readable text from ``agent --output-format stream-json``.

Reads NDJSON from stdin. Prints assistant text as it arrives. On a final
``result`` event, exits 0 on success and 1 on error. Unknown lines pass through.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    saw_result = False
    exit_code = 0
    saw_partial_assistant = False
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print(line, flush=True)
            continue

        kind = event.get("type")
        if kind == "assistant":
            # With --stream-partial-output, deltas include timestamp_ms; a final
            # duplicate full message omits it. Prefer deltas; fall back to full
            # messages when partial streaming is off.
            if "timestamp_ms" in event:
                saw_partial_assistant = True
            elif saw_partial_assistant:
                continue
            for block in event.get("message", {}).get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text") or ""
                    if text:
                        print(text, end="", flush=True)
        elif kind == "tool_call" and event.get("subtype") == "started":
            tool = event.get("tool_call", {}) or {}
            name = (
                tool.get("name")
                or tool.get("toolName")
                or event.get("name")
                or "tool"
            )
            print(f"\n[{name}]", flush=True)
        elif kind == "result":
            saw_result = True
            # Ensure a trailing newline after streamed assistant text.
            print(flush=True)
            if event.get("is_error"):
                err = event.get("result") or event.get("error") or "agent error"
                print(err, file=sys.stderr, flush=True)
                exit_code = 1

    if not saw_result:
        print("agent stream ended without a result event", file=sys.stderr)
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
