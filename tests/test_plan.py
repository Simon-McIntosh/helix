"""Tests for the plan phase — the human's seat.

The plan phase materializes a ``PlanState``-shaped contract on disk: the tool
writes deterministic metadata (frontmatter), the worker/human writes the
judgment-laden body, and sealing stamps ``agreed_at``. The produced document is
consumed unchanged by ``helix run``.
"""

from datetime import datetime

from helix.config import Config
from helix.models import PlanState
from helix.phases import implement, plan
from helix.state import read_doc


def _config(command, plan_file="PLAN.md"):
    return Config.model_validate(
        {"repo": ".", "plan": plan_file, "worker": {"command": command}}
    )


def test_scaffold_writes_valid_planstate_frontmatter(tmp_path):
    path = tmp_path / "PLAN.md"

    record = plan.scaffold(path, "helix")

    assert path.exists()
    fm, body = read_doc(path)
    # Deterministic metadata is a valid PlanState — and not yet a contract.
    parsed = PlanState.model_validate(fm)
    assert parsed.project == "helix"
    assert parsed.id
    assert "agreed_at" not in fm
    # The body carries the sections the worker/human fills in.
    assert "## Intent" in body
    assert record.agreed_at is None


def test_scaffold_preserves_an_existing_draft(tmp_path):
    path = tmp_path / "PLAN.md"
    first = plan.scaffold(path, "helix")
    # Simulate co-authoring: the worker rewrote the body.
    fm, _ = read_doc(path)
    from helix.state import write_doc

    write_doc(path, fm, "# Plan\n\n## Intent\n\nBuild the widget.\n")

    again = plan.scaffold(path, "helix")

    # Same id (not regenerated) and the drafted body is untouched.
    assert again.id == first.id
    _, body = read_doc(path)
    assert "Build the widget." in body


def test_seal_stamps_agreed_at(tmp_path):
    path = tmp_path / "PLAN.md"
    plan.scaffold(path, "helix")

    record = plan.seal(path, now=datetime(2026, 7, 1, 12, 0, 0))

    assert record.agreed_at is not None
    fm, _ = read_doc(path)
    assert "agreed_at" in fm
    PlanState.model_validate(fm)  # still a valid record


def _coauthoring_worker(text):
    # A fake worker that writes judgment-laden prose into PLAN.md (cwd=repo) and
    # ignores the opening prompt passed as argv.
    return ["sh", "-c", f'printf "\\n## Intent\\n\\n{text}\\n" >> PLAN.md', "x"]


def test_run_coauthors_and_seals_into_a_consumable_contract(tmp_path):
    config = _config(_coauthoring_worker("Build the widget."))
    sessions = tmp_path / "sessions"

    result = plan.run(
        config, tmp_path, sessions_dir=sessions, intent="A widget", agree=True
    )

    # The document is materialized, co-authored, and sealed.
    assert result.agreed
    fm, body = read_doc(result.plan_path)
    assert "Build the widget." in body
    assert "agreed_at" in fm
    PlanState.model_validate(fm)

    # A plan session records the handoff, with the composed prompt as evidence.
    sfm, _ = read_doc(result.session_dir / "session.md")
    assert sfm["phase"] == "plan"
    assert (result.session_dir / "evidence" / "prompt.txt").exists()

    # helix run consumes it unchanged: the plan body flows into the implement prompt.
    prompt = implement.compose_prompt(config, tmp_path, sessions)
    assert "Build the widget." in prompt


def test_run_without_agree_leaves_a_draft(tmp_path):
    config = _config(_coauthoring_worker("Draft only."))
    sessions = tmp_path / "sessions"

    result = plan.run(config, tmp_path, sessions_dir=sessions, agree=False)

    assert not result.agreed
    fm, _ = read_doc(result.plan_path)
    assert "agreed_at" not in fm


def test_run_chains_the_plan_session(tmp_path):
    config = _config(["true"])
    sessions = tmp_path / "sessions"

    result = plan.run(
        config,
        tmp_path,
        sessions_dir=sessions,
        predecessor="20260701T000000Z-seed",
        invoke_worker=True,
    )

    fm, _ = read_doc(result.session_dir / "session.md")
    assert fm["predecessor"] == "20260701T000000Z-seed"
