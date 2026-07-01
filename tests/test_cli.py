"""Tests for the CLI surface.

The CLI is a thin skin over the loop: it maps ``helix run`` to the loop and
turns the verdict into an exit code (pass -> 0, fail/exhausted -> 1, blocked ->
2), so shell orchestration and CI can act on the result.
"""

import yaml
from typer.testing import CliRunner

from helix.cli import app

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
