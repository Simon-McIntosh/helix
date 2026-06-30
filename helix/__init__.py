"""Helix — a long-horizon agent orchestrator.

Helix wraps a native agent worker inside a deterministic outer loop with three
disciplined phases: plan, implement, judge. The loop itself contains no model
judgment; all intelligence stays in the worker. Durable state lives in
plain-text artifacts and git history, never in an accumulating conversation.

See ``docs/specs/`` for the design and ``AGENTS.md`` for working conventions.
"""

__version__ = "0.0.0"
