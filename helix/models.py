from __future__ import annotations

import re
import sys
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer,
)


metamodel_version = "1.11.0"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias=True,
        validate_by_name=True,
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        use_enum_values=True,
        strict=False,
    )


class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key: str):
        return getattr(self.root, key)

    def __getitem__(self, key: str):
        return self.root[key]

    def __setitem__(self, key: str, value):
        self.root[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta(
    {
        "default_prefix": "helix",
        "default_range": "string",
        "description": "The durable record types for a Helix run. These define the "
        "plain-text state the dumb outer loop reads and writes: "
        "sessions (self-contained, chained runs), findings (age- and "
        "condition-stamped claims), oracle gates (tiered completion "
        "criteria), and the plan state (the signed contract crossing "
        "plan->implement). pydantic v2 models are generated from this "
        "schema with `gen-pydantic` (see helix/models.py).",
        "id": "https://github.com/Simon-McIntosh/helix/schema/helix",
        "imports": ["linkml:types"],
        "license": "CC BY-ND 4.0",
        "name": "helix",
        "prefixes": {
            "helix": {
                "prefix_prefix": "helix",
                "prefix_reference": "https://github.com/Simon-McIntosh/helix/schema/",
            },
            "linkml": {
                "prefix_prefix": "linkml",
                "prefix_reference": "https://w3id.org/linkml/",
            },
        },
        "source_file": "schema/helix.yaml",
        "title": "Helix Orchestration Schema",
    }
)


class Phase(str, Enum):
    """
    The three disciplined phases of the loop.
    """

    plan = "plan"
    """
    Interactive, high-judgment. The human's seat.
    """
    implement = "implement"
    """
    Autonomous, low-judgment. A worker makes bounded progress.
    """
    judge = "judge"
    """
    Independent verdict. A separate invocation from the worker.
    """


class GateTier(str, Enum):
    """
    How a completion gate is checked.
    """

    surrogate = "surrogate"
    """
    Fast, cheap check run every iteration as backpressure.
    """
    blocking = "blocking"
    """
    Slow or physical-experiment check. The loop blocks and waits for human-supplied ground truth rather than guessing.
    """


class Verdict(str, Enum):
    """
    The judge's decision for a session.
    """

    pass_ = "pass"
    """
    Every gate's criterion is satisfied by the evidence.
    """
    fail = "fail"
    """
    At least one surrogate gate is unmet.
    """
    blocked = "blocked"
    """
    A blocking-tier gate needs human-supplied ground truth.
    """


class Session(ConfiguredBaseModel):
    """
    A self-contained, human-sortable run of one phase. Sessions chain through their predecessor to form a campaign thread walkable over years.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://github.com/Simon-McIntosh/helix/schema/helix"}
    )

    id: str = Field(
        default=...,
        description="""Human-sortable id, YYYYMMDDTHHMMSSZ-<slug> (UTC).""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["Session", "Finding", "OracleGate", "PlanState"]
            }
        },
    )
    phase: Phase = Field(
        default=..., json_schema_extra={"linkml_meta": {"domain_of": ["Session"]}}
    )
    predecessor: Optional[str] = Field(
        default=None,
        description="""Id of the session this one continues from (empty for the first).""",
        json_schema_extra={"linkml_meta": {"domain_of": ["Session"]}},
    )
    created_at: datetime = Field(
        default=..., json_schema_extra={"linkml_meta": {"domain_of": ["Session"]}}
    )
    verdict: Optional[Verdict] = Field(
        default=None,
        description="""Set only for judge sessions.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["Session"]}},
    )
    summary: Optional[str] = Field(
        default=None,
        description="""One-paragraph human-readable summary of what this session did.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["Session"]}},
    )


class Finding(ConfiguredBaseModel):
    """
    A durable claim produced during a session, stamped with when it was observed and the conditions under which it held true.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://github.com/Simon-McIntosh/helix/schema/helix"}
    )

    id: str = Field(
        default=...,
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["Session", "Finding", "OracleGate", "PlanState"]
            }
        },
    )
    statement: str = Field(
        default=...,
        description="""The claim itself, in plain language.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["Finding"]}},
    )
    observed_at: datetime = Field(
        default=..., json_schema_extra={"linkml_meta": {"domain_of": ["Finding"]}}
    )
    conditions: Optional[str] = Field(
        default=None,
        description="""The conditions under which the claim was true (machine, config, inputs).""",
        json_schema_extra={"linkml_meta": {"domain_of": ["Finding"]}},
    )
    session: str = Field(
        default=...,
        description="""Id of the session that produced this finding.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["Finding"]}},
    )


class OracleGate(ConfiguredBaseModel):
    """
    A single completion criterion checked against evidence.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://github.com/Simon-McIntosh/helix/schema/helix"}
    )

    id: str = Field(
        default=...,
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["Session", "Finding", "OracleGate", "PlanState"]
            }
        },
    )
    name: str = Field(
        default=..., json_schema_extra={"linkml_meta": {"domain_of": ["OracleGate"]}}
    )
    tier: GateTier = Field(
        default=..., json_schema_extra={"linkml_meta": {"domain_of": ["OracleGate"]}}
    )
    criterion: str = Field(
        default=...,
        description="""Human-readable done condition.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["OracleGate"]}},
    )
    command: Optional[str] = Field(
        default=None,
        description="""Shell command that evaluates a surrogate gate (empty for blocking gates).""",
        json_schema_extra={"linkml_meta": {"domain_of": ["OracleGate"]}},
    )


class PlanState(ConfiguredBaseModel):
    """
    The agreed plan crossing the plan->implement boundary — the signed contract the worker and judge are measured against.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://github.com/Simon-McIntosh/helix/schema/helix"}
    )

    id: str = Field(
        default=...,
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["Session", "Finding", "OracleGate", "PlanState"]
            }
        },
    )
    project: str = Field(
        default=..., json_schema_extra={"linkml_meta": {"domain_of": ["PlanState"]}}
    )
    intent: Optional[str] = Field(
        default=None,
        description="""Expanded specification, feature list, and constraints.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["PlanState"]}},
    )
    tasks: Optional[list[str]] = Field(
        default=None,
        description="""Ordered task units, each with a write scope and verification command.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["PlanState"]}},
    )
    gates: Optional[list[str]] = Field(
        default=None,
        description="""Ids of the oracle gates that define done for this plan.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["PlanState"]}},
    )
    agreed_at: Optional[datetime] = Field(
        default=None,
        description="""When the human signed off on the plan as the contract.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["PlanState"]}},
    )


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
Session.model_rebuild()
Finding.model_rebuild()
OracleGate.model_rebuild()
PlanState.model_rebuild()
