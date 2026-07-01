"""Judge phase — independent verdict.

The judge is always a separate invocation from the worker, with a fresh context,
so a worker can never declare its own work complete. It reads the oracle gates
(the agreed criteria) and the evidence on disk, then returns a verdict: pass,
fail, or blocked (awaiting human ground truth for a blocking-tier gate).

In this bootstrap tier the verdict is decided *mechanically* by the surrogate
oracle — evidence against criteria, no model judgment. That is the purest form
of "the loop holds no judgment": the test suite is the judge.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from helix import oracle, session
from helix.config import Config


@dataclass
class JudgeResult:
    """The verdict of one judge invocation and where it was recorded."""

    id: str
    verdict: str
    session_dir: Path


def _gates_evidence(result: oracle.OracleResult) -> str:
    lines = []
    for o in result.outcomes:
        status = "PASS" if o.passed else "FAIL"
        lines.append(f"## [{o.tier}] {o.id} — {status}\n{o.output}".rstrip())
    return "\n\n".join(lines) + "\n"


def _finding_statement(result: oracle.OracleResult) -> str:
    gate_ids = ", ".join(o.id for o in result.outcomes) or "(none)"
    return (
        f"Surrogate oracle verdict `{result.verdict}` over gates [{gate_ids}], "
        f"decided from evidence against criteria."
    )


def run(
    config: Config,
    project: Path,
    *,
    sessions_dir: Path,
    slug: str,
    predecessor: str | None = None,
    now: datetime | None = None,
) -> JudgeResult:
    """Evaluate the oracle over the repo and persist a judge session."""
    project = Path(project)
    sessions_dir = Path(sessions_dir)
    repo = (project / config.repo).resolve()
    observed_at = now or datetime.now(UTC)

    result = oracle.evaluate(config.gates, cwd=repo)

    summary = f"Verdict `{result.verdict}` over {len(result.outcomes)} gate(s)."
    body = (
        f"# judge session\n\nIndependent evaluation of the surrogate oracle in "
        f"`{repo}`. Verdict: **{result.verdict}**. See `evidence/gates.txt`."
    )
    session_id, session_dir = session.write_session(
        sessions_dir,
        phase="judge",
        slug=slug,
        now=now,
        predecessor=predecessor,
        verdict=result.verdict,
        summary=summary,
        body=body,
    )
    (session_dir / "evidence" / "gates.txt").write_text(_gates_evidence(result))
    gate_ids = ", ".join(o.id for o in result.outcomes) or "(none)"
    session.record_findings(
        session_dir,
        [_finding_statement(result)],
        session_id=session_id,
        observed_at=observed_at,
        conditions=f"repo={repo}; gates=[{gate_ids}]",
    )
    return JudgeResult(id=session_id, verdict=result.verdict, session_dir=session_dir)
