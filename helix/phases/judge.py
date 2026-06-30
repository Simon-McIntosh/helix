"""Judge phase — independent verdict.

The judge is always a separate invocation from the worker, with a fresh context,
so a worker can never declare its own work complete. The judge reads the plan,
the evidence, and the oracle gates, and returns a verdict: pass, fail, or
blocked (awaiting human ground truth for a blocking-tier gate).
"""

from __future__ import annotations

from pathlib import Path


def run(session_dir: Path) -> str:
    """Return a verdict ('pass' | 'fail' | 'blocked') for the session's evidence.

    Raises ``NotImplementedError`` until the judge phase is built (P1).
    """
    raise NotImplementedError("judge phase is a bootstrap target (P1)")
