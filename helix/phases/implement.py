"""Implement phase — autonomous, low-judgment.

A worker makes bounded progress against the agreed plan in a fresh context
window, then writes its progress and evidence to disk. Work that is read-heavy
or draft may fan out across workers with disjoint write scopes; commits to
shared state are serialized.
"""

from __future__ import annotations

from pathlib import Path


def run(project: Path) -> None:
    """Make one bounded increment of progress against the plan and persist evidence.

    Raises ``NotImplementedError`` until the implement phase is built (P1).
    """
    raise NotImplementedError("implement phase is a bootstrap target (P1)")
