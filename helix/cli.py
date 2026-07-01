"""Command-line entry point for Helix.

The CLI is a thin surface over the outer loop. Each subcommand maps to a phase
or to a loop control action. The CLI holds no model judgment — it composes
inputs from files, invokes the worker, and writes state back to disk.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from helix.loop import run_loop

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
) -> None:
    """Interactive planning phase: co-author the agreed plan (the signed contract)."""
    console.print(f"helix plan {project}: {_NOT_YET}")
    raise typer.Exit(code=1)


# verdict -> process exit code, so shells and CI can branch on the outcome.
_EXIT_CODE = {"pass": 0, "blocked": 2}
_VERDICT_STYLE = {"pass": "green", "blocked": "yellow"}


@app.command()
def run(
    project: str = typer.Argument(..., help="Project directory to run the loop in."),
    max_iterations: int = typer.Option(
        0, help="Iteration cap (0 = use project config)."
    ),
) -> None:
    """Autonomous loop: iterate implement->judge until the oracle is satisfied."""
    result = run_loop(Path(project), max_iterations or None)
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


@app.command()
def status(project: str = typer.Argument(..., help="Project directory.")) -> None:
    """Show campaign state: latest session, chain, open gates, recent findings."""
    console.print(f"helix status {project}: {_NOT_YET}")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
