"""The tiered completion oracle.

Contract
--------
"Done" is decided by evidence against criteria, not by vibes. The oracle is
tiered:

* **surrogate** gates are fast, cheap checks (tests, linters, reference diffs)
  run every iteration as backpressure. A worker without verification is just a
  text generator with file permissions.
* **blocking** gates are slow or physical-experiment checks. When one is
  reached the loop *blocks and waits* for human-supplied ground truth rather
  than guessing. This is what lets Helix run autonomously against simulation
  while correctly pausing for real experiments.

Gate definitions are project data (see ``projects/``), not core logic.
"""

from __future__ import annotations

from pathlib import Path


def evaluate_surrogates(project: Path) -> bool:
    """Run all surrogate-tier gates and return whether they all pass.

    Raises ``NotImplementedError`` until the oracle is built (bootstrap phase P1).
    """
    raise NotImplementedError("oracle is a bootstrap target (P1)")
