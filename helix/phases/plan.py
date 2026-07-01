"""Plan phase — interactive, high-judgment.

This is the human's seat. Planning is where domain expertise enters and where
the human stays coupled to the work. The artifact crossing into the autonomous
loop is the agreed plan, which functions as a signed contract.

The determinism boundary is strict:

* The **tool** writes deterministic metadata — the :class:`~helix.models.PlanState`
  frontmatter (``id``, ``project``, and the ``agreed_at`` signature). It holds no
  model judgment.
* The **worker/human** writes the judgment-laden content — the Intent, the task
  units, and the oracle gates — as prose in the document body.

The phase runs in three moves: **scaffold** (materialize the ``PlanState``
skeleton), **co-author** (an interactive worker fills the body with the human in
the seat), and **seal** (stamp ``agreed_at`` — the human's signature that turns
a draft into the contract). The produced document is consumed unchanged by
``helix run`` — its body is composed into the implement prompt (see
:func:`helix.phases.implement.compose_prompt`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from helix import session, worker
from helix.config import Config
from helix.models import PlanState
from helix.phases import base_prompt
from helix.state import read_doc, write_doc

# Where an agreed plan lives when the project config names no path.
DEFAULT_PLAN_FILENAME = "PLAN.md"

# The judgment-laden sections the worker/human fills in the document body. The
# tool only owns the frontmatter; this template just orients the co-authoring.
_BODY_TEMPLATE = """# Plan

## Intent

<!-- The expanded specification, feature list, and constraints. -->

## Tasks

<!-- Ordered, independently verifiable task units. Each names a write scope and
     a verification command. -->

## Oracle gates

<!-- The completion criteria. Tag each `surrogate` (fast, every-iteration
     backpressure) or `blocking` (slow / physical; the loop waits for human
     ground truth). These become the gates in helix.yaml. -->
"""


@dataclass
class PlanResult:
    """What one plan invocation produced and whether it is a sealed contract."""

    id: str
    plan_path: Path
    session_dir: Path
    agreed: bool


def plan_path(config: Config, project: Path) -> Path:
    """Resolve where the agreed plan lives: ``config.plan`` or a conventional default.

    Kept in step with :func:`helix.phases.implement.compose_prompt`, which reads
    ``project / config.plan`` — so a plan materialized here is consumed unchanged
    by ``helix run``.
    """
    name = config.plan or DEFAULT_PLAN_FILENAME
    return Path(project) / name


def scaffold(
    path: Path, project_name: str, *, now: datetime | None = None
) -> PlanState:
    """Materialize (or preserve) a ``PlanState``-shaped plan document at ``path``.

    A fresh document gets deterministic frontmatter (``id``, ``project``) and a
    template body for the worker/human to fill. An existing draft is left intact
    — only its frontmatter is validated — so co-authoring can resume across
    sessions without clobbering work.
    """
    path = Path(path)
    if path.exists():
        frontmatter, _ = read_doc(path)
        return PlanState.model_validate(frontmatter)

    record = PlanState(id=session.new_session_id("plan", now=now), project=project_name)
    write_doc(path, record.model_dump(mode="json", exclude_none=True), _BODY_TEMPLATE)
    return record


def compose_prompt(
    config: Config, project: Path, path: Path, intent: str | None, repo: Path
) -> str:
    """Assemble the plan prompt: base contract + overlay + where to write + draft."""
    try:
        where = Path(path).resolve().relative_to(Path(repo).resolve())
    except ValueError:
        where = Path(path).resolve()

    sections = [base_prompt(project, "plan")]
    task = (
        "## Your task\n\n"
        f"Co-author the agreed plan for project `{Path(project).name}`. Write the "
        f"Intent, Tasks, and Oracle gates as prose into the body of `{where}`. "
        "Do not edit the frontmatter — Helix stamps `agreed_at` when the human "
        "signs off. Stop when the human agrees the plan is the contract."
    )
    sections.append(task)
    if intent:
        sections.append("## Starting intent\n\n" + intent.strip())

    _, draft = read_doc(path)
    if draft.strip():
        sections.append("## Current draft\n\n" + draft.strip())
    return "\n\n".join(sections).strip() + "\n"


def seal(path: Path, *, now: datetime | None = None) -> PlanState:
    """Stamp ``agreed_at`` on the plan document — the human's signature.

    Reads the document, validates its metadata as a :class:`PlanState`, sets the
    agreement timestamp, and rewrites the frontmatter (the body prose is left
    exactly as the worker/human authored it).
    """
    frontmatter, body = read_doc(path)
    record = PlanState.model_validate(frontmatter)
    record.agreed_at = now or datetime.now(UTC)
    write_doc(path, record.model_dump(mode="json", exclude_none=True), body)
    return record


def run(
    config: Config,
    project: Path,
    *,
    sessions_dir: Path,
    slug: str = "plan",
    intent: str | None = None,
    agree: bool = False,
    out: Path | None = None,
    invoke_worker: bool = True,
    predecessor: str | None = None,
    now: datetime | None = None,
) -> PlanResult:
    """Scaffold, co-author, and (on agreement) seal the plan; persist a session.

    The document is materialized with deterministic ``PlanState`` metadata, an
    interactive worker fills its body with the human in the seat, and — when the
    human agrees — the tool stamps ``agreed_at`` to turn the draft into the
    signed contract. A plan session records the handoff (fresh context, files as
    the artifact).
    """
    project = Path(project)
    sessions_dir = Path(sessions_dir)
    repo = (project / config.repo).resolve()
    path = (Path(out) if out else plan_path(config, project)).resolve()

    scaffold(path, project.name, now=now)
    prompt = compose_prompt(config, project, path, intent, repo)

    if invoke_worker:
        worker.converse(prompt, cwd=repo, command=config.worker.command)

    agreed = False
    if agree:
        seal(path, now=now)
        agreed = True

    state = "agreed (contract sealed)" if agreed else "draft"
    summary = f"Plan {state} at `{path.name}` for project `{project.name}`."
    body = (
        f"# plan session\n\nInteractive planning for `{project.name}`. The agreed "
        f"plan is at `{path}` ({state}). Deterministic metadata is written by the "
        f"tool; the judgment-laden body is co-authored by the worker and human. "
        f"See `evidence/prompt.txt` for the composed plan-phase prompt."
    )
    session_id, session_dir = session.write_session(
        sessions_dir,
        phase="plan",
        slug=slug,
        now=now,
        predecessor=predecessor,
        summary=summary,
        body=body,
    )
    (session_dir / "evidence" / "prompt.txt").write_text(prompt)
    return PlanResult(
        id=session_id, plan_path=path, session_dir=session_dir, agreed=agreed
    )
