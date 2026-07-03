"""Implement phase — autonomous, low-judgment.

A worker makes bounded progress against the agreed plan in a fresh context
window, then writes its progress and evidence to disk. Work that is read-heavy
or draft may fan out across workers with disjoint write scopes; commits to
shared state are serialized.

This module composes the prompt from files, invokes the native worker (see
:mod:`helix.worker` — no tool reimplementation), and persists a session. It
holds no model judgment: it decides nothing about whether the work is done.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from helix import session, worker
from helix.config import Config
from helix.phases import base_prompt
from helix.state import read_doc

_RECENT_LIMIT = 3


@dataclass
class ImplementResult:
    """What one implement invocation produced."""

    id: str
    session_dir: Path
    output: str
    returncode: int = 0


def _recent_summaries(sessions_dir: Path) -> str:
    """A short digest of the latest sessions, so the worker sees prior progress."""
    if not sessions_dir.exists():
        return ""
    dirs = sorted(p for p in sessions_dir.iterdir() if (p / "session.md").exists())
    lines = []
    for d in dirs[-_RECENT_LIMIT:]:
        fm, _ = read_doc(d / "session.md")
        phase = fm.get("phase", "?")
        summary = fm.get("summary", "").strip()
        verdict = fm.get("verdict")
        tag = f" [{verdict}]" if verdict else ""
        lines.append(f"- **{phase}**{tag} `{d.name}` — {summary}")
    return "\n".join(lines)


def compose_prompt(config: Config, project: Path, sessions_dir: Path) -> str:
    """Assemble the implement prompt: base contract + agreed plan + recent progress."""
    sections = [base_prompt(project, "implement")]
    if config.plan:
        plan_path = project / config.plan
        if plan_path.exists():
            _, plan_body = read_doc(plan_path)
            sections.append("## The agreed plan\n\n" + plan_body.strip())
    recent = _recent_summaries(sessions_dir)
    if recent:
        sections.append("## Recent progress\n\n" + recent)
    return "\n\n".join(sections).strip() + "\n"


def run(
    config: Config,
    project: Path,
    *,
    sessions_dir: Path,
    slug: str,
    predecessor: str | None = None,
    now: datetime | None = None,
    observer: Callable[[str], None] | None = None,
    command: list[str] | None = None,
) -> ImplementResult:
    """Compose the prompt, run the worker in the repo, and persist a session.

    The session directory is created *before* the worker runs so its trace
    streams into ``evidence/worker.txt`` live (tail-able during the run). An
    optional ``observer`` is called with each output line for a live rendered
    train-of-thought (see :mod:`helix.observe`). ``command`` overrides the
    config's worker argv — the loop uses it to route a model or a resume flag
    (see :func:`helix.worker.build_command`) without touching config.
    """
    project = Path(project)
    sessions_dir = Path(sessions_dir)
    repo = (project / config.repo).resolve()
    now = now or datetime.now(UTC)

    prompt = compose_prompt(config, project, sessions_dir)
    session_id, session_dir = session.prepare_session(sessions_dir, slug=slug, now=now)
    (session_dir / "evidence" / "prompt.txt").write_text(prompt)

    try:
        invoked = worker.invoke(
            prompt,
            cwd=repo,
            command=command or config.worker.command,
            timeout_s=config.worker.timeout_s,
            sink=session_dir / "evidence" / "worker.txt",
            on_line=observer,
        )
    except subprocess.TimeoutExpired:
        # Persist the cut session before propagating — the streamed evidence is
        # already on disk and must stay discoverable in the chain.
        session.write_record(
            session_dir,
            id=session_id,
            phase="implement",
            created_at=now,
            predecessor=predecessor,
            summary=f"Worker cut by timeout after {config.worker.timeout_s}s.",
            body=(
                "# implement session\n\nThe worker exceeded its wall-clock cap "
                "and was cut. Partial trace in `evidence/worker.txt`; the run "
                "is resumable with the worker's continue flag."
            ),
        )
        raise
    output = invoked.output

    summary = (
        f"Worker ran in `{repo.name}` ({len(output)} chars of output, "
        f"exit {invoked.returncode})."
    )
    body = (
        f"# implement session\n\nThe worker was invoked with a fresh context in "
        f"`{repo}`. See `evidence/prompt.txt` for the composed prompt and "
        f"`evidence/worker.txt` for the worker's (streamed) output."
    )
    session.write_record(
        session_dir,
        id=session_id,
        phase="implement",
        created_at=now,
        predecessor=predecessor,
        summary=summary,
        body=body,
    )
    return ImplementResult(
        id=session_id,
        session_dir=session_dir,
        output=output,
        returncode=invoked.returncode,
    )
