"""Command-line entry point for Helix.

The CLI is a thin surface over the outer loop. Each subcommand maps to a phase
or to a loop control action. The CLI holds no model judgment — it composes
inputs from files, invokes the worker, and writes state back to disk.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape as esc

from helix import observe, session
from helix.config import load_config
from helix.loop import SESSIONS_DIRNAME, run_loop
from helix.phases import plan as plan_phase

app = typer.Typer(
    name="helix",
    help="A dumb plan-implement-judge loop around a smart native worker.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

_NOT_YET = "[yellow]not yet implemented[/] — scaffolded target for the bootstrap loop"


@app.command()
def plan(
    project: str = typer.Argument(..., help="Project directory to plan in."),
    intent: str = typer.Option(
        "", help="Starting intent handed to the worker as the opening context."
    ),
    agree: bool = typer.Option(
        False,
        "--agree/--draft",
        help="Seal the plan as the signed contract (stamp agreed_at).",
    ),
    out: str = typer.Option(
        "", help="Where to write the plan (default: the project's configured plan)."
    ),
    no_worker: bool = typer.Option(
        False, "--no-worker", help="Scaffold/seal only; do not launch the worker."
    ),
) -> None:
    """Interactive planning phase: co-author the agreed plan (the signed contract).

    Materializes a ``PlanState``-shaped document (deterministic metadata written
    by the tool; judgment-laden body co-authored by the worker and human) that
    ``helix run`` consumes unchanged.
    """
    root = Path(project)
    try:
        config = load_config(root)
        result = plan_phase.run(
            config,
            root,
            sessions_dir=root / SESSIONS_DIRNAME,
            intent=intent or None,
            agree=agree,
            out=Path(out) if out else None,
            invoke_worker=not no_worker,
        )
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    state = "agreed" if result.agreed else "draft"
    style = "green" if result.agreed else "yellow"
    console.print(
        f"[{style}]plan {state}[/] -> {result.plan_path} (session {result.id})"
    )


# verdict -> process exit code, so shells and CI can branch on the outcome.
_EXIT_CODE = {"pass": 0, "blocked": 2}
_VERDICT_STYLE = {"pass": "green", "blocked": "yellow"}


def _stream_observer():
    """A worker-line observer that renders the live train-of-thought to console."""

    def observe_line(line: str) -> None:
        rendered = observe.render_line(line)
        if rendered is not None:
            console.print(rendered, highlight=False, soft_wrap=True)

    return observe_line


@app.command()
def run(
    project: str = typer.Argument(..., help="Project directory to run the loop in."),
    max_iterations: int = typer.Option(
        0, help="Iteration cap (0 = use project config)."
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--quiet",
        help="Render the worker's live train-of-thought as it runs.",
    ),
) -> None:
    """Autonomous loop: iterate implement->judge until the oracle is satisfied.

    With --stream (default) the worker's train-of-thought and actions render live
    as it works; the raw trace is also streamed to each session's
    evidence/worker.txt, so `tail -f` follows it from another shell.
    """
    observer = _stream_observer() if stream else None
    announce = (lambda msg: console.rule(f"[bold]{msg}[/bold]")) if stream else None
    result = run_loop(
        Path(project), max_iterations or None, observer=observer, announce=announce
    )
    style = _VERDICT_STYLE.get(result.verdict, "red")
    console.print(
        f"[{style}]{result.verdict}[/] after {result.iterations} iteration(s) "
        f"— {len(result.sessions)} session(s) written"
    )
    raise typer.Exit(code=_EXIT_CODE.get(result.verdict, 1))


@app.command()
def judge(session: str = typer.Argument(..., help="Session id to judge.")) -> None:
    """Independent judge phase: decide done/not-done from evidence vs the oracle."""
    console.print(f"helix judge {session}: {_NOT_YET}")
    raise typer.Exit(code=1)


_PHASE_MARK = {"plan": "◇", "implement": "●", "judge": "◆"}
_FINDINGS_SHOWN = 5


@app.command()
def status(project: str = typer.Argument(..., help="Project directory.")) -> None:
    """Show campaign state: the session chain, verdicts, gates, recent findings.

    Read-only: it walks the predecessor chain and renders what is on disk. It
    holds no model judgment and re-runs nothing.
    """
    root = Path(project)
    sessions_dir = root / SESSIONS_DIRNAME
    chain = session.walk_chain(sessions_dir)

    if not chain:
        console.print(f"[yellow]no sessions yet[/] in {sessions_dir}")
        raise typer.Exit(code=0)

    latest = chain[0]
    style = _VERDICT_STYLE.get(latest.verdict or "", "white")
    verdict = latest.verdict or "—"
    console.print(
        f"[bold]{root.name}[/bold] — {len(chain)} session(s) in chain · "
        f"latest verdict [{style}]{verdict}[/]"
    )

    console.print("\n[bold]Chain[/bold] (newest first):")
    for view in chain:
        mark = _PHASE_MARK.get(view.phase, "·")
        vstyle = _VERDICT_STYLE.get(view.verdict or "", "white")
        vtag = f" [{vstyle}]{esc(view.verdict)}[/]" if view.verdict else ""
        summary = esc((view.summary or "").strip())
        console.print(
            f"  {mark} [dim]{esc(view.id)}[/dim] {esc(view.phase)}{vtag} — {summary}"
        )

    try:
        config = load_config(root)
        if config.gates:
            console.print("\n[bold]Gates[/bold]:")
            for gate in config.gates:
                tier, gid, crit = esc(gate.tier), esc(gate.id), esc(gate.criterion)
                console.print(f"  [dim]{tier}[/dim] {gid} — {crit}")
    except FileNotFoundError:
        pass

    findings = [f for view in chain for f in session.read_findings(view.dir)]
    if findings:
        console.print("\n[bold]Recent findings[/bold] (age-/condition-stamped):")
        for f in findings[:_FINDINGS_SHOWN]:
            when = esc(str(f.get("observed_at", "?")))
            cond = f.get("conditions")
            tail = f" [dim]({esc(cond)})[/dim]" if cond else ""
            console.print(
                f"  • {esc(f.get('statement', ''))} [dim]@ {when}[/dim]{tail}"
            )

    raise typer.Exit(code=0)


@app.command()
def watch(
    project: str = typer.Argument(..., help="Project directory."),
    session_id: str = typer.Option(
        "", "--session", help="Session id to replay (default: the latest)."
    ),
) -> None:
    """Replay a session's worker trace as a rendered train-of-thought.

    For a *live* follow while a run is in progress, `tail -f` the session's
    evidence/worker.txt directly; this command renders a captured trace legibly.
    """
    root = Path(project)
    sessions_dir = root / SESSIONS_DIRNAME
    views = session.iter_sessions(sessions_dir)
    if session_id:
        views = [v for v in views if v.id == session_id]
    else:
        views = [v for v in reversed(views) if v.phase == "implement"][:1]

    if not views:
        console.print("[yellow]no matching session with a worker trace[/]")
        raise typer.Exit(code=1)

    view = views[0]
    trace = view.dir / "evidence" / "worker.txt"
    if not trace.exists():
        console.print(f"[yellow]no worker trace at[/] {trace}")
        raise typer.Exit(code=1)

    console.rule(f"[bold]{view.id}[/bold]")
    for rendered in observe.render_stream(trace.read_text().splitlines()):
        console.print(rendered, highlight=False, soft_wrap=True)
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
