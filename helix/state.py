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


def read_doc(path: Path) -> tuple[dict, str]:
    """Read a markdown doc, returning ``(frontmatter, body)``.

    Raises ``NotImplementedError`` until the substrate is built (bootstrap P1).
    """
    raise NotImplementedError("state substrate is a bootstrap target (P1)")


def write_doc(path: Path, frontmatter: dict, body: str) -> None:
    """Write ``frontmatter`` + ``body`` to ``path`` as markdown with YAML frontmatter.

    Raises ``NotImplementedError`` until the substrate is built (bootstrap P1).
    """
    raise NotImplementedError("state substrate is a bootstrap target (P1)")
