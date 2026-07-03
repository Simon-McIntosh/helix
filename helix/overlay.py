"""Core-vs-overlay resolution and the anti-drift check.

Contract
--------
Helix is a project-agnostic core plus project-specific data. A project layers
domain guidance over a phase contract by shipping
``<project>/prompts/overlay.<phase>.md`` — the extension is **appended** to the
packaged core contract at compose time. Overlays extend; they never replace.

Drift between projects is the chief long-term risk and is designed against: a
project that ships a full ``prompts/<phase>.md`` replacement has forked the
core contract, and :func:`check_project` flags it mechanically (no judgment —
path identity, verbatim heading duplication, and size are the signals). The one
sanctioned identity: when the project directory *is* the Helix repo itself
(self-hosting), its ``prompts/<phase>.md`` resolves to the core file and is
simply the contract, not a fork.
"""

from __future__ import annotations

from pathlib import Path

from helix.config import load_config

# The packaged core contracts (repo layout: prompts/ beside helix/).
CORE_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

PHASES = ("plan", "implement", "judge")


def _core_path(phase: str) -> Path:
    return CORE_PROMPTS_DIR / f"{phase}.md"


def _core_prompt(phase: str) -> str:
    path = _core_path(phase)
    if path.exists():
        return path.read_text()
    return f"# {phase} phase\n\n(No base prompt found.)\n"


def overlay_path(project: Path, phase: str) -> Path:
    """Where a project's extension for one phase contract lives."""
    return Path(project) / "prompts" / f"overlay.{phase}.md"


def resolve_prompt(project: Path, phase: str) -> str:
    """The phase contract for a project: core contract + appended extension.

    A legacy full-replacement ``<project>/prompts/<phase>.md`` is ignored here
    (the drift check flags it) — resolution never lets a project fork the core.
    """
    sections = [_core_prompt(phase)]
    extension = overlay_path(project, phase)
    if extension.exists():
        sections.append(extension.read_text())
    return "\n\n".join(s.strip() for s in sections if s.strip()) + "\n"


def _check_prompts(project: Path) -> list[str]:
    problems: list[str] = []
    for phase in PHASES:
        replacement = Path(project) / "prompts" / f"{phase}.md"
        if replacement.exists() and (
            not _core_path(phase).exists()
            or replacement.resolve() != _core_path(phase).resolve()
        ):
            problems.append(
                f"prompts/{phase}.md: forked core contract — move domain "
                f"guidance to prompts/overlay.{phase}.md (extensions are "
                "appended, never substituted)"
            )

        extension = overlay_path(project, phase)
        if not extension.exists():
            continue
        core = _core_prompt(phase)
        overlay_text = extension.read_text()
        core_headings = {
            line.strip()
            for line in core.splitlines()
            if line.lstrip().startswith("#") and line.strip()
        }
        duplicated = sorted(
            line.strip()
            for line in overlay_text.splitlines()
            if line.strip() in core_headings
        )
        if duplicated:
            problems.append(
                f"prompts/overlay.{phase}.md: restates the core contract "
                f"(duplicated heading {duplicated[0]!r}) — extend it, don't "
                "repeat it"
            )
        if len(overlay_text.encode()) > len(core.encode()):
            problems.append(
                f"prompts/overlay.{phase}.md: larger than the core contract — "
                "overlays are small diffs; push general guidance into the core"
            )
    return problems


def _check_config(project: Path) -> list[str]:
    try:
        config = load_config(Path(project))
    except FileNotFoundError:
        return ["helix.yaml: missing — a project needs a run configuration"]

    problems: list[str] = []
    seen: set[str] = set()
    for gate in config.gates:
        if gate.id in seen:
            problems.append(f"helix.yaml: duplicate gate id {gate.id!r}")
        seen.add(gate.id)
        if gate.tier == "surrogate" and not (gate.command or "").strip():
            problems.append(
                f"helix.yaml: surrogate gate {gate.id!r} has no command — "
                "surrogate gates must be mechanically runnable"
            )
    if config.plan and not (Path(project) / config.plan).exists():
        problems.append(f"{config.plan}: configured plan file is missing")
    return problems


def check_project(project: Path) -> list[str]:
    """Mechanical anti-drift audit of one project; ``[]`` means clean.

    Every problem is a one-line, actionable string prefixed by the
    project-relative path it concerns.
    """
    return _check_prompts(project) + _check_config(project)
