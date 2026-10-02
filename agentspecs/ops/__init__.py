# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Op specifications.

An *Op* is the orchestrated, supervised AI workflow a person launches: "close
the books", "qualify this lead", "build the board's pipeline report". It is
the level at which knowledge workers think about their job. The idea, and the
words, are the Intelligence Hub whitepaper's (sections 4.5 and 5.6).

An Op composes what the catalogue already has, by reference:

- **Cogs** (``agentspecs.cogs``) do the work, each carrying its own Frames;
- **Frames** (``agentspecs.frames``) applied at the workflow level orient the
  Op as a whole;
- a **supervisor** coordinates the Cogs;
- and a **validation strategy** says how the work is verified: the **Guards**
  (``agentspecs.guards``) run at each stage of its life, the **Gates**
  (``agentspecs.gates``) that decide whether it proceeds, and the **Track**
  (``agentspecs.tracks``) kept as evidence.

**An Op is not complete unless it declares how its work will be verified.**
So a spec with no post-run Guard, no Gate or no Track is refused, as is one
whose Gate reads a Guard the Op does not run.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from ..cogs import _RAW_COGS, CogError, resolve_cog
from ..frames import FrameError, compose_frames
from ..gates import GATE_CATALOGUE, GateSpec
from ..guards import _RAW_GUARDS, GuardError, GuardStage, id_of, load_raw, resolve_guard
from ..tracks import TRACK_CATALOGUE


class OpError(ValueError):
    """An Op that cannot be resolved — named plainly."""


class OpTrigger(str, Enum):
    """How an Op is invoked."""

    LAUNCHER = "launcher"
    """An application icon in a launcher."""

    COMMAND = "command"
    """A command typed in a CLI or a chat."""

    BUTTON = "button"
    """A button or a link in an application."""

    SCHEDULE = "schedule"
    """A job triggered by time, an event or another system."""


class OpSupervisor(BaseModel):
    """What coordinates the Cogs of an Op."""

    model: str = Field(..., description="The model that supervises, as the model catalogue names it")
    instructions: str = Field(
        default="",
        description="How the Cogs are sequenced, and what is done when something unexpected happens",
    )


class OpGuards(BaseModel):
    """The Guards of an Op, by the stage they run at."""

    preflight: List[str] = Field(default_factory=list, description="Is this Op allowed and properly configured?")
    in_flight: List[str] = Field(default_factory=list, description="Is the work staying within policy and bounds?")
    post_run: List[str] = Field(default_factory=list, description="Is the output correct, safe and ready for action?")
    continuous: List[str] = Field(default_factory=list, description="Is quality improving, degrading or drifting?")

    def by_stage(self) -> Dict[GuardStage, List[str]]:
        """The Guards, by stage."""
        return {stage: list(getattr(self, stage.value)) for stage in GuardStage}

    def all(self) -> List[str]:
        """Every Guard id the Op runs, once, in the order of the stages."""
        seen: List[str] = []
        for refs in self.by_stage().values():
            for ref in refs:
                if id_of(ref) not in seen:
                    seen.append(id_of(ref))
        return seen


class OpSpec(BaseModel):
    """Specification for an Op, as it is written."""

    id: str = Field(..., description="Unique Op identifier")
    version: str = Field(default="0.0.1", description="Op spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="The outcome the Op produces")
    owner: str = Field(..., description="The person or the group accountable for the outcome")
    goal: str = Field(default="", description="What a run is asked to achieve")
    cogs: List[str] = Field(..., description="The Cogs that do the work, `id` or `id:version`")
    frames: List[str] = Field(
        default_factory=list,
        description="Frames applied at the workflow level, beyond what the Cogs carry",
    )
    supervisor: OpSupervisor = Field(..., description="What coordinates the Cogs")
    guards: OpGuards = Field(..., description="The Guards, by the stage they run at")
    gates: List[str] = Field(..., description="The Gates that decide whether the work proceeds")
    track: str = Field(..., description="The Track kept as evidence, `id` or `id:version`")
    triggers: List[OpTrigger] = Field(
        default_factory=lambda: [OpTrigger.LAUNCHER],
        description="How the Op is invoked",
    )
    enabled: bool = Field(default=False, description="Whether the Op is offered today")
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="workflow", description="Icon identifier")
    emoji: str = Field(default="⚙️", description="Emoji representation")
    color: str = Field(default="", description="Accent colour")

    @field_validator("owner")
    @classmethod
    def _is_owned(cls, owner: str) -> str:
        if not owner.strip():
            raise ValueError("an Op names its owner: somebody is accountable for the outcome")
        return owner

    @field_validator("cogs")
    @classmethod
    def _has_workers(cls, cogs: List[str]) -> List[str]:
        if not cogs:
            raise ValueError("an Op names at least one Cog")
        if len({id_of(cog) for cog in cogs}) != len(cogs):
            raise ValueError("an Op names a Cog once")
        return cogs

    @model_validator(mode="after")
    def _declares_how_its_work_is_verified(self) -> "OpSpec":
        if not self.guards.post_run:
            raise ValueError(f"Op {self.id!r} is not complete: it names no post-run Guard")
        if not self.gates:
            raise ValueError(f"Op {self.id!r} is not complete: it names no Gate")
        if not self.track.strip():
            raise ValueError(f"Op {self.id!r} is not complete: it names no Track")
        return self


def load_raw_ops(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Op YAML of a directory as plain data, by id, unresolved."""
    return load_raw(directory or Path(__file__).parent)


def resolve_op(op: Dict[str, Any]) -> Dict[str, Any]:
    """One Op, with everything it names looked up and checked.

    The result keeps the Op's own fields and adds what a runtime and an
    auditor need without a second lookup:

    - ``cogs``: each Cog's id, the agent it extends, its Frames and its kind;
    - ``frames`` and ``lineage``: the workflow-level Frames, and every Frame
      that orients the Op — those, and the ones its Cogs carry;
    - ``guards``: by stage, each Guard resolved with the guardrail it extends;
    - ``frame_guards``: the checks the Frames themselves declare;
    - ``gates``: each Gate, with the signals it reads;
    - ``track``: the Track, with its retention in days.

    Refused: a Cog, Frame, Guard, Gate or Track that does not exist; a Guard,
    Gate or Track that is not enabled; a Cog that is not enabled when the Op
    is (a draft Op may name a draft Cog); a Guard named at a stage it does not
    run at; Gates listed out of the order of the stages; a Gate that reads a
    Guard the Op does not run, or decides at a stage where none of its Guards
    has run yet.
    """
    spec = OpSpec(**op)

    cogs: List[Dict[str, Any]] = []
    lineage: List[str] = []
    frame_guards: Dict[str, Dict[str, Any]] = {}
    try:
        context = compose_frames(spec.frames)
        contexts = [context.model_dump(mode="json")]
        for ref in spec.cogs:
            raw = _RAW_COGS.get(id_of(ref))
            if raw is None:
                raise OpError(f"Op {spec.id!r} names Cog {ref!r}, which is not defined")
            cog = resolve_cog(raw)
            if spec.enabled and not cog["enabled"]:
                raise OpError(
                    f"Op {spec.id!r} is enabled and names Cog {cog['id']!r}, which is not: "
                    "an Op that is offered has workers that are"
                )
            cogs.append({"id": cog["id"], "agent": cog["agent"], "frames": cog["frames"], "kind": cog["kind"]})
            contexts.append(cog["frame_context"])
    except (FrameError, CogError) as error:
        raise OpError(f"Op {spec.id!r}: {error}") from error
    for entry in contexts:
        for identity in entry["lineage"]:
            if identity not in lineage:
                lineage.append(identity)
        for guard in entry["guards"]:
            frame_guards[guard["id"]] = guard

    guards: Dict[str, List[Dict[str, Any]]] = {}
    ran_by: Dict[str, List[GuardStage]] = {}
    for stage, refs in spec.guards.by_stage().items():
        guards[stage.value] = []
        for ref in refs:
            raw_guard = _RAW_GUARDS.get(id_of(ref))
            if raw_guard is None:
                raise OpError(f"Op {spec.id!r} names Guard {ref!r}, which is not defined")
            try:
                guard = resolve_guard(raw_guard)
            except GuardError as error:
                raise OpError(f"Op {spec.id!r}: {error}") from error
            if not guard["enabled"]:
                raise OpError(f"Op {spec.id!r} names Guard {ref!r}, which is not enabled")
            if stage.value not in guard["stages"]:
                raise OpError(
                    f"Op {spec.id!r} runs Guard {guard['id']!r} at {stage.value}; "
                    f"it runs at {', '.join(guard['stages'])}"
                )
            guards[stage.value].append(guard)
            ran_by.setdefault(guard["id"], []).append(stage)

    order = list(GuardStage)
    gates: List[Dict[str, Any]] = []
    met: Optional[GateSpec] = None
    for ref in spec.gates:
        gate: Optional[GateSpec] = GATE_CATALOGUE.get(id_of(ref))
        if gate is None:
            raise OpError(f"Op {spec.id!r} names Gate {ref!r}, which is not defined")
        if not gate.enabled:
            raise OpError(f"Op {spec.id!r} names Gate {ref!r}, which is not enabled")
        # The list is the order the Gates are met in: a stage never comes back.
        if met is not None and order.index(gate.stage) < order.index(met.stage):
            raise OpError(
                f"Op {spec.id!r}: Gate {gate.id!r} decides at {gate.stage.value} and is listed "
                f"after {met.id!r}, which decides at {met.stage.value}"
            )
        met = gate
        for guard_ref in gate.guards:
            stages = ran_by.get(id_of(guard_ref))
            if not stages:
                raise OpError(
                    f"Op {spec.id!r}: Gate {gate.id!r} reads Guard {guard_ref!r}, which the Op does not run"
                )
            if min(order.index(stage) for stage in stages) > order.index(gate.stage):
                raise OpError(
                    f"Op {spec.id!r}: Gate {gate.id!r} decides at {gate.stage.value}, "
                    f"before Guard {id_of(guard_ref)!r} has run"
                )
        gates.append({**gate.model_dump(mode="json"), "signals": gate.signals})

    track = TRACK_CATALOGUE.get(id_of(spec.track))
    if track is None:
        raise OpError(f"Op {spec.id!r} names Track {spec.track!r}, which is not defined")
    if not track.enabled:
        raise OpError(f"Op {spec.id!r} names Track {spec.track!r}, which is not enabled")

    resolved = spec.model_dump(mode="json")
    resolved.update(
        {
            "cogs": cogs,
            "frames": list(context.frames),
            "lineage": lineage,
            "guards": guards,
            "frame_guards": list(frame_guards.values()),
            "gates": gates,
            "track": {**track.model_dump(mode="json"), "retention_days": track.retention_days},
        }
    )
    return resolved


def load_ops(directory: Optional[Path] = None) -> Dict[str, OpSpec]:
    """Every Op of a directory, validated and checked to resolve, as it is written."""
    raw = load_raw_ops(directory)
    for op in raw.values():
        resolve_op(op)
    return {identity: OpSpec(**op) for identity, op in raw.items()}


_RAW_OPS: Dict[str, Dict[str, Any]] = load_raw_ops()

#: Every Op, by id, as it is written.
OP_CATALOGUE: Dict[str, OpSpec] = load_ops()


def get_op(op_id: str) -> Optional[OpSpec]:
    """An Op as it is written, by `id` or `id:version`, or None."""
    return OP_CATALOGUE.get(id_of(op_id))


def get_resolved_op(op_id: str) -> Optional[Dict[str, Any]]:
    """An Op, resolved — see `resolve_op` — or None."""
    op = _RAW_OPS.get(id_of(op_id))
    return None if op is None else resolve_op(op)


def list_ops() -> List[OpSpec]:
    """Every Op, as it is written."""
    return list(OP_CATALOGUE.values())


def ops_using(ref: str) -> List[OpSpec]:
    """The Ops that name a Cog, a Guard, a Gate or a Track."""
    wanted = id_of(ref)
    using = []
    for op in OP_CATALOGUE.values():
        named = {id_of(item) for item in [*op.cogs, *op.guards.all(), *op.gates, op.track]}
        if wanted in named:
            using.append(op)
    return using


__all__ = [
    "OP_CATALOGUE",
    "OpError",
    "OpGuards",
    "OpSpec",
    "OpSupervisor",
    "OpTrigger",
    "get_op",
    "get_resolved_op",
    "list_ops",
    "load_ops",
    "load_raw_ops",
    "ops_using",
    "resolve_op",
]
