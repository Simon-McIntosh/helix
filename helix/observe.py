"""Observability — render the worker's own trace as a live train-of-thought.

The worker (a native agent CLI) can emit a structured event stream — for a
Claude Code worker, ``--output-format stream-json --verbose`` produces
newline-delimited JSON: a ``system``/``init`` header, ``assistant`` turns whose
content blocks are text / thinking / tool_use, ``user`` turns carrying
tool_result blocks, and a final ``result`` with cost and timing.

This module is a **projection**: it reads the worker's own emitted trace and
formats it for a human. It never steers the worker and never reimplements its
tools — it only makes the trace legible. Each line is rendered independently, so
it works equally on a live stream (via :func:`helix.worker.invoke`'s ``on_line``)
and on a replay of the captured ``evidence/worker.txt``. Lines that are not
recognizable JSON events pass through verbatim — a worker configured for plain
``text`` output still renders, just without the structure.
"""

from __future__ import annotations

import json

from rich.markup import escape

# Tool-input fields worth surfacing, in priority order — the one identifying
# argument for the common tools, so the action line reads at a glance.
_INPUT_KEYS = ("command", "file_path", "path", "pattern", "query", "url", "prompt")


def _summarize_input(payload: dict) -> str:
    """A compact one-line summary of a tool_use input."""
    for key in _INPUT_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            flat = " ".join(value.split())
            return flat if len(flat) <= 70 else flat[:67] + "…"
    if not payload:
        return ""
    flat = " ".join(json.dumps(payload, default=str).split())
    return flat if len(flat) <= 70 else flat[:67] + "…"


def _render_assistant(message: dict, *, markup: bool) -> list[str]:
    esc = escape if markup else (lambda s: s)
    lines: list[str] = []
    for block in message.get("content", []):
        btype = block.get("type")
        if btype == "text":
            text = block.get("text", "").strip()
            if text:
                lines.append(esc(text))
        elif btype == "thinking":
            think = " ".join(block.get("thinking", "").split())
            if think:
                snippet = think if len(think) <= 200 else think[:197] + "…"
                lines.append(
                    f"[dim]  … {esc(snippet)}[/dim]" if markup else f"  … {snippet}"
                )
        elif btype == "tool_use":
            name = block.get("name", "tool")
            summary = _summarize_input(block.get("input", {}) or {})
            body = f"→ {esc(name)}({esc(summary)})" if summary else f"→ {esc(name)}"
            lines.append(f"[cyan]{body}[/cyan]" if markup else body)
    return lines


def _render_tool_results(message: dict, *, markup: bool) -> list[str]:
    lines: list[str] = []
    for block in message.get("content", []):
        if block.get("type") != "tool_result":
            continue
        content = block.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(part.get("text", "")) for part in content if isinstance(part, dict)
            )
        n = len(str(content))
        status = "err" if block.get("is_error") else "ok"
        body = f"← result ({status}, {n} chars)"
        lines.append(f"[dim]{body}[/dim]" if markup else body)
    return lines


def render_line(line: str, *, markup: bool = True) -> str | None:
    """Render one stream line to a human-readable string, or ``None`` to skip it.

    Recognizes Claude Code ``stream-json`` events; unrecognized-but-valid events
    (heartbeats, hooks, rate-limit notices, token deltas) return ``None`` so the
    train-of-thought stays signal. Non-JSON lines pass through verbatim.
    """
    esc = escape if markup else (lambda s: s)
    line = line.strip()
    if not line:
        return None
    if not line.startswith("{"):
        return esc(line)  # plain-text worker output — show as-is.

    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return esc(line)

    etype = event.get("type")
    if etype == "system" and event.get("subtype") == "init":
        model = esc(str(event.get("model", "?")))
        tools = len(event.get("tools", []) or [])
        mode = esc(str(event.get("permissionMode", "?")))
        body = f"● worker init — model={model} · tools={tools} · perms={mode}"
        return f"[bold]{body}[/bold]" if markup else body
    if etype == "assistant":
        rendered = _render_assistant(event.get("message", {}) or {}, markup=markup)
        return "\n".join(rendered) if rendered else None
    if etype == "user":
        rendered = _render_tool_results(event.get("message", {}) or {}, markup=markup)
        return "\n".join(rendered) if rendered else None
    if etype == "result":
        turns = event.get("num_turns", "?")
        cost = event.get("total_cost_usd")
        dur = event.get("duration_ms")
        parts = [f"turns={turns}"]
        if isinstance(cost, int | float):
            parts.append(f"cost=${cost:.4f}")
        if isinstance(dur, int | float):
            parts.append(f"{dur / 1000:.1f}s")
        marker = "✗" if event.get("is_error") else "✓"
        body = f"{marker} worker done — " + " · ".join(parts)
        return f"[bold]{body}[/bold]" if markup else body
    return None


def render_stream(lines: list[str], *, markup: bool = True) -> list[str]:
    """Render a whole captured stream, dropping skipped lines."""
    out = []
    for line in lines:
        rendered = render_line(line, markup=markup)
        if rendered is not None:
            out.append(rendered)
    return out
