"""The three phase contracts: plan, implement, judge.

Each phase is a distinct worker invocation with a fresh context. Phases hand off
through files, never through an accumulating conversation. The judge is always a
separate invocation from the worker — a worker never declares its own work done.
"""

from __future__ import annotations

from pathlib import Path

# Base prompts ship alongside the package (repo layout: prompts/ beside helix/).
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def base_prompt(project: Path, phase: str) -> str:
    """The base phase contract: project overlay first, then the packaged default.

    A project may layer domain guidance over the core contract by shipping its
    own ``prompts/<phase>.md``; otherwise the project-agnostic default is used.
    """
    for candidate in (
        Path(project) / "prompts" / f"{phase}.md",
        PROMPTS_DIR / f"{phase}.md",
    ):
        if candidate.exists():
            return candidate.read_text()
    return f"# {phase} phase\n\n(No base prompt found.)\n"
