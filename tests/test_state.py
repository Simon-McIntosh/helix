"""Tests for the markdown+frontmatter state substrate.

state.py is the read/write boundary for Helix's plain-text state — the handoff
substrate every phase reads and writes. These tests pin the round-trip contract.
"""

from helix.state import read_doc, write_doc


def test_write_then_read_round_trips_frontmatter_and_body(tmp_path):
    path = tmp_path / "session.md"
    frontmatter = {"id": "20260701T000000Z-implement", "phase": "implement"}
    body = "# Narrative\n\nThe worker made an increment.\n"

    write_doc(path, frontmatter, body)
    fm, read_body = read_doc(path)

    assert fm == frontmatter
    assert read_body.strip() == body.strip()


def test_write_doc_emits_yaml_frontmatter_delimiters(tmp_path):
    path = tmp_path / "doc.md"
    write_doc(path, {"k": "v"}, "hello")

    text = path.read_text()
    assert text.startswith("---\n")
    assert "\n---\n" in text
    assert "k: v" in text
    assert text.rstrip().endswith("hello")


def test_read_doc_without_frontmatter_returns_empty_dict(tmp_path):
    path = tmp_path / "plain.md"
    path.write_text("no frontmatter here\njust body\n")

    fm, body = read_doc(path)

    assert fm == {}
    assert body == "no frontmatter here\njust body\n"


def test_read_doc_preserves_horizontal_rules_in_body(tmp_path):
    # A body that itself contains a --- must not be truncated at that marker.
    path = tmp_path / "doc.md"
    write_doc(path, {"id": "x"}, "before\n\n---\n\nafter")

    fm, body = read_doc(path)

    assert fm == {"id": "x"}
    assert "before" in body
    assert "after" in body


def test_write_doc_creates_parent_directories(tmp_path):
    path = tmp_path / "sessions" / "sid" / "session.md"
    write_doc(path, {"id": "sid"}, "body")

    assert path.exists()
    fm, _ = read_doc(path)
    assert fm == {"id": "sid"}
