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


def new_session_id(slug: str, *, now: datetime | None = None) -> str:
    """Return a human-sortable session id: ``YYYYMMDDTHHMMSSZ-<slug>``.

    Lexical sort order equals chronological order, which is what the campaign
    chain walker relies on.
    """
    now = now or datetime.now(UTC)
    return f"{now.strftime('%Y%m%dT%H%M%SZ')}-{slug}"
