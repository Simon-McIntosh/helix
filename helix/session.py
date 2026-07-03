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

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from helix import state
from helix.models import Finding, Phase, Session, Verdict

SESSION_FILENAME = "session.md"
FINDINGS_FILENAME = "findings.md"


def new_session_id(slug: str, *, now: datetime | None = None) -> str:
    """Return a human-sortable session id: ``YYYYMMDDTHHMMSSZ-<slug>``.

    Lexical sort order equals chronological order, which is what the campaign
    chain walker relies on.
    """
    now = now or datetime.now(UTC)
    return f"{now.strftime('%Y%m%dT%H%M%SZ')}-{slug}"


def prepare_session(
    sessions_dir: Path, *, slug: str, now: datetime | None = None
) -> tuple[str, Path]:
    """Allocate a session id and create its directory (with ``evidence/``).

    Split out from :func:`write_session` so a phase can start streaming evidence
    into the session *before* it finalizes the record — the worker's trace lands
    in ``evidence/`` live, tail-able as it is produced.
    """
    now = now or datetime.now(UTC)
    session_id = new_session_id(slug, now=now)
    session_dir = Path(sessions_dir) / session_id
    # Same-second collisions (fast loops, back-to-back runs) get a lexical
    # suffix so every session stays self-contained and the sort order holds.
    bump = 2
    while (session_dir / SESSION_FILENAME).exists():
        session_id = f"{new_session_id(slug, now=now)}-{bump}"
        session_dir = Path(sessions_dir) / session_id
        bump += 1
    (session_dir / "evidence").mkdir(parents=True, exist_ok=True)
    return session_id, session_dir


def write_record(
    session_dir: Path,
    *,
    id: str,
    phase: str,
    created_at: datetime,
    predecessor: str | None = None,
    summary: str | None = None,
    verdict: str | None = None,
    body: str = "",
) -> None:
    """Write a session's ``session.md``: schema :class:`Session` frontmatter + body."""
    record = Session(
        id=id,
        phase=Phase(phase),
        predecessor=predecessor,
        created_at=created_at,
        verdict=Verdict(verdict) if verdict else None,
        summary=summary,
    )
    state.write_doc(
        Path(session_dir) / SESSION_FILENAME,
        record.model_dump(mode="json", exclude_none=True),
        body or f"# {phase} session\n\nSession `{id}`.",
    )


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
    session_id, session_dir = prepare_session(sessions_dir, slug=slug, now=now)
    write_record(
        session_dir,
        id=session_id,
        phase=phase,
        created_at=now,
        predecessor=predecessor,
        summary=summary,
        verdict=verdict,
        body=body,
    )
    return session_id, session_dir


@dataclass
class SessionView:
    """A read-only view of one persisted session, for chain walking and status."""

    id: str
    dir: Path
    phase: str
    predecessor: str | None
    verdict: str | None
    summary: str | None
    created_at: str | None


def _view(session_dir: Path) -> SessionView:
    frontmatter, _ = state.read_doc(Path(session_dir) / SESSION_FILENAME)
    return SessionView(
        id=frontmatter.get("id", Path(session_dir).name),
        dir=Path(session_dir),
        phase=frontmatter.get("phase", "?"),
        predecessor=frontmatter.get("predecessor"),
        verdict=frontmatter.get("verdict"),
        summary=frontmatter.get("summary"),
        created_at=frontmatter.get("created_at"),
    )


def iter_sessions(sessions_dir: Path) -> list[SessionView]:
    """All sessions under ``sessions_dir``, sorted chronologically (oldest first)."""
    sessions_dir = Path(sessions_dir)
    if not sessions_dir.exists():
        return []
    dirs = sorted(p for p in sessions_dir.iterdir() if (p / SESSION_FILENAME).exists())
    return [_view(d) for d in dirs]


def walk_chain(sessions_dir: Path, start_id: str | None = None) -> list[SessionView]:
    """Walk the predecessor chain, newest first.

    Starts from ``start_id`` (default: the latest session) and follows each
    session's ``predecessor`` link back to the root, so the returned list is one
    coherent campaign thread — not merely everything on disk. A dangling
    predecessor (an id with no session) simply ends the walk.
    """
    by_id = {v.id: v for v in iter_sessions(sessions_dir)}
    if not by_id:
        return []
    current = start_id or max(by_id)
    chain: list[SessionView] = []
    seen: set[str] = set()
    while current and current in by_id and current not in seen:
        seen.add(current)
        view = by_id[current]
        chain.append(view)
        current = view.predecessor
    return chain


def record_findings(
    session_dir: Path,
    statements: list[str],
    *,
    session_id: str,
    observed_at: datetime,
    conditions: str | None = None,
    body: str | None = None,
) -> list[Finding]:
    """Persist age- and condition-stamped :class:`Finding` records for a session.

    Findings are the durable, stamped claims of a session — written as schema
    records in ``findings.md`` frontmatter (a ``findings`` list) with a readable
    body, so the chain walker can rediscover them years later with their
    ``observed_at`` time and the ``conditions`` under which they held.
    """
    findings = [
        Finding(
            id=f"{session_id}-f{i}",
            statement=statement,
            observed_at=observed_at,
            conditions=conditions,
            session=session_id,
        )
        for i, statement in enumerate(statements)
    ]
    frontmatter = {
        "findings": [f.model_dump(mode="json", exclude_none=True) for f in findings]
    }
    default_body = "# Findings\n\n" + "\n".join(
        f"- {f.statement} _(observed {f.observed_at.isoformat()}"
        + (f"; conditions: {f.conditions}" if f.conditions else "")
        + ")_"
        for f in findings
    )
    state.write_doc(
        Path(session_dir) / FINDINGS_FILENAME, frontmatter, body or default_body
    )
    return findings


def read_findings(session_dir: Path) -> list[dict]:
    """Read a session's persisted :class:`Finding` records, or ``[]`` if none."""
    path = Path(session_dir) / FINDINGS_FILENAME
    if not path.exists():
        return []
    frontmatter, _ = state.read_doc(path)
    return frontmatter.get("findings", []) or []
