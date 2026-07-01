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
import threading
from collections.abc import Callable
from pathlib import Path


def _feed_stdin(stdin, prompt: str) -> None:
    """Write the prompt to the worker's stdin from a thread, then close it.

    Feeding from a separate thread while the main thread drains stdout avoids the
    classic pipe deadlock when the worker's output fills the buffer before it has
    consumed all of its input.
    """
    try:
        stdin.write(prompt)
    except (BrokenPipeError, ValueError):
        pass
    finally:
        try:
            stdin.close()
        except OSError:
            pass


def invoke(
    prompt: str,
    cwd: Path,
    *,
    command: list[str],
    timeout_s: int | None = None,
    env: dict[str, str] | None = None,
    sink: Path | None = None,
    on_line: Callable[[str], None] | None = None,
) -> str:
    """Run the native worker once with ``prompt`` in ``cwd`` and return its output.

    The composed prompt is fed to the worker on **stdin**; ``command`` is the
    worker's own argv. Helix does not steer the worker turn-by-turn and does not
    reimplement its tools — it starts a fresh process, hands it context, and
    captures what it produces.

    Output is streamed line by line as the worker produces it — not buffered
    until exit — so it is observable *live*:

    * ``sink`` — if given, each line is written and flushed to this file as it
      arrives, so a human can ``tail -f`` the worker's trace during a run.
    * ``on_line`` — if given, called with each line (newline stripped), so the
      caller can render a live train-of-thought (see :mod:`helix.observe`).

    stderr is merged into the stream so the full trace is preserved in one place.
    Returns the complete captured output. Raises ``FileNotFoundError`` if the
    worker binary is not found, and ``subprocess.TimeoutExpired`` if it exceeds
    ``timeout_s``.
    """
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    timed_out = threading.Event()
    timer: threading.Timer | None = None
    if timeout_s is not None:
        timer = threading.Timer(timeout_s, lambda: (timed_out.set(), proc.kill()))
        timer.start()

    feeder = threading.Thread(
        target=_feed_stdin, args=(proc.stdin, prompt), daemon=True
    )
    feeder.start()

    captured: list[str] = []
    sink_fh = open(sink, "w") if sink is not None else None
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            captured.append(line)
            if sink_fh is not None:
                sink_fh.write(line)
                sink_fh.flush()
            if on_line is not None:
                on_line(line.rstrip("\n"))
        proc.wait()
    finally:
        if timer is not None:
            timer.cancel()
        if sink_fh is not None:
            sink_fh.close()
        feeder.join(timeout=1)

    output = "".join(captured)
    if timed_out.is_set():
        raise subprocess.TimeoutExpired(command, timeout_s, output=output)
    return output


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
