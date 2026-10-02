# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Guard specifications.

A *Guard* is a reusable verification and protection component: it checks
whether the output or the action of a Cog or an Op is correct, safe,
policy-compliant and ready for use. Guards check; Gates (``agentspecs.gates``)
decide. The idea, and the words, are the Intelligence Hub whitepaper's
(section 5.1).

**A Guard extends a guardrail.** A guardrail (``agentspecs/guardrails``) is a
policy: what may be read, written, executed and sent, how much, and how data
is handled. It bounds what an agent may do, and nothing in it verifies that
the bounds held. A Guard is that verification. ``extends`` names the
guardrail, by the extension mechanism every spec uses
(``docs/modularity/extension``): the resolved Guard carries the guardrail's
policy — the standard it checks against, and the bounds it runs within when
the Guard is itself a Cog or a person — with what the Guard adds: which of
the seven categories it is, at which stages of an Op it runs, what it checks,
and the signals it reports for a Gate to decide on.
"""

from __future__ import annotations

import copy
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..compose import merge_spec

_ROOT = Path(__file__).parent.parent


class GuardError(ValueError):
    """A Guard that cannot be resolved — named plainly."""


class GuardCategory(str, Enum):
    """What a Guard verifies: the whitepaper's seven categories (section 5.5)."""

    ALGORITHMIC = "algorithmic"
    SOURCE_GROUNDING = "source-grounding"
    CONSENSUS = "consensus"
    EXPERT = "expert"
    POLICY_SAFETY = "policy-safety"
    REGRESSION_DRIFT = "regression-drift"
    OUTCOME = "outcome"


class GuardStage(str, Enum):
    """When in the life of an Op a Guard runs (section 5.4)."""

    PREFLIGHT = "preflight"
    """Is this Op allowed and properly configured?"""

    IN_FLIGHT = "in_flight"
    """Is the work staying within policy and expected bounds?"""

    POST_RUN = "post_run"
    """Is the output correct, useful, safe and ready for action?"""

    CONTINUOUS = "continuous"
    """Is quality improving, degrading or drifting over time?"""


class GuardMethod(str, Enum):
    """How the check is made."""

    ALGORITHMIC = "algorithmic"
    """Code decides: a schema, a reconciliation, a rule."""

    COG = "cog"
    """A Cog judges, where the check needs interpretation."""

    HUMAN = "human"
    """A person judges."""


class GuardSignal(BaseModel):
    """Something a Guard reports, which a Gate's condition can read."""

    name: str = Field(..., description="The name a Gate's `when` uses, e.g. `confidence`")
    type: str = Field(default="boolean", description="`boolean`, `number` or `string`")
    description: str = Field(default="", description="What it measures")

    @field_validator("type")
    @classmethod
    def _is_a_known_type(cls, value: str) -> str:
        if value not in ("boolean", "number", "string"):
            raise ValueError("a signal is a `boolean`, a `number` or a `string`")
        return value


class GuardSpec(BaseModel):
    """Specification for a Guard, as it is written.

    Any other field is a guardrail field the Guard overrides, by the rules of
    extension: a mapping replaces the guardrail's, a scalar wins.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique Guard identifier")
    version: str = Field(default="0.0.1", description="Guard spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What the Guard is for")
    extends: str = Field(
        ...,
        description="The guardrail the Guard extends, `id` or `id:version`",
    )
    category: GuardCategory = Field(..., description="Which of the seven categories it is")
    stages: List[GuardStage] = Field(
        ...,
        description="The stages of an Op it may run at",
    )
    method: GuardMethod = Field(default=GuardMethod.ALGORITHMIC, description="How the check is made")
    check: str = Field(
        ...,
        description="What is verified, written so that code, a Cog or a person can run it",
    )
    signals: List[GuardSignal] = Field(
        default_factory=list,
        description="What it reports beside pass or fail, for a Gate to decide on",
    )
    required: bool = Field(
        default=True,
        description="Whether the work counts only once the Guard has passed",
    )
    enabled: bool = Field(default=True, description="Whether an Op may name it today")
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="shield-check", description="Icon identifier")
    emoji: str = Field(default="\U0001f6e1️", description="Emoji representation")

    @field_validator("stages")
    @classmethod
    def _runs_somewhere(cls, stages: List[GuardStage]) -> List[GuardStage]:
        if not stages:
            raise ValueError("a Guard names at least one stage it runs at")
        if len(set(stages)) != len(stages):
            raise ValueError("a Guard names a stage once")
        return stages

    @field_validator("check")
    @classmethod
    def _checks_something(cls, check: str) -> str:
        if not check.strip():
            raise ValueError("a Guard says what it checks")
        return check


def id_of(ref: str) -> str:
    """The id of a reference, `id` or `id:version`."""
    base, _, version = str(ref).rpartition(":")
    return base if base and "." in version else str(ref)


def load_raw(directory: Path) -> Dict[str, Dict[str, Any]]:
    """Every YAML spec of a directory as plain data, by id; the file is named for the id."""
    raw: Dict[str, Dict[str, Any]] = {}
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("id") != path.stem:
            raise GuardError(f"{path.name}: the file is named for id {path.stem!r}, the spec says {data.get('id')!r}")
        raw[path.stem] = data
    return raw


def load_raw_guards(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Guard YAML of a directory as plain data, by id, unresolved."""
    return load_raw(directory or Path(__file__).parent)


_GUARDRAILS: Dict[str, Dict[str, Any]] = {}


def _default_guardrails() -> Dict[str, Dict[str, Any]]:
    """This package's guardrails, read once."""
    if not _GUARDRAILS:
        _GUARDRAILS.update(load_raw(_ROOT / "guardrails"))
    return _GUARDRAILS


#: What identifies the guardrail and is the Guard's own in the resolved spec.
_IDENTITY = ("id", "version", "name", "description", "extends")


def resolve_guard(
    guard: Dict[str, Any],
    *,
    guardrails: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """One Guard, flat: the guardrail it extends, with what the Guard adds.

    The result carries every field of the guardrail — its permissions, its
    data scope and handling, its limits, its approval policy — under the
    Guard's own identity, and ``guardrail``, the id of the guardrail extended.
    """
    guardrails = guardrails if guardrails is not None else _default_guardrails()
    spec = GuardSpec(**guard)
    guardrail_id = id_of(spec.extends)
    if guardrail_id not in guardrails:
        known = ", ".join(sorted(guardrails)) or "nothing"
        raise GuardError(
            f"Guard {spec.id!r} extends {spec.extends!r}, which is not a guardrail (known: {known})"
        )
    policy = {key: value for key, value in guardrails[guardrail_id].items() if key not in _IDENTITY}
    flat = copy.deepcopy(merge_spec(policy, {key: value for key, value in guard.items() if key != "extends"}))
    flat.update(
        {
            "id": spec.id,
            "version": spec.version,
            "guardrail": guardrail_id,
            "category": spec.category.value,
            "stages": [stage.value for stage in spec.stages],
            "method": spec.method.value,
            "signals": [signal.model_dump() for signal in spec.signals],
            "required": spec.required,
            "enabled": spec.enabled,
        }
    )
    return flat


def load_guards(directory: Optional[Path] = None) -> Dict[str, GuardSpec]:
    """Every Guard of a directory, validated and checked to resolve, as it is written."""
    raw = load_raw_guards(directory)
    for guard in raw.values():
        resolve_guard(guard)
    return {identity: GuardSpec(**guard) for identity, guard in raw.items()}


_RAW_GUARDS: Dict[str, Dict[str, Any]] = load_raw_guards()

#: Every Guard, by id, as it is written.
GUARD_CATALOGUE: Dict[str, GuardSpec] = load_guards()


def get_guard(guard_id: str) -> Optional[GuardSpec]:
    """A Guard as it is written, by `id` or `id:version`, or None."""
    return GUARD_CATALOGUE.get(id_of(guard_id))


def get_resolved_guard(guard_id: str) -> Optional[Dict[str, Any]]:
    """A Guard, flat — see `resolve_guard` — or None."""
    guard = _RAW_GUARDS.get(id_of(guard_id))
    return None if guard is None else resolve_guard(guard)


def list_guards() -> List[GuardSpec]:
    """Every Guard, as it is written."""
    return list(GUARD_CATALOGUE.values())


def guards_extending(guardrail_id: str) -> List[GuardSpec]:
    """The Guards that verify one guardrail."""
    wanted = id_of(guardrail_id)
    return [guard for guard in GUARD_CATALOGUE.values() if id_of(guard.extends) == wanted]


__all__ = [
    "GUARD_CATALOGUE",
    "GuardCategory",
    "GuardError",
    "GuardMethod",
    "GuardSignal",
    "GuardSpec",
    "GuardStage",
    "get_guard",
    "get_resolved_guard",
    "guards_extending",
    "id_of",
    "list_guards",
    "load_guards",
    "load_raw",
    "load_raw_guards",
    "resolve_guard",
]
