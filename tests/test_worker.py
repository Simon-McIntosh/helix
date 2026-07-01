"""Tests for the native-worker adapter.

worker.invoke sets context and runs a worker process — it must not reimplement
the worker's tools. These tests use trivial stand-in commands (cat, sh) as the
"worker" to pin the process contract: prompt on stdin, run in cwd, output back.
"""

import pytest

from helix.worker import invoke


def test_invoke_feeds_prompt_on_stdin_and_returns_output(tmp_path):
    out = invoke("hello\nworld", cwd=tmp_path, command=["cat"])
    assert "hello" in out
    assert "world" in out


def test_invoke_runs_in_cwd(tmp_path):
    (tmp_path / "note.txt").write_text("from-the-repo")
    out = invoke("ignored", cwd=tmp_path, command=["cat", "note.txt"])
    assert "from-the-repo" in out


def test_invoke_captures_stderr_as_evidence(tmp_path):
    out = invoke("x", cwd=tmp_path, command=["sh", "-c", "echo oops 1>&2"])
    assert "oops" in out


def test_invoke_missing_command_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        invoke("x", cwd=tmp_path, command=["helix-no-such-worker-binary"])
