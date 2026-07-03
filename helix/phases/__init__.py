"""The three phase contracts: plan, implement, judge.

Each phase is a distinct worker invocation with a fresh context. Phases hand off
through files, never through an accumulating conversation. The judge is always a
separate invocation from the worker — a worker never declares its own work done.
"""

from __future__ import annotations

from pathlib import Path

from helix import overlay

# Base prompts ship alongside the package (repo layout: prompts/ beside helix/).
PROMPTS_DIR = overlay.CORE_PROMPTS_DIR


def base_prompt(project: Path, phase: str) -> str:
    """The phase contract: the packaged core plus the project's appended overlay.

    A project layers domain guidance over the core contract by shipping
    ``prompts/overlay.<phase>.md`` — appended, never substituted (see
    :mod:`helix.overlay` for the resolution and the anti-drift check).
    """
    return overlay.resolve_prompt(Path(project), phase)
