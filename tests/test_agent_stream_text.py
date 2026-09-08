"""Behavior tests for ``scripts/agent_stream_text.py``."""

from __future__ import annotations

import json

from conftest import run_repo_script


def run_filter(events: list[dict]) -> tuple[int, str, str]:
    stdin = "\n".join(json.dumps(e) for e in events) + "\n"
    proc = run_repo_script("agent_stream_text.py", stdin=stdin)
    return proc.returncode, proc.stdout, proc.stderr


def test_prints_assistant_text_and_succeeds() -> None:
    code, out, err = run_filter(
        [
            {
                "type": "assistant",
                "timestamp_ms": 1,
                "message": {"content": [{"type": "text", "text": "hi "}]},
            },
            {
                "type": "assistant",
                "timestamp_ms": 2,
                "message": {"content": [{"type": "text", "text": "there"}]},
            },
            # Final non-delta duplicate — must be ignored.
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "hi there"}]},
            },
            {"type": "result", "subtype": "success", "is_error": False, "result": "hi there"},
        ]
    )
    assert code == 0, err
    assert out.count("hi there") == 1 or out.replace("\n", "") == "hi there"


def test_fails_on_error_result() -> None:
    code, _out, err = run_filter(
        [
            {"type": "result", "subtype": "error", "is_error": True, "result": "boom"},
        ]
    )
    assert code == 1
    assert "boom" in err


def test_fails_without_result_event() -> None:
    code, _out, err = run_filter(
        [
            {
                "type": "assistant",
                "timestamp_ms": 1,
                "message": {"content": [{"type": "text", "text": "x"}]},
            }
        ]
    )
    assert code == 1
    assert "without a result" in err
