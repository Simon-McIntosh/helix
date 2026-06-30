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

from pathlib import Path


def invoke(prompt: str, cwd: Path, *, timeout_s: int | None = None) -> str:
    """Run the native worker once with ``prompt`` in ``cwd`` and return its output.

    Raises ``NotImplementedError`` until the adapter is built (bootstrap phase P1).
    """
    raise NotImplementedError("worker adapter is a bootstrap target (P1)")
