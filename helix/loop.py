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

from pathlib import Path


def run_loop(project: Path, max_iterations: int | None = None) -> None:
    """Drive implement->judge iterations until the oracle passes or a cap/gate halts.

    Raises ``NotImplementedError`` until the loop is built (bootstrap phase P1).
    """
    raise NotImplementedError("outer loop is a bootstrap target (P1)")
