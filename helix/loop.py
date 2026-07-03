"""The dumb outer loop.

Contract
--------
The loop contains NO model judgment. Its only responsibilities are:

1. Compose a phase prompt from files (base prompt + project overlay + state).
2. Invoke the native worker in a fresh context (see :mod:`helix.worker`).
3. Run the tiered oracle (see :mod:`helix.oracle`) as backpressure.
4. Enforce caps (max iterations, wall-clock, token budget) and gates.
5. Persist session state to disk (see :mod:`helix.session`, :mod:`helix.state`).

Each iteration is a fresh restart that reads disk, makes bounded progress, and
writes disk. The loop never carries an accumulating conversation across
iterations, and it never lets the worker declare its own work complete — that
verdict belongs to a separate judge invocation.

Robustness: a worker invocation cut off mid-flight (token/usage limit, crash,
kill) halts the loop with verdict ``interrupted`` rather than judging half-done
work. The disk is the state, so resuming costs nothing — ``resume=True`` seeds
the chain from the latest session and hands the first worker invocation its
native continue flag so the cut conversation picks up where it stopped.
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from helix import observe, oracle, session, tasks, worker
from helix.config import Config, load_config
from helix.phases import implement, judge
from helix.progress import Snapshot

SESSIONS_DIRNAME = "sessions"
EXHAUSTED = "exhausted"
INTERRUPTED = "interrupted"


@dataclass
class LoopResult:
    """The outcome of a loop run: how it halted, after how many iterations."""

    verdict: str  # "pass" | "blocked" | "exhausted" | "interrupted"
    iterations: int
    sessions: list[str] = field(default_factory=list)
    reason: str | None = None  # one-line hint when the run was interrupted


def _plan_tasks(config: Config, project: Path) -> list[tasks.Task]:
    """The plan's checkbox tasks — the loop's whole progress model."""
    if not config.plan:
        return []
    return tasks.read_tasks(project / config.plan)


def _worker_model(
    override: str | None, items: list[tasks.Task], config: Config
) -> str | None:
    """Resolve the model for the next invocation: CLI > task annotation > config."""
    if override:
        return override
    nxt = tasks.next_task(items)
    if nxt is not None and nxt.model:
        return nxt.model
    return config.worker.model


def run_loop(
    project: Path,
    max_iterations: int | None = None,
    *,
    observer: Callable[[str], None] | None = None,
    announce: Callable[[str], None] | None = None,
    on_progress: Callable[[Snapshot], None] | None = None,
    model: str | None = None,
    resume: bool = False,
) -> LoopResult:
    """Drive implement->judge iterations until the oracle passes or a cap/gate halts.

    Each iteration is a fresh restart: the implement phase invokes the worker and
    writes disk; the judge phase (a separate invocation — never the worker) runs
    the surrogate oracle and writes its verdict. Sessions chain through their
    predecessor — across runs too: a new run continues the campaign thread from
    the latest session on disk. The loop carries no accumulating conversation
    and holds no model judgment — it composes, invokes, evaluates, and persists.

    ``model`` overrides the worker model for every iteration; otherwise the next
    open task's ``(model: …)`` annotation, then the config's worker model, route
    it. ``on_progress`` receives a mechanical :class:`~helix.progress.Snapshot`
    after each iteration. ``resume=True`` hands the *first* worker invocation
    the worker's native continue flag so an interrupted conversation resumes.

    Halts on:
    * ``pass`` — the surrogate oracle is satisfied; the increment is verified.
    * ``blocked`` — a blocking-tier gate needs human ground truth.
    * ``interrupted`` — the worker was cut off (token/usage limit, crash); the
      run is resumable from disk with ``resume=True``.
    * ``exhausted`` — the iteration cap was reached without a pass.
    """
    project = Path(project)
    config = load_config(project)
    cap = max_iterations or config.caps.max_iterations
    sessions_dir = project / SESSIONS_DIRNAME
    started = time.monotonic()

    # Continue the campaign thread across runs: the newest session on disk is
    # the predecessor of this run's first session.
    prior = session.iter_sessions(sessions_dir)
    last_id: str | None = prior[-1].id if prior else None
    sessions: list[str] = []

    done_start, _ = tasks.progress(_plan_tasks(config, project))

    def snapshot(iteration: int) -> Snapshot:
        done, total = tasks.progress(_plan_tasks(config, project))
        return Snapshot(
            tasks_done=done,
            tasks_total=total,
            iteration=iteration,
            cap=cap,
            elapsed_s=time.monotonic() - started,
            tasks_done_start=done_start,
        )

    for i in range(cap):
        items = _plan_tasks(config, project)
        command = worker.build_command(
            config.worker.command,
            model=_worker_model(model, items, config),
            model_flag=config.worker.model_flag,
            resume=resume and i == 0,
            resume_args=config.worker.resume_args,
        )
        if announce is not None:
            announce(f"iteration {i + 1}/{cap} — implement")
        try:
            impl = implement.run(
                config,
                project,
                sessions_dir=sessions_dir,
                slug=f"{i:02d}-implement",
                predecessor=last_id,
                observer=observer,
                command=command,
            )
        except subprocess.TimeoutExpired:
            # The worker overran its wall-clock cap — same halt as any other
            # cut: resumable, never judged.
            reason = f"worker timeout after {config.worker.timeout_s}s"
            return LoopResult(INTERRUPTED, i + 1, sessions, reason=reason)
        except KeyboardInterrupt:
            return LoopResult(INTERRUPTED, i + 1, sessions, reason="interrupted (^C)")
        last_id = impl.id
        sessions.append(impl.id)

        if observe.classify_trace(impl.output, impl.returncode) == observe.INTERRUPTED:
            reason = observe.halt_reason(impl.output)
            if announce is not None:
                announce(f"iteration {i + 1}/{cap} — worker interrupted")
            return LoopResult(INTERRUPTED, i + 1, sessions, reason=reason)

        verdict = judge.run(
            config,
            project,
            sessions_dir=sessions_dir,
            slug=f"{i:02d}-judge",
            predecessor=last_id,
        )
        last_id = verdict.id
        sessions.append(verdict.id)
        if announce is not None:
            announce(f"iteration {i + 1}/{cap} — judge verdict: {verdict.verdict}")
        if on_progress is not None:
            on_progress(snapshot(i + 1))

        if verdict.verdict in (oracle.PASS, oracle.BLOCKED):
            return LoopResult(verdict.verdict, i + 1, sessions)

    return LoopResult(EXHAUSTED, cap, sessions)
