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

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from helix.models import OracleGate

# Verdict values (mirror schema/helix.yaml's Verdict enum, kept as plain strings
# so the oracle has no import-time coupling to serialization concerns).
PASS = "pass"
FAIL = "fail"
BLOCKED = "blocked"


@dataclass
class GateOutcome:
    """The result of checking a single gate against the evidence."""

    id: str
    name: str
    tier: str
    passed: bool
    output: str = ""


@dataclass
class OracleResult:
    """The reduced verdict plus the per-gate outcomes that produced it."""

    verdict: str
    outcomes: list[GateOutcome] = field(default_factory=list)


def run_gate(
    gate: OracleGate, cwd: Path, *, timeout_s: int | None = None
) -> GateOutcome:
    """Run one surrogate gate's command in ``cwd`` and capture its outcome.

    A gate passes iff its command exits 0. A gate with no command cannot be
    evaluated mechanically and is reported as not passed (callers decide what an
    unrunnable gate means for the verdict).
    """
    if not gate.command:
        return GateOutcome(gate.id, gate.name, gate.tier, passed=False, output="")
    try:
        proc = subprocess.run(
            gate.command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return GateOutcome(
            gate.id, gate.name, gate.tier, passed=False, output=f"timeout: {exc}"
        )
    output = (proc.stdout or "") + (proc.stderr or "")
    return GateOutcome(
        gate.id, gate.name, gate.tier, passed=proc.returncode == 0, output=output
    )


def evaluate(
    gates: list[OracleGate], cwd: Path, *, timeout_s: int | None = None
) -> OracleResult:
    """Reduce the tiered gates to a single verdict.

    * Every ``surrogate`` gate is run in ``cwd``. If any fails, the verdict is
      ``fail`` — the next iteration has direction and should keep working.
    * If all surrogates pass but a ``blocking`` gate is present, the verdict is
      ``blocked``: progress is sound but a slow/physical gate needs human ground
      truth. Blocking gates are never auto-run.
    * If all surrogates pass and no blocking gate remains, the verdict is ``pass``.
    """
    surrogates = [g for g in gates if g.tier == "surrogate"]
    blocking = [g for g in gates if g.tier == "blocking"]

    outcomes = [run_gate(g, cwd, timeout_s=timeout_s) for g in surrogates]

    if any(not o.passed for o in outcomes):
        return OracleResult(FAIL, outcomes)
    if blocking:
        outcomes += [
            GateOutcome(
                g.id, g.name, g.tier, passed=False, output="awaiting ground truth"
            )
            for g in blocking
        ]
        return OracleResult(BLOCKED, outcomes)
    return OracleResult(PASS, outcomes)
