"""Mechanical run-progress arithmetic and plain rendering.

The loop reports a :class:`Snapshot` after each iteration — box counts from the
plan's Tasks section, the iteration position, and elapsed wall-clock. Everything
derived here is arithmetic: the ETA is average-time-per-task-completed-this-run
times the tasks remaining, not an estimate anyone reasoned about. The CLI owns
colour; this module renders plain strings so it stays terminal-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass

_BAR_WIDTH = 24


@dataclass(frozen=True)
class Snapshot:
    """One mechanical reading of run progress, taken after an iteration."""

    tasks_done: int
    tasks_total: int
    iteration: int
    cap: int
    elapsed_s: float
    # Boxes already checked when the run started — the ETA rate is based only
    # on tasks completed *this* run, so a resumed campaign doesn't skew it.
    tasks_done_start: int = 0

    @property
    def eta_s(self) -> float | None:
        """Seconds remaining at this run's pace, or ``None`` before any signal."""
        completed = self.tasks_done - self.tasks_done_start
        remaining = self.tasks_total - self.tasks_done
        if completed <= 0 or remaining <= 0:
            return None
        return self.elapsed_s / completed * remaining


def bar(done: int, total: int, width: int = _BAR_WIDTH) -> str:
    """A textual progress bar, full-width even when the plan has no tasks."""
    if total <= 0:
        return "░" * width
    filled = round(width * min(done, total) / total)
    return "█" * filled + "░" * (width - filled)


def fmt_duration(seconds: float) -> str:
    """Compact human duration: ``42s``, ``4m10s``, ``1h03m``."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def describe(snap: Snapshot) -> str:
    """One status line: tasks bar, iteration, elapsed, and the mechanical ETA."""
    if snap.tasks_total > 0:
        pct = round(100 * snap.tasks_done / snap.tasks_total)
        tasks = f"tasks {snap.tasks_done}/{snap.tasks_total} {pct:3d}%"
    else:
        tasks = "tasks —"
    eta = fmt_duration(snap.eta_s) if snap.eta_s is not None else "—"
    return (
        f"{bar(snap.tasks_done, snap.tasks_total)} {tasks}"
        f" · iter {snap.iteration}/{snap.cap}"
        f" · elapsed {fmt_duration(snap.elapsed_s)} · eta {eta}"
    )
