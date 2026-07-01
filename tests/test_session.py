"""Tests for session provenance: chain walking and stamped findings.

Sessions chain through their predecessor into a campaign thread; findings are
persisted as schema-shaped, age-/condition-stamped records the chain walker can
rediscover. This is the lab-notebook substrate.
"""

from datetime import UTC, datetime

from helix import session


def _write(sessions, slug, phase, predecessor, when, verdict=None):
    return session.write_session(
        sessions,
        phase=phase,
        slug=slug,
        now=when,
        predecessor=predecessor,
        verdict=verdict,
        summary=f"{phase} {slug}",
    )


def test_walk_chain_follows_predecessors_newest_first(tmp_path):
    sessions = tmp_path / "sessions"
    id0, _ = _write(
        sessions, "00-plan", "plan", None, datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    )
    id1, _ = _write(
        sessions,
        "00-implement",
        "implement",
        id0,
        datetime(2026, 7, 1, 10, 1, tzinfo=UTC),
    )
    id2, _ = _write(
        sessions,
        "00-judge",
        "judge",
        id1,
        datetime(2026, 7, 1, 10, 2, tzinfo=UTC),
        verdict="pass",
    )

    chain = session.walk_chain(sessions)

    assert [v.id for v in chain] == [id2, id1, id0]
    assert chain[0].phase == "judge"
    assert chain[0].verdict == "pass"
    assert chain[-1].predecessor is None


def test_walk_chain_isolates_one_thread(tmp_path):
    # A second, unrelated root on disk must not appear in the first thread's walk.
    sessions = tmp_path / "sessions"
    a0, _ = _write(
        sessions, "a", "implement", None, datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
    )
    a1, _ = _write(sessions, "a2", "judge", a0, datetime(2026, 7, 1, 9, 1, tzinfo=UTC))
    _write(
        sessions, "orphan", "implement", None, datetime(2026, 7, 1, 8, 0, tzinfo=UTC)
    )

    chain = session.walk_chain(sessions, start_id=a1)
    assert [v.id for v in chain] == [a1, a0]


def test_iter_sessions_is_chronological(tmp_path):
    sessions = tmp_path / "sessions"
    late, _ = _write(
        sessions, "z", "implement", None, datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    )
    early, _ = _write(
        sessions, "a", "implement", None, datetime(2026, 7, 1, 6, 0, tzinfo=UTC)
    )
    assert [v.id for v in session.iter_sessions(sessions)] == [early, late]


def test_findings_round_trip_stamped(tmp_path):
    sessions = tmp_path / "sessions"
    sid, sdir = _write(
        sessions, "00-judge", "judge", None, datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    )

    session.record_findings(
        sdir,
        ["the oracle passed"],
        session_id=sid,
        observed_at=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        conditions="repo=.; gates=[tests]",
    )

    findings = session.read_findings(sdir)
    assert len(findings) == 1
    assert findings[0]["statement"] == "the oracle passed"
    assert findings[0]["session"] == sid
    assert findings[0]["conditions"] == "repo=.; gates=[tests]"
    assert "2026-07-01" in findings[0]["observed_at"]


def test_read_findings_empty_when_absent(tmp_path):
    sessions = tmp_path / "sessions"
    _, sdir = _write(
        sessions, "x", "implement", None, datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    )
    assert session.read_findings(sdir) == []
