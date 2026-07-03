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


def test_loop_halts_interrupted_when_the_worker_is_cut(tmp_path):
    # A worker that dies (nonzero exit) must not be judged — the loop halts
    # resumably instead of iterating on half-done work.
    project = _project(
        tmp_path,
        ["sh", "-c", "cat >/dev/null; echo 'usage limit reached'; exit 1"],
        _DONE_GATE,
        max_iterations=4,
    )

    result = run_loop(project)

    assert result.verdict == "interrupted"
    assert result.iterations == 1
    assert len(result.sessions) == 1  # implement only, no judge
    assert "usage limit" in (result.reason or "")


def test_loop_routes_model_and_resume_flag_into_the_worker_argv(tmp_path):
    # The stand-in worker records its argv; build_command appends model routing
    # and (on resume) the continue flag after the base command.
    project = _project(
        tmp_path,
        ["sh", "-c", 'cat >/dev/null; printf "%s " "$@" > argv.txt; : > done.txt', "w"],
        _DONE_GATE,
    )
    config = yaml.safe_load((project / "helix.yaml").read_text())
    config["worker"]["model"] = "haiku"
    config["plan"] = "PLAN.md"
    (project / "helix.yaml").write_text(yaml.safe_dump(config))
    (project / "PLAN.md").write_text(
        "## Tasks\n\n- [ ] first open task (model: sonnet)\n"
    )

    result = run_loop(project, resume=True)

    assert result.verdict == "pass"
    argv = (project / "argv.txt").read_text().split()
    # Task annotation outranks the config default; resume flag present.
    assert argv == ["--model", "sonnet", "--continue"]


def test_loop_cli_model_override_outranks_the_task_annotation(tmp_path):
    project = _project(
        tmp_path,
        ["sh", "-c", 'cat >/dev/null; printf "%s " "$@" > argv.txt; : > done.txt', "w"],
        _DONE_GATE,
    )
    config = yaml.safe_load((project / "helix.yaml").read_text())
    config["plan"] = "PLAN.md"
    (project / "helix.yaml").write_text(yaml.safe_dump(config))
    (project / "PLAN.md").write_text("## Tasks\n\n- [ ] task (model: sonnet)\n")

    run_loop(project, model="opus")

    assert (project / "argv.txt").read_text().split() == ["--model", "opus"]


def test_loop_chains_a_new_run_onto_the_previous_campaign(tmp_path):
    from helix.session import walk_chain

    project = _project(
        tmp_path, ["sh", "-c", "cat >/dev/null; : > done.txt"], _DONE_GATE
    )

    first = run_loop(project)
    second = run_loop(project)

    chain = walk_chain(project / "sessions")
    ids = [v.id for v in chain]
    # The chain walks from the second run's judge all the way back through the
    # first run — one campaign thread, not two islands.
    assert ids == list(reversed(first.sessions + second.sessions))


def test_loop_reports_progress_snapshots(tmp_path):
    # The worker checks its task box; the snapshot after the iteration sees it.
    project = _project(
        tmp_path,
        ["sh", "-c", "cat >/dev/null; printf '## Tasks\\n\\n- [x] t\\n' > PLAN.md; : > done.txt"],
        _DONE_GATE,
    )
    config = yaml.safe_load((project / "helix.yaml").read_text())
    config["plan"] = "PLAN.md"
    (project / "helix.yaml").write_text(yaml.safe_dump(config))
    (project / "PLAN.md").write_text("## Tasks\n\n- [ ] t\n")

    seen = []
    result = run_loop(project, on_progress=seen.append)

    assert result.verdict == "pass"
    assert len(seen) == 1
    snap = seen[0]
    assert (snap.tasks_done, snap.tasks_total) == (1, 1)
    assert snap.tasks_done_start == 0
    assert snap.iteration == 1 and snap.cap == 5
    assert snap.elapsed_s >= 0
