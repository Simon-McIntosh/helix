"""Project run configuration.

A Helix run is parameterized by a project's ``helix.yaml``: where the worker
operates, how to invoke it, the iteration cap, and the oracle gates. This is
*runtime* configuration — distinct from the durable state records defined in
``schema/helix.yaml`` (which describe what the loop persists, not how it runs).

The shape lives in the core; the values are project data. The core stays
project-agnostic: it knows a run has a worker command, caps, and gates, but
nothing about any particular project's domain.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from helix.models import OracleGate

CONFIG_FILENAME = "helix.yaml"


class WorkerConfig(BaseModel):
    """How to invoke the native worker (see :mod:`helix.worker`)."""

    model_config = ConfigDict(extra="forbid")

    command: list[str] = Field(
        description="Argv of the native worker. The composed prompt is fed on stdin."
    )
    timeout_s: int | None = Field(
        default=None, description="Per-invocation wall-clock cap (seconds)."
    )
    model: str | None = Field(
        default=None,
        description="Default model routed to the worker. Overridden per run by "
        "the CLI and per step by a task's `(model: …)` annotation in the plan.",
    )
    model_flag: str = Field(
        default="--model",
        description="The worker's own flag for selecting a model. Worker data — "
        "the default fits Claude Code.",
    )
    resume_args: list[str] = Field(
        default_factory=lambda: ["--continue"],
        description="Extra argv that makes the worker continue its most recent "
        "conversation in the repo — used for the first invocation after an "
        "interrupted run. The default fits Claude Code.",
    )


class Caps(BaseModel):
    """Bounds that halt the loop independent of the oracle."""

    model_config = ConfigDict(extra="forbid")

    max_iterations: int = Field(
        default=10, ge=1, description="Maximum implement->judge iterations."
    )


class Config(BaseModel):
    """A project's Helix run configuration, loaded from ``helix.yaml``."""

    model_config = ConfigDict(extra="forbid")

    repo: str = Field(
        default=".",
        description="Working directory for the worker and gates, relative to the "
        "project directory.",
    )
    plan: str | None = Field(
        default=None,
        description="Path to the agreed-plan document, relative to the project "
        "directory. Composed into the implement prompt.",
    )
    worker: WorkerConfig
    caps: Caps = Field(default_factory=Caps)
    gates: list[OracleGate] = Field(default_factory=list)


def load_config(project: Path) -> Config:
    """Load and validate ``<project>/helix.yaml`` into a :class:`Config`.

    Raises ``FileNotFoundError`` if the project has no config, and a pydantic
    ``ValidationError`` if the config is malformed.
    """
    path = Path(project) / CONFIG_FILENAME
    if not path.exists():
        raise FileNotFoundError(f"no {CONFIG_FILENAME} in project {project}")
    data = yaml.safe_load(path.read_text()) or {}
    return Config.model_validate(data)
