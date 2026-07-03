"""Tests for machine-countable plan tasks.

The Tasks section of an agreed plan uses markdown checkboxes so the dumb loop
can count progress without judgment. A task may carry a per-step model
annotation the loop routes to the worker.
"""

from helix.state import write_doc
from helix.tasks import Task, next_task, parse_tasks, progress, read_tasks

_BODY = """# Plan

## Intent

Ship the widget.

## Tasks

- [x] Scaffold the widget module (model: haiku)
- [ ] Implement the widget core
- [ ] Add integration coverage (model: sonnet)

## Oracle gates

- [ ] not a task — outside the Tasks section
"""


def test_parse_tasks_reads_only_the_tasks_section():
    items = parse_tasks(_BODY)
    assert len(items) == 3
    assert [t.done for t in items] == [True, False, False]


def test_parse_tasks_extracts_model_annotations_and_cleans_text():
    items = parse_tasks(_BODY)
    assert items[0].model == "haiku"
    assert items[0].text == "Scaffold the widget module"
    assert items[1].model is None
    assert items[2].model == "sonnet"


def test_parse_tasks_without_a_tasks_heading_scans_the_whole_body():
    body = "- [ ] lone task\n- [X] shouted done marker\n"
    items = parse_tasks(body)
    assert len(items) == 2
    assert items[1].done is True


def test_parse_tasks_ignores_prose_and_empty_body():
    assert parse_tasks("just prose, no checkboxes") == []
    assert parse_tasks("") == []


def test_next_task_is_the_first_open_item():
    items = parse_tasks(_BODY)
    nxt = next_task(items)
    assert nxt is not None and nxt.text == "Implement the widget core"


def test_next_task_none_when_all_done():
    assert next_task([Task(text="t", done=True)]) is None
    assert next_task([]) is None


def test_progress_counts_done_vs_total():
    assert progress(parse_tasks(_BODY)) == (1, 3)
    assert progress([]) == (0, 0)


def test_read_tasks_from_a_plan_document(tmp_path):
    plan = tmp_path / "PLAN.md"
    write_doc(plan, {"id": "p", "project": "x"}, _BODY)
    items = read_tasks(plan)
    assert progress(items) == (1, 3)


def test_read_tasks_missing_file_is_empty(tmp_path):
    assert read_tasks(tmp_path / "absent.md") == []


def test_parse_tasks_joins_wrapped_task_lines():
    body = (
        "## Tasks\n\n"
        "- [ ] Create the widget with a long description that\n"
        "  wraps onto a continuation line (model: haiku)\n"
        "- [x] A second, single-line task\n"
    )
    items = parse_tasks(body)
    assert len(items) == 2
    assert items[0].model == "haiku"
    assert items[0].text.endswith("wraps onto a continuation line")
    assert items[1].done is True
