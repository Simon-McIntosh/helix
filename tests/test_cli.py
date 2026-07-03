"""Tests for the CLI surface.

The CLI is a thin skin over the loop: it maps ``helix run`` to the loop and
turns the verdict into an exit code (pass -> 0, fail/exhausted -> 1, blocked ->
2), so shell orchestration and CI can act on the result.
"""

import json

import yaml
from typer.testing import CliRunner

from helix.cli import app
from helix.state import read_doc

runner = CliRunner()


def _project(tmp_path, worker_command, gates, max_iterations=3):
    (tmp_path / "helix.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": ".",
                "worker": {"command": worker_command},
                "caps": {"max_iterations": max_iterations},
                "gates": gates,
            }
        )
    )
    return tmp_path


_DONE_GATE = [
    {
        "id": "done",
        "name": "done marker",
        "tier": "surrogate",
        "criterion": "done.txt exists",
        "command": "test -f done.txt",
    }
]


def test_run_exits_zero_on_pass(tmp_path):
    project = _project(
        tmp_path, ["sh", "-c", "cat >/dev/null; : > done.txt"], _DONE_GATE
    )
    result = runner.invoke(app, ["run", str(project)])
    assert result.exit_code == 0
    assert "pass" in result.stdout


def test_run_exits_one_when_cap_is_exhausted(tmp_path):
    project = _project(tmp_path, ["true"], _DONE_GATE, max_iterations=2)
    result = runner.invoke(app, ["run", str(project)])
    assert result.exit_code == 1
    assert "exhausted" in result.stdout


def _plan_project(tmp_path, worker_command):
    (tmp_path / "helix.yaml").write_text(
        yaml.safe_dump(
            {"repo": ".", "plan": "PLAN.md", "worker": {"command": worker_command}}
        )
    )
    return tmp_path


def test_plan_materializes_and_seals_the_contract(tmp_path):
    worker = ["sh", "-c", 'printf "\\n## Intent\\n\\nDo X.\\n" >> PLAN.md', "x"]
    project = _plan_project(tmp_path, worker)

    result = runner.invoke(app, ["plan", str(project), "--intent", "do X", "--agree"])

    assert result.exit_code == 0
    assert "agreed" in result.stdout
    fm, body = read_doc(project / "PLAN.md")
    assert "agreed_at" in fm
    assert "Do X." in body


def test_plan_draft_leaves_contract_unsealed(tmp_path):
    project = _plan_project(tmp_path, ["true"])

    result = runner.invoke(app, ["plan", str(project), "--draft", "--no-worker"])

    assert result.exit_code == 0
    assert "draft" in result.stdout
    fm, _ = read_doc(project / "PLAN.md")
    assert "agreed_at" not in fm


# A worker that emits a stream-json assistant line (so the trace renders) and
# satisfies the done gate.
_ASSISTANT_LINE = json.dumps(
    {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "working on it"}]},
    }
)
_STREAMING_WORKER = [
    "sh",
    "-c",
    f"cat >/dev/null; printf '%s\\n' '{_ASSISTANT_LINE}'; : > done.txt",
]


def test_status_shows_chain_verdict_and_findings(tmp_path):
    project = _project(tmp_path, _STREAMING_WORKER, _DONE_GATE)
    assert runner.invoke(app, ["run", str(project), "--quiet"]).exit_code == 0

    result = runner.invoke(app, ["status", str(project)])

    assert result.exit_code == 0
    assert "session(s) in chain" in result.stdout
    assert "pass" in result.stdout  # latest verdict
    assert "implement" in result.stdout and "judge" in result.stdout
    assert "done" in result.stdout  # the configured gate id/criterion
    assert "Recent findings" in result.stdout


def test_status_no_sessions_is_graceful(tmp_path):
    project = _project(tmp_path, ["true"], _DONE_GATE)
    result = runner.invoke(app, ["status", str(project)])
    assert result.exit_code == 0
    assert "no sessions yet" in result.stdout


def test_run_stream_renders_train_of_thought(tmp_path):
    project = _project(tmp_path, _STREAMING_WORKER, _DONE_GATE)
    result = runner.invoke(app, ["run", str(project), "--stream"])
    assert result.exit_code == 0
    assert "working on it" in result.stdout  # rendered from the worker's stream


def test_watch_replays_a_session_trace(tmp_path):
    project = _project(tmp_path, _STREAMING_WORKER, _DONE_GATE)
    assert runner.invoke(app, ["run", str(project), "--quiet"]).exit_code == 0

    result = runner.invoke(app, ["watch", str(project)])
    assert result.exit_code == 0
    assert "working on it" in result.stdout


def test_run_exits_three_and_prints_resume_hint_when_interrupted(tmp_path):
    project = _project(
        tmp_path,
        ["sh", "-c", "cat >/dev/null; echo 'usage limit reached'; exit 1"],
        _DONE_GATE,
    )
    result = runner.invoke(app, ["run", str(project)])
    assert result.exit_code == 3
    assert "interrupted" in result.stdout
    assert "helix run" in result.stdout and "-c" in result.stdout


def test_run_renders_the_progress_line(tmp_path):
    check_off = (
        "cat >/dev/null; printf '## Tasks\\n\\n- [x] t\\n' > PLAN.md; : > done.txt"
    )
    project = _project(tmp_path, ["sh", "-c", check_off], _DONE_GATE)
    config = yaml.safe_load((project / "helix.yaml").read_text())
    config["plan"] = "PLAN.md"
    (project / "helix.yaml").write_text(yaml.safe_dump(config))
    (project / "PLAN.md").write_text("## Tasks\n\n- [ ] t\n")

    result = runner.invoke(app, ["run", str(project)])
    assert result.exit_code == 0
    assert "tasks 1/1" in result.stdout
    assert "iter 1/3" in result.stdout


def test_run_model_override_reaches_the_worker_argv(tmp_path):
    project = _project(
        tmp_path,
        ["sh", "-c", 'cat >/dev/null; printf "%s " "$@" > argv.txt; : > done.txt', "w"],
        _DONE_GATE,
    )
    result = runner.invoke(app, ["run", str(project), "--model", "haiku"])
    assert result.exit_code == 0
    assert (project / "argv.txt").read_text().split() == ["--model", "haiku"]


def test_check_reports_clean_and_drift(tmp_path):
    project = _project(tmp_path, ["true"], _DONE_GATE)
    result = runner.invoke(app, ["check", str(project)])
    assert result.exit_code == 0
    assert "clean" in result.stdout

    (project / "prompts").mkdir()
    (project / "prompts" / "judge.md").write_text("# forked judge\n")
    result = runner.invoke(app, ["check", str(project)])
    assert result.exit_code == 1
    assert "drift" in result.stdout and "forked core contract" in result.stdout
