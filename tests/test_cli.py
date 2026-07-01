"""Tests for the CLI surface.

The CLI is a thin skin over the loop: it maps ``helix run`` to the loop and
turns the verdict into an exit code (pass -> 0, fail/exhausted -> 1, blocked ->
2), so shell orchestration and CI can act on the result.
"""

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
