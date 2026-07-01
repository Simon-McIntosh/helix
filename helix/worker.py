"""Native-worker adapter.

Contract (model-harness fit — non-negotiable)
---------------------------------------------
Helix invokes a *native* agent worker (e.g. a CLI agent) in a fresh context and
lets it use its own native tool surface, skills, and edit format. Helix MUST
NOT reimplement, wrap, or translate the worker's tools: doing so breaks the
model-harness fit the worker was post-trained against and degrades performance.

This module's job is narrow: given a composed prompt and a working directory,
start a worker process with a clean context, stream/capture its output, and
return when it finishes. It sets the working context; it does not steer the
worker turn-by-turn.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def invoke(
    prompt: str,
    cwd: Path,
    *,
    command: list[str],
    timeout_s: int | None = None,
    env: dict[str, str] | None = None,
) -> str:
    """Run the native worker once with ``prompt`` in ``cwd`` and return its output.

    The composed prompt is fed to the worker on **stdin**; ``command`` is the
    worker's own argv. Helix does not steer the worker turn-by-turn and does not
    reimplement its tools — it starts a fresh process, hands it context, and
    captures what it produces.

    Returns the worker's stdout with any stderr appended, so the full trace is
    preserved as evidence. Raises ``FileNotFoundError`` if the worker binary is
    not found, and ``subprocess.TimeoutExpired`` if it exceeds ``timeout_s``.
    """
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=env,
    )
    parts = [proc.stdout or ""]
    if proc.stderr:
        parts.append(proc.stderr)
    return "".join(parts)


def converse(
    prompt: str,
    cwd: Path,
    *,
    command: list[str],
    env: dict[str, str] | None = None,
) -> int:
    """Launch the worker interactively with ``prompt`` as its opening message.

    Unlike :func:`invoke`, this hands the worker Helix's own stdin/stdout/stderr
    so a human is *in the seat* and can converse in the worker's native REPL —
    the mode the plan phase runs in. The composed prompt is passed as the final
    argv element (the opening message); ``command`` is the worker's own argv.

    Helix sets the working context and gets out of the way (model-harness fit):
    it does not steer the worker turn-by-turn and does not reimplement its tools.

    Returns the worker's exit code. Raises ``FileNotFoundError`` if the worker
    binary is not found.
    """
    proc = subprocess.run([*command, prompt], cwd=str(cwd), env=env)
    return proc.returncode
