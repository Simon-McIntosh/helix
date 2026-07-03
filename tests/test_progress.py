"""Tests for the mechanical progress arithmetic and rendering."""

from helix.progress import Snapshot, bar, describe, fmt_duration


def _snap(**overrides):
    base = dict(tasks_done=2, tasks_total=5, iteration=1, cap=8, elapsed_s=120.0)
    base.update(overrides)
    return Snapshot(**base)


def test_eta_is_pace_times_remaining():
    # 2 tasks in 120s -> 60s/task; 3 remaining -> 180s.
    assert _snap().eta_s == 180.0


def test_eta_uses_only_tasks_completed_this_run():
    # 1 box was already checked at start: 1 task in 120s, 3 remaining -> 360s.
    assert _snap(tasks_done_start=1).eta_s == 360.0


def test_eta_none_without_signal_or_remaining_work():
    assert _snap(tasks_done=0).eta_s is None  # nothing completed yet
    assert _snap(tasks_done=5).eta_s is None  # nothing remaining


def test_bar_fills_proportionally_and_handles_no_tasks():
    assert bar(0, 4, width=4) == "░░░░"
    assert bar(2, 4, width=4) == "██░░"
    assert bar(4, 4, width=4) == "████"
    assert bar(0, 0, width=4) == "░░░░"


def test_fmt_duration_scales_units():
    assert fmt_duration(42) == "42s"
    assert fmt_duration(250) == "4m10s"
    assert fmt_duration(3780) == "1h03m"


def test_describe_reads_as_one_status_line():
    line = describe(_snap())
    assert "tasks 2/5" in line and "40%" in line
    assert "iter 1/8" in line and "elapsed 2m00s" in line and "eta 3m00s" in line


def test_describe_without_tasks_shows_placeholder():
    line = describe(_snap(tasks_done=0, tasks_total=0))
    assert "tasks —" in line and "eta —" in line
