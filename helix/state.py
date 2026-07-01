"""Markdown-and-files state substrate.

Contract
--------
All loop state and provenance live as plain text (markdown with YAML
frontmatter) co-located with the repo and committed to git. This module is the
read/write boundary for that substrate. Human-facing review surfaces (HTML) are
*projections* generated on demand, never the source of truth.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_DELIM = "---"


def read_doc(path: Path) -> tuple[dict, str]:
    """Read a markdown doc, returning ``(frontmatter, body)``.

    A leading ``---`` fenced block is parsed as YAML frontmatter; everything
    after the closing fence is the body. A ``---`` inside the body (a horizontal
    rule) is left untouched. A document with no frontmatter returns ``({}, text)``.
    """
    text = Path(path).read_text()
    if text.startswith(_DELIM + "\n") or text.startswith(_DELIM + "\r\n"):
        # Split into ['', <frontmatter>, <body>] — maxsplit keeps body intact.
        _, fenced, body = text.split(_DELIM, 2)
        frontmatter = yaml.safe_load(fenced) or {}
        return frontmatter, body.lstrip("\n")
    return {}, text


def write_doc(path: Path, frontmatter: dict, body: str) -> None:
    """Write ``frontmatter`` + ``body`` to ``path`` as markdown with YAML frontmatter.

    Parent directories are created as needed. Keys are emitted in insertion order
    (not sorted) so the human-facing record reads in a stable, meaningful order.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fenced = yaml.safe_dump(frontmatter, sort_keys=False).strip()
    path.write_text(f"{_DELIM}\n{fenced}\n{_DELIM}\n\n{body.rstrip()}\n")
