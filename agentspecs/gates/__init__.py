# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Gate specifications.

A *Gate* is a decision point in an Op: the results of one or more Guards
determine what happens next. Guards check; Gates decide. The idea, and the
words, are the Intelligence Hub whitepaper's (section 5.2).

Not every failure is the same — some need a correction, some a review, some
an escalation, some a stop — and a Gate writes that decision into the
workflow: ``when`` a condition on what its Guards reported holds, ``then``
one of a closed set of actions. A Gate is also where the autonomy an Op was
granted ends: the point at which a person can interpret an output, decline
it, override it or stop the work.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from ..guards import GuardStage, id_of, load_raw


class GateError(ValueError):
    """A Gate that cannot be resolved — named plainly."""


class GateAction(str, Enum):
    """What a Gate decides."""

    PROCEED = "proceed"
    """The work goes on."""

    PAUSE = "pause"
    """The work waits for a revision."""

    RETRY = "retry"
    """The step is run again, possibly by another Cog."""

    ADDITIONAL_VALIDATION = "additional_validation"
    """More Guards are run before deciding."""

    HUMAN_REVIEW_REQUIRED = "human_review_required"
    """A person reviews the output before it is used."""

    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    """A person approves before the action is taken."""

    EXPERT_REVIEW_REQUIRED = "expert_review_required"
    """A named expert reviews."""

    STOP = "stop"
    """The Op ends."""

    STOP_AND_ESCALATE = "stop_and_escalate"
    """The Op ends and somebody is told."""


#: The actions that hand the decision to a person: a Gate deciding one says to whom.
HUMAN_ACTIONS = frozenset(
    {
        GateAction.HUMAN_REVIEW_REQUIRED,
        GateAction.HUMAN_APPROVAL_REQUIRED,
        GateAction.EXPERT_REVIEW_REQUIRED,
        GateAction.STOP_AND_ESCALATE,
    }
)

#: The condition that always holds, for a Gate every run goes through.
ALWAYS = "always"

#: `signal`, `signal == value`, `signal < 0.8`, joined by `and` / `or`.
_CLAUSE = re.compile(
    r"^\s*(?P<signal>[a-z][a-z0-9_]*)\s*(?:(?P<op>==|!=|<=|>=|<|>)\s*(?P<value>-?\d+(?:\.\d+)?|true|false|[a-z][a-z0-9_-]*))?\s*$"
)


def signals_of(condition: str) -> List[str]:
    """The signals a condition reads, in order; refuses one it cannot parse.

    A condition is a signal on its own (true when the Guard reported it),
    or a comparison of one with a number, `true`, `false` or a word; several
    are joined by `and` or `or`. `always` reads nothing.
    """
    if condition.strip() == ALWAYS:
        return []
    names: List[str] = []
    for clause in re.split(r"\s+(?:and|or)\s+", condition.strip()):
        matched = _CLAUSE.match(clause)
        if matched is None or matched.group("signal") in ("and", "or", "true", "false"):
            raise GateError(
                f"cannot read the condition {condition!r}: write `signal`, or `signal < 0.8`, "
                "joined by `and` / `or`, or `always`"
            )
        if matched.group("signal") not in names:
            names.append(matched.group("signal"))
    return names


class GateSpec(BaseModel):
    """Specification for a Gate."""

    id: str = Field(..., description="Unique Gate identifier")
    version: str = Field(default="0.0.1", description="Gate spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What decision the Gate makes, and why")
    stage: GuardStage = Field(
        default=GuardStage.POST_RUN,
        description="The stage of an Op the decision is made at",
    )
    guards: List[str] = Field(
        default_factory=list,
        description="The Guards whose results the Gate reads, `id` or `id:version`",
    )
    when: str = Field(
        ...,
        description="The condition, on the signals its Guards report; `always` for a Gate every run goes through",
    )
    then: GateAction = Field(..., description="What happens when the condition holds")
    otherwise: GateAction = Field(
        default=GateAction.PROCEED,
        description="What happens when it does not",
    )
    reviewers: List[str] = Field(
        default_factory=list,
        description="The roles the decision is handed to, when it is handed to a person",
    )
    max_retries: int = Field(default=0, ge=0, description="How many times `retry` may be decided")
    enabled: bool = Field(default=True, description="Whether an Op may name it today")
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="git-branch", description="Icon identifier")
    emoji: str = Field(default="\U0001f6a6", description="Emoji representation")

    @field_validator("when")
    @classmethod
    def _is_a_condition(cls, when: str) -> str:
        signals_of(when)
        return when.strip()

    @model_validator(mode="after")
    def _is_decidable(self) -> "GateSpec":
        # Either branch can hand the decision to a person.
        for action in (self.then, self.otherwise):
            if action in HUMAN_ACTIONS and not self.reviewers:
                raise ValueError(f"Gate {self.id!r} decides {action.value}: it names the `reviewers` it goes to")
        if GateAction.RETRY in (self.then, self.otherwise) and self.max_retries < 1:
            raise ValueError(f"Gate {self.id!r} decides retry: it says `max_retries`, at least 1")
        if self.when != ALWAYS and not self.guards:
            raise ValueError(f"Gate {self.id!r} reads a condition: it names the `guards` that report it")
        if self.then == self.otherwise:
            raise ValueError(f"Gate {self.id!r} decides {self.then.value} either way: it decides nothing")
        return self

    @property
    def signals(self) -> List[str]:
        """The signals the condition reads."""
        return signals_of(self.when)


def load_raw_gates(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Gate YAML of a directory as plain data, by id."""
    return load_raw(directory or Path(__file__).parent)


def check_gate(gate: GateSpec, guards: Dict[str, Dict[str, Any]]) -> None:
    """A Gate names Guards that exist and reads signals they report."""
    reported: set = set()
    for ref in gate.guards:
        guard = guards.get(id_of(ref))
        if guard is None:
            raise GateError(f"Gate {gate.id!r} reads Guard {ref!r}, which is not defined")
        reported.update(signal.get("name") for signal in guard.get("signals") or [])
    for signal in gate.signals:
        if signal not in reported:
            raise GateError(
                f"Gate {gate.id!r} reads the signal {signal!r}, which none of its Guards reports "
                f"(they report: {', '.join(sorted(reported)) or 'nothing'})"
            )


def load_gates(directory: Optional[Path] = None) -> Dict[str, GateSpec]:
    """Every Gate of a directory, validated against the Guard catalogue."""
    from ..guards import _RAW_GUARDS

    gates = {identity: GateSpec(**gate) for identity, gate in load_raw_gates(directory).items()}
    for gate in gates.values():
        check_gate(gate, _RAW_GUARDS)
    return gates


#: Every Gate, by id.
GATE_CATALOGUE: Dict[str, GateSpec] = load_gates()


def get_gate(gate_id: str) -> Optional[GateSpec]:
    """A Gate, by `id` or `id:version`, or None."""
    return GATE_CATALOGUE.get(id_of(gate_id))


def list_gates() -> List[GateSpec]:
    """Every Gate."""
    return list(GATE_CATALOGUE.values())


__all__ = [
    "ALWAYS",
    "GATE_CATALOGUE",
    "HUMAN_ACTIONS",
    "GateAction",
    "GateError",
    "GateSpec",
    "check_gate",
    "get_gate",
    "list_gates",
    "load_gates",
    "load_raw_gates",
    "signals_of",
]
