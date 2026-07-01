"""Tests for the tiered completion oracle.

The oracle is the loop's backpressure: it runs surrogate-tier gate commands
every iteration and reduces the outcomes to a verdict. Blocking-tier gates are
never auto-run — their presence pauses the loop for human ground truth.
"""

from helix.models import OracleGate
from helix.oracle import evaluate


def _gate(gid, tier, command=None):
    return OracleGate(
        id=gid, name=gid, tier=tier, criterion=f"{gid} holds", command=command
    )


def test_all_surrogates_passing_yields_pass(tmp_path):
    gates = [_gate("a", "surrogate", "true"), _gate("b", "surrogate", "true")]
    result = evaluate(gates, cwd=tmp_path)
    assert result.verdict == "pass"
    assert all(o.passed for o in result.outcomes)


def test_a_failing_surrogate_yields_fail(tmp_path):
    gates = [_gate("a", "surrogate", "true"), _gate("b", "surrogate", "false")]
    result = evaluate(gates, cwd=tmp_path)
    assert result.verdict == "fail"
    failed = [o for o in result.outcomes if not o.passed]
    assert [o.id for o in failed] == ["b"]


def test_blocking_gate_with_passing_surrogates_yields_blocked(tmp_path):
    gates = [_gate("a", "surrogate", "true"), _gate("phys", "blocking")]
    result = evaluate(gates, cwd=tmp_path)
    assert result.verdict == "blocked"


def test_failing_surrogate_takes_priority_over_blocking(tmp_path):
    # A failing surrogate means iterate; don't prematurely block for a human.
    gates = [_gate("a", "surrogate", "false"), _gate("phys", "blocking")]
    result = evaluate(gates, cwd=tmp_path)
    assert result.verdict == "fail"


def test_no_gates_is_vacuously_pass(tmp_path):
    result = evaluate([], cwd=tmp_path)
    assert result.verdict == "pass"


def test_gate_runs_in_cwd_and_captures_output(tmp_path):
    (tmp_path / "marker").write_text("x")
    gates = [_gate("present", "surrogate", "ls marker && echo FOUND")]
    result = evaluate(gates, cwd=tmp_path)
    assert result.verdict == "pass"
    assert "FOUND" in result.outcomes[0].output
