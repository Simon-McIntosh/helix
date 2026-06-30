"""Smoke tests for the only piece of real logic in the bootstrap scaffold.

These exist so the loop's surrogate oracle (the test suite) has a green
baseline from day one. Every other module raises NotImplementedError by design
until its bootstrap phase lands.
"""

from datetime import UTC, datetime

from helix.session import new_session_id


def test_session_id_is_human_sortable_and_chronological() -> None:
    early = new_session_id("a", now=datetime(2026, 6, 30, 10, 15, 0, tzinfo=UTC))
    late = new_session_id("b", now=datetime(2026, 6, 30, 10, 16, 0, tzinfo=UTC))
    assert early == "20260630T101500Z-a"
    assert early < late  # lexical order == chronological order


def test_session_id_embeds_slug() -> None:
    sid = new_session_id("bootstrap-p1", now=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))
    assert sid.endswith("-bootstrap-p1")
    assert sid.startswith("20260102T030405Z")
