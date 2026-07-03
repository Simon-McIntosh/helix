"""Machine-countable plan tasks.

Contract
--------
The Tasks section of the agreed plan is the loop's only progress signal, so it
must be countable without judgment: each task unit is a markdown checkbox
(``- [ ]`` open, ``- [x]`` done) that the *worker* checks off as part of writing
its progress state back to disk. The tool never decides a task is done — it
only counts boxes.

A task may carry a per-step model annotation, e.g.::

    - [ ] Build the parser (model: haiku)

which the loop routes to the worker invocation (see :mod:`helix.loop`). The
annotation is data in the plan — the human priced the step at plan time — not a
runtime judgment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from helix.state import read_doc

_CHECKBOX = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*\S)\s*$")
_MODEL = re.compile(r"\s*\(\s*model\s*:\s*([^)]+?)\s*\)", re.IGNORECASE)
_TASKS_HEADING = re.compile(r"^#{1,6}\s+tasks\s*$", re.IGNORECASE)
_ANY_HEADING = re.compile(r"^#{1,6}\s+\S")


@dataclass(frozen=True)
class Task:
    """One checkbox task unit from the agreed plan."""

    text: str
    done: bool
    model: str | None = None


def _tasks_section(body: str) -> str:
    """The lines under the Tasks heading, or the whole body if there is none.

    Scoping to the heading keeps stray checklists elsewhere in the plan (e.g.
    oracle-gate notes) out of the progress count.
    """
    lines = body.splitlines()
    start = next(
        (i + 1 for i, line in enumerate(lines) if _TASKS_HEADING.match(line)), None
    )
    if start is None:
        return body
    end = next(
        (i for i in range(start, len(lines)) if _ANY_HEADING.match(lines[i])),
        len(lines),
    )
    return "\n".join(lines[start:end])


def parse_tasks(body: str) -> list[Task]:
    """Parse the plan body's checkbox tasks into :class:`Task` records."""
    items: list[Task] = []
    for line in _tasks_section(body).splitlines():
        match = _CHECKBOX.match(line)
        if not match:
            continue
        mark, text = match.groups()
        model_match = _MODEL.search(text)
        model = model_match.group(1) if model_match else None
        text = _MODEL.sub("", text).strip()
        items.append(Task(text=text, done=mark in "xX", model=model))
    return items


def next_task(items: list[Task]) -> Task | None:
    """The first open task — the unit the next worker iteration should pick."""
    return next((t for t in items if not t.done), None)


def progress(items: list[Task]) -> tuple[int, int]:
    """``(done, total)`` box counts — the loop's whole progress model."""
    return sum(1 for t in items if t.done), len(items)


def read_tasks(plan_path: Path) -> list[Task]:
    """Read a plan document's tasks from disk (``[]`` if the file is absent)."""
    plan_path = Path(plan_path)
    if not plan_path.exists():
        return []
    _, body = read_doc(plan_path)
    return parse_tasks(body)
