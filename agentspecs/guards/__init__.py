# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Guard specifications.

A *Guard* is a reusable verification and protection component: it checks
whether the output or the action of a Cog or an Op is correct, safe,
policy-compliant and ready for use. Guards check; Gates (``agentspecs.gates``)
decide. The idea, and the words, are the Intelligence Hub whitepaper's
(section 5.1).

**A Guard extends a Policy.** A Policy (``agentspecs/policies``) is the
Shield's document: the rules that decide what may be read, written, deleted,
executed, sent and bought, the limits, the hosts and the MCP servers lent. It
bounds what an agent may do, and nothing in it verifies that the bounds held.
A Guard is that verification. ``extends`` names the Policy, ``id`` or
``id:version``; a Guard naming a Policy the catalogue does not hold is
refused. Resolution does not merge the Policy into the Guard: the resolved
Guard carries ``policy``, the Policy's ``id:version``, and :func:`policy_of`
gives the :class:`~agentspecs.policies.PolicySpec` — the standard the Guard
checks against, and the bounds it runs within when the Guard is itself a Cog
or a person — beside what the Guard adds: which of the seven categories it
is, at which stages of an Op it runs, what it checks, and the signals it
reports for a Gate to decide on.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..policies import POLICY_CATALOGUE, PolicySpec


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
    """Specification for a Guard, as it is written."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique Guard identifier")
    version: str = Field(default="0.0.1", description="Guard spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What the Guard is for")
    extends: str = Field(
        ...,
        description="The Policy the Guard extends, `id` or `id:version`",
    )
    category: GuardCategory = Field(..., description="Which of the seven categories it is")
    stages: list[GuardStage] = Field(
        ...,
        description="The stages of an Op it may run at",
    )
    method: GuardMethod = Field(
        default=GuardMethod.ALGORITHMIC, description="How the check is made"
    )
    check: str = Field(
        ...,
        description="What is verified, written so that code, a Cog or a person can run it",
    )
    signals: list[GuardSignal] = Field(
        default_factory=list,
        description="What it reports beside pass or fail, for a Gate to decide on",
    )
    required: bool = Field(
        default=True,
        description="Whether the work counts only once the Guard has passed",
    )
    enabled: bool = Field(default=True, description="Whether an Op may name it today")
    tags: list[str] = Field(default_factory=list)
    icon: str = Field(default="shield-check", description="Icon identifier")
    emoji: str = Field(default="\U0001f6e1️", description="Emoji representation")

    @field_validator("stages")
    @classmethod
    def _runs_somewhere(cls, stages: list[GuardStage]) -> list[GuardStage]:
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

    @field_validator("extends")
    @classmethod
    def _extends_a_policy(cls, extends: str) -> str:
        policy_ref(extends)
        return extends


def id_of(ref: str) -> str:
    """The id of a reference, `id` or `id:version`."""
    base, _, version = str(ref).rpartition(":")
    return base if base and "." in version else str(ref)


def policy_ref(ref: str, *, policies: Mapping[str, PolicySpec] | None = None) -> str:
    """The `id:version` of the Policy a reference names, from the catalogue.

    Refused, in a sentence, when no Policy has the id, or when the reference
    gives a version the catalogue's Policy does not have.
    """
    policies = policies if policies is not None else POLICY_CATALOGUE
    base = id_of(ref)
    policy = policies.get(base)
    if policy is None:
        known = ", ".join(sorted(policies)) or "nothing"
        raise ValueError(f"{ref!r} is not a Policy of the catalogue (known: {known})")
    _, _, version = str(ref).rpartition(":")
    if base != str(ref) and version != policy.version:
        raise ValueError(
            f"{ref!r} names a version the Policy {base!r} does not have ({policy.version})"
        )
    return f"{policy.id}:{policy.version}"


def load_raw(directory: Path) -> dict[str, dict[str, Any]]:
    """Every YAML spec of a directory as plain data, by id; the file is named for the id."""
    raw: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("id") != path.stem:
            raise GuardError(
                f"{path.name}: the file is named for id {path.stem!r}, "
                f"the spec says {data.get('id')!r}"
            )
        raw[path.stem] = data
    return raw


def load_raw_guards(directory: Path | None = None) -> dict[str, dict[str, Any]]:
    """Every Guard YAML of a directory as plain data, by id, unresolved."""
    return load_raw(directory or Path(__file__).parent)


def resolve_guard(guard: dict[str, Any]) -> dict[str, Any]:
    """One Guard, resolved: what it says, with ``policy`` in place of ``extends``.

    ``policy`` is the `id:version` of the Policy it extends, as the catalogue
    holds it; the Policy's document is not merged in — :func:`policy_of`
    gives it. A Guard naming a Policy the catalogue does not hold fails
    validation (``extends`` is checked as the spec is read).
    """
    spec = GuardSpec(**guard)
    flat = spec.model_dump(mode="json", exclude={"extends"})
    flat["policy"] = policy_ref(spec.extends)
    return flat


def policy_of(guard: GuardSpec | Mapping[str, Any]) -> PolicySpec:
    """The Policy a Guard extends, as written (``extends``) or resolved (``policy``)."""
    ref = (
        guard.extends
        if isinstance(guard, GuardSpec)
        else guard.get("policy") or guard.get("extends")
    )
    if not ref:
        raise GuardError("the Guard names no Policy")
    try:
        policy_ref(str(ref))
    except ValueError as error:
        raise GuardError(f"Guard {_name(guard)!r} extends {error}") from None
    return POLICY_CATALOGUE[id_of(str(ref))]


def _name(guard: GuardSpec | Mapping[str, Any]) -> str:
    return str(guard.id if isinstance(guard, GuardSpec) else guard.get("id", ""))


def load_guards(directory: Path | None = None) -> dict[str, GuardSpec]:
    """Every Guard of a directory, validated and checked to resolve, as it is written."""
    raw = load_raw_guards(directory)
    for guard in raw.values():
        resolve_guard(guard)
    return {identity: GuardSpec(**guard) for identity, guard in raw.items()}


_RAW_GUARDS: dict[str, dict[str, Any]] = load_raw_guards()

#: Every Guard, by id, as it is written.
GUARD_CATALOGUE: dict[str, GuardSpec] = load_guards()


def get_guard(guard_id: str) -> GuardSpec | None:
    """A Guard as it is written, by `id` or `id:version`, or None."""
    return GUARD_CATALOGUE.get(id_of(guard_id))


def get_resolved_guard(guard_id: str) -> dict[str, Any] | None:
    """A Guard, resolved — see `resolve_guard` — or None."""
    guard = _RAW_GUARDS.get(id_of(guard_id))
    return None if guard is None else resolve_guard(guard)


def list_guards() -> list[GuardSpec]:
    """Every Guard, as it is written."""
    return list(GUARD_CATALOGUE.values())


def guards_extending(policy_id: str) -> list[GuardSpec]:
    """The Guards that verify one Policy."""
    wanted = id_of(policy_id)
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
    "policy_of",
    "policy_ref",
    "resolve_guard",
]
