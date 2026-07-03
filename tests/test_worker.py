"""Tests for the native-worker adapter.

worker.invoke sets context and runs a worker process — it must not reimplement
the worker's tools. These tests use trivial stand-in commands (cat, sh) as the
"worker" to pin the process contract: prompt on stdin, run in cwd, output back.
"""

import pytest

from helix.worker import build_command, converse, invoke


def test_invoke_feeds_prompt_on_stdin_and_returns_output(tmp_path):
    out = invoke("hello\nworld", cwd=tmp_path, command=["cat"]).output
    assert "hello" in out
    assert "world" in out


def test_invoke_runs_in_cwd(tmp_path):
    (tmp_path / "note.txt").write_text("from-the-repo")
    out = invoke("ignored", cwd=tmp_path, command=["cat", "note.txt"]).output
    assert "from-the-repo" in out


def test_invoke_captures_stderr_as_evidence(tmp_path):
    out = invoke("x", cwd=tmp_path, command=["sh", "-c", "echo oops 1>&2"]).output
    assert "oops" in out


def test_invoke_missing_command_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        invoke("x", cwd=tmp_path, command=["helix-no-such-worker-binary"])


def test_converse_passes_prompt_as_opening_argv_and_runs_in_cwd(tmp_path):
    # The interactive human's-seat entry: prompt handed as the final argv element.
    rc = converse(
        "the-opening-message",
        cwd=tmp_path,
        command=["sh", "-c", 'printf "%s" "$1" > seen.txt', "x"],
    )
    assert rc == 0
    assert (tmp_path / "seen.txt").read_text() == "the-opening-message"


def test_converse_returns_worker_exit_code(tmp_path):
    assert converse("x", cwd=tmp_path, command=["sh", "-c", "exit 3", "x"]) == 3


def test_invoke_streams_to_sink_file_live(tmp_path):
    sink = tmp_path / "stream.txt"
    out = invoke(
        "ignored",
        cwd=tmp_path,
        command=["sh", "-c", "printf 'a\\nb\\nc\\n'"],
        sink=sink,
    )
    # The sink captured the stream as it arrived, matching the returned output.
    assert sink.read_text() == "a\nb\nc\n"
    assert out.output == "a\nb\nc\n"


def test_invoke_reports_the_worker_exit_code(tmp_path):
    assert invoke("x", cwd=tmp_path, command=["sh", "-c", "exit 0"]).returncode == 0
    assert invoke("x", cwd=tmp_path, command=["sh", "-c", "exit 7"]).returncode == 7


def test_build_command_routes_model_and_resume():
    base = ["claude", "-p"]
    assert build_command(base) == base
    assert build_command(base, model="haiku") == ["claude", "-p", "--model", "haiku"]
    assert build_command(base, resume=True) == ["claude", "-p", "--continue"]
    assert build_command(
        base, model="sonnet", model_flag="-m", resume=True, resume_args=["-c"]
    ) == ["claude", "-p", "-m", "sonnet", "-c"]
    # The base argv is never mutated.
    assert base == ["claude", "-p"]


def test_invoke_calls_on_line_per_line(tmp_path):
    seen = []
    invoke(
        "ignored",
        cwd=tmp_path,
        command=["sh", "-c", "printf 'one\\ntwo\\n'"],
        on_line=seen.append,
    )
    assert seen == ["one", "two"]


def test_invoke_times_out(tmp_path):
    import subprocess

    with pytest.raises(subprocess.TimeoutExpired):
        invoke("x", cwd=tmp_path, command=["sh", "-c", "sleep 5"], timeout_s=1)
