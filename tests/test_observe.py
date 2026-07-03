"""Tests for the observability stream renderer.

observe.render_line is a projection over the worker's own emitted trace: it
turns Claude Code stream-json events into a legible train-of-thought and passes
plain text through. It never steers the worker. Event shapes here mirror what
`claude -p --output-format stream-json --verbose` actually emits.
"""

import json

from helix import observe


def test_init_event_renders_a_header():
    line = json.dumps(
        {
            "type": "system",
            "subtype": "init",
            "model": "claude-sonnet-5",
            "tools": ["Read", "Edit", "Bash"],
            "permissionMode": "acceptEdits",
        }
    )
    out = observe.render_line(line, markup=False)
    assert "worker init" in out
    assert "claude-sonnet-5" in out
    assert "tools=3" in out


def test_assistant_text_renders_the_prose():
    line = json.dumps(
        {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "pong"}]},
        }
    )
    assert observe.render_line(line, markup=False) == "pong"


def test_tool_use_renders_an_action_with_a_summary():
    line = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "pytest -q"},
                    }
                ]
            },
        }
    )
    out = observe.render_line(line, markup=False)
    assert "→ Bash(pytest -q)" == out


def test_thinking_renders_dimmed():
    line = json.dumps(
        {
            "type": "assistant",
            "message": {"content": [{"type": "thinking", "thinking": "let me check"}]},
        }
    )
    out = observe.render_line(line, markup=False)
    assert "let me check" in out
    assert out.strip().startswith("…")


def test_tool_result_renders_status_and_size():
    line = json.dumps(
        {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "x", "content": "hello"}
                ]
            },
        }
    )
    out = observe.render_line(line, markup=False)
    assert "← result" in out
    assert "ok" in out
    assert "5 chars" in out


def test_result_event_renders_a_footer_with_cost_and_turns():
    line = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "num_turns": 3,
            "total_cost_usd": 0.1807,
            "duration_ms": 3216,
        }
    )
    out = observe.render_line(line, markup=False)
    assert "worker done" in out
    assert "turns=3" in out
    assert "cost=$0.1807" in out
    assert "3.2s" in out


def test_noise_events_are_skipped():
    for etype in ("rate_limit_event", "stream_event"):
        assert observe.render_line(json.dumps({"type": etype})) is None
    assert observe.render_line("   ") is None


def test_plain_text_passes_through():
    assert observe.render_line("just some output") == "just some output"
    assert observe.render_line("not json {oops", markup=False) == "not json {oops"


def test_markup_mode_escapes_brackets_in_data():
    # Data containing [..] must be escaped so Rich does not eat it as a style tag.
    line = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "ls [a]"}}
                ]
            },
        }
    )
    out = observe.render_line(line, markup=True)
    assert "\\[a]" in out


def test_render_stream_drops_skipped_lines():
    lines = [
        json.dumps(
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "hi"}]},
            }
        ),
        json.dumps({"type": "rate_limit_event"}),
        "plain",
    ]
    assert observe.render_stream(lines, markup=False) == ["hi", "plain"]


def _result(subtype="success", **extra):
    return json.dumps({"type": "result", "subtype": subtype, **extra})


def test_classify_trace_ok_on_clean_exit_and_success_result():
    trace = _result(num_turns=3) + "\n"
    assert observe.classify_trace(trace, 0) == observe.OK


def test_classify_trace_ok_for_plain_text_worker():
    # A stand-in/plain worker emits no result event; exit 0 is completion.
    assert observe.classify_trace("did the thing\n", 0) == observe.OK


def test_classify_trace_interrupted_on_nonzero_exit():
    assert observe.classify_trace("Claude AI usage limit reached\n", 1) == (
        observe.INTERRUPTED
    )


def test_classify_trace_interrupted_on_error_result_event():
    trace = _result(subtype="error_during_execution", is_error=True) + "\n"
    assert observe.classify_trace(trace, 0) == observe.INTERRUPTED


def test_classify_trace_not_fooled_by_prose_about_limits():
    trace = "let's discuss the rate limit design\n" + _result() + "\n"
    assert observe.classify_trace(trace, 0) == observe.OK


def test_halt_reason_prefers_the_result_event_then_the_tail():
    trace = _result(subtype="error", result="Context low · Run /compact") + "\n"
    assert observe.halt_reason(trace) == "Context low · Run /compact"
    assert observe.halt_reason("boom: usage limit\n") == "boom: usage limit"
    assert observe.halt_reason("") is None
