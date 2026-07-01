"""Tests for the implement and judge phases.

Phases are distinct invocations that hand off through files. The implement phase
runs the worker and persists a session; the judge phase runs the oracle (a
separate invocation — never the worker) and records its verdict. Fresh context,
files as the handoff.
"""

from helix.config import Config
from helix.phases import implement, judge
from helix.state import read_doc


def _config(command, gates=None, repo="."):
    return Config.model_validate(
        {"repo": repo, "worker": {"command": command}, "gates": gates or []}
    )


def test_implement_runs_worker_in_repo_and_persists_session(tmp_path):
    # Worker consumes the prompt on stdin and makes a real change in the repo.
    config = _config(["sh", "-c", "cat >/dev/null; echo worked; : > done.txt"])
    sessions = tmp_path / "sessions"

    result = implement.run(config, tmp_path, sessions_dir=sessions, slug="00-implement")

    # The worker's change landed in the repo (cwd).
    assert (tmp_path / "done.txt").exists()
    # A session with the schema's record shape was written.
    session_md = result.session_dir / "session.md"
    assert session_md.exists()
    fm, _ = read_doc(session_md)
    assert fm["phase"] == "implement"
    assert fm["id"] == result.id
    # The worker's output is preserved as evidence.
    assert "worked" in (result.session_dir / "evidence" / "worker.txt").read_text()


def test_implement_composes_plan_into_the_prompt(tmp_path):
    (tmp_path / "plan.md").write_text("# Plan\n\nBuild the thing.\n")
    config = Config.model_validate({"worker": {"command": ["cat"]}, "plan": "plan.md"})
    sessions = tmp_path / "sessions"

    result = implement.run(config, tmp_path, sessions_dir=sessions, slug="00-implement")

    # cat echoes the composed prompt back to stdout -> evidence.
    evidence = (result.session_dir / "evidence" / "worker.txt").read_text()
    assert "Build the thing." in evidence


def test_judge_passes_when_surrogate_gate_is_met(tmp_path):
    (tmp_path / "done.txt").write_text("x")
    config = _config(
        ["true"],
        gates=[
            {
                "id": "done",
                "name": "done marker",
                "tier": "surrogate",
                "criterion": "done.txt exists",
                "command": "test -f done.txt",
            }
        ],
    )
    sessions = tmp_path / "sessions"

    result = judge.run(config, tmp_path, sessions_dir=sessions, slug="00-judge")

    assert result.verdict == "pass"
    fm, _ = read_doc(result.session_dir / "session.md")
    assert fm["phase"] == "judge"
    assert fm["verdict"] == "pass"


def test_judge_fails_when_surrogate_gate_is_unmet(tmp_path):
    config = _config(
        ["true"],
        gates=[
            {
                "id": "done",
                "name": "done marker",
                "tier": "surrogate",
                "criterion": "done.txt exists",
                "command": "test -f done.txt",
            }
        ],
    )
    sessions = tmp_path / "sessions"

    result = judge.run(config, tmp_path, sessions_dir=sessions, slug="00-judge")

    assert result.verdict == "fail"
    fm, _ = read_doc(result.session_dir / "session.md")
    assert fm["verdict"] == "fail"


def test_judge_records_predecessor_for_chaining(tmp_path):
    config = _config(["true"])  # no gates -> vacuous pass
    sessions = tmp_path / "sessions"

    result = judge.run(
        config,
        tmp_path,
        sessions_dir=sessions,
        slug="00-judge",
        predecessor="20260701T000000Z-00-implement",
    )

    fm, _ = read_doc(result.session_dir / "session.md")
    assert fm["predecessor"] == "20260701T000000Z-00-implement"
