"""Sessions and provenance.

Contract
--------
Every run is a self-contained, human-sortable session. Sessions reference their
predecessor, forming a campaign thread that can be walked over years. Findings
produced in a session are age- and condition-stamped so the durable record
knows when, and under what conditions, each claim was true.

Session state is plain text committed to git — this is the lab-notebook role and
for multi-year campaigns it is the primary asset.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from helix import state
from helix.models import Phase, Session, Verdict


def new_session_id(slug: str, *, now: datetime | None = None) -> str:
    """Return a human-sortable session id: ``YYYYMMDDTHHMMSSZ-<slug>``.

    Lexical sort order equals chronological order, which is what the campaign
    chain walker relies on.
    """
    now = now or datetime.now(UTC)
    return f"{now.strftime('%Y%m%dT%H%M%SZ')}-{slug}"


def write_session(
    sessions_dir: Path,
    *,
    phase: str,
    slug: str,
    now: datetime | None = None,
    predecessor: str | None = None,
    summary: str | None = None,
    verdict: str | None = None,
    body: str = "",
) -> tuple[str, Path]:
    """Create a session directory and write its ``session.md`` record.

    Returns ``(session_id, session_dir)``. The record shape is the schema's
    :class:`~helix.models.Session`; ``session.md`` carries it as frontmatter and
    a human-readable narrative as the body. An ``evidence/`` subdirectory is
    created for the phase to drop test output, logs, and traces into.
    """
    now = now or datetime.now(UTC)
    session_id = new_session_id(slug, now=now)
    session_dir = Path(sessions_dir) / session_id
    (session_dir / "evidence").mkdir(parents=True, exist_ok=True)

    record = Session(
        id=session_id,
        phase=Phase(phase),
        predecessor=predecessor,
        created_at=now,
        verdict=Verdict(verdict) if verdict else None,
        summary=summary,
    )
    frontmatter = record.model_dump(mode="json", exclude_none=True)
    state.write_doc(
        session_dir / "session.md",
        frontmatter,
        body or f"# {phase} session\n\nSession `{session_id}`.",
    )
    return session_id, session_dir
