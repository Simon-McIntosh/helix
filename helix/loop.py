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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from helix import oracle
from helix.config import load_config
from helix.phases import implement, judge

SESSIONS_DIRNAME = "sessions"
EXHAUSTED = "exhausted"


@dataclass
class LoopResult:
    """The outcome of a loop run: how it halted, after how many iterations."""

    verdict: str  # "pass" | "blocked" | "exhausted"
    iterations: int
    sessions: list[str] = field(default_factory=list)


def run_loop(project: Path, max_iterations: int | None = None) -> LoopResult:
    """Drive implement->judge iterations until the oracle passes or a cap/gate halts.

    Each iteration is a fresh restart: the implement phase invokes the worker and
    writes disk; the judge phase (a separate invocation — never the worker) runs
    the surrogate oracle and writes its verdict. Sessions chain through their
    predecessor. The loop carries no accumulating conversation and holds no model
    judgment — it composes, invokes, evaluates, and persists.

    Halts on:
    * ``pass`` — the surrogate oracle is satisfied; the increment is verified.
    * ``blocked`` — a blocking-tier gate needs human ground truth.
    * ``exhausted`` — the iteration cap was reached without a pass.
    """
    project = Path(project)
    config = load_config(project)
    cap = max_iterations or config.caps.max_iterations
    sessions_dir = project / SESSIONS_DIRNAME

    last_id: str | None = None
    sessions: list[str] = []

    for i in range(cap):
        impl = implement.run(
            config,
            project,
            sessions_dir=sessions_dir,
            slug=f"{i:02d}-implement",
            predecessor=last_id,
        )
        last_id = impl.id
        sessions.append(impl.id)

        verdict = judge.run(
            config,
            project,
            sessions_dir=sessions_dir,
            slug=f"{i:02d}-judge",
            predecessor=last_id,
        )
        last_id = verdict.id
        sessions.append(verdict.id)

        if verdict.verdict in (oracle.PASS, oracle.BLOCKED):
            return LoopResult(verdict.verdict, i + 1, sessions)

    return LoopResult(EXHAUSTED, cap, sessions)
