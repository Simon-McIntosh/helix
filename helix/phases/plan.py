"""Plan phase — interactive, high-judgment.

This is the human's seat. Planning is where domain expertise enters and where
the human stays coupled to the work. The artifact crossing into the autonomous
loop is the agreed plan, which functions as a signed contract. Deterministic
metadata is written by the tool; judgment-laden content by the worker/human.
"""

from __future__ import annotations

from pathlib import Path


def run(project: Path) -> None:
    """Co-author the plan and materialize the contract the loop will consume.

    Raises ``NotImplementedError`` until the plan phase is built (bootstrap P2).
    """
    raise NotImplementedError("plan phase is a bootstrap target (P2)")
