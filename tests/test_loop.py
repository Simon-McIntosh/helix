"""End-to-end tests for the dumb outer loop.

These drive a full ``implement -> judge`` loop against a synthetic project with a
stand-in worker. They are the honest P1 signal: an autonomous loop makes a
verified increment (or halts on fail/cap/gate) with no human in the inner loop.
"""

import yaml

from helix.loop import run_loop


def _project(tmp_path, worker_command, gates, max_iterations=5, repo="."):
    (tmp_path / "helix.yaml").write_text(
        yaml.safe_dump(
            {
                "repo": repo,
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


def test_loop_passes_when_worker_makes_the_gate_green(tmp_path):
    # Worker creates the marker the gate checks -> pass on the first iteration.
    project = _project(
        tmp_path,
        ["sh", "-c", "cat >/dev/null; : > done.txt"],
        _DONE_GATE,
    )

    result = run_loop(project)

    assert result.verdict == "pass"
    assert result.iterations == 1
    # One implement + one judge session were persisted.
    assert len(result.sessions) == 2
    for sid in result.sessions:
        assert (project / "sessions" / sid / "session.md").exists()


def test_loop_exhausts_the_cap_when_gate_never_greens(tmp_path):
    # Worker does nothing; gate can never pass -> loop runs to the cap.
    project = _project(tmp_path, ["true"], _DONE_GATE, max_iterations=3)

    result = run_loop(project)

    assert result.verdict == "exhausted"
    assert result.iterations == 3
    assert len(result.sessions) == 6  # 3 implement + 3 judge


def test_loop_blocks_on_a_blocking_gate(tmp_path):
    gates = [
        {
            "id": "s",
            "name": "surrogate",
            "tier": "surrogate",
            "criterion": "always ok",
            "command": "true",
        },
        {
            "id": "phys",
            "name": "physical experiment",
            "tier": "blocking",
            "criterion": "human confirms on hardware",
        },
    ]
    project = _project(tmp_path, ["true"], gates)

    result = run_loop(project)

    assert result.verdict == "blocked"
    assert result.iterations == 1


def test_loop_max_iterations_argument_overrides_config(tmp_path):
    project = _project(tmp_path, ["true"], _DONE_GATE, max_iterations=99)

    result = run_loop(project, max_iterations=2)

    assert result.iterations == 2


def test_loop_chains_sessions_through_predecessors(tmp_path):
    from helix.state import read_doc

    project = _project(tmp_path, ["true"], _DONE_GATE, max_iterations=2)

    result = run_loop(project)

    # Every session after the first names its immediate predecessor.
    predecessors = []
    for sid in result.sessions:
        fm, _ = read_doc(project / "sessions" / sid / "session.md")
        predecessors.append(fm.get("predecessor"))
    assert predecessors[0] is None
    assert predecessors[1:] == result.sessions[:-1]
