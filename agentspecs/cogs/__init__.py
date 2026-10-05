# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Cog specifications.

A *Cog* is an AI worker you can hold to account: not a bare model, but an
assembly of model, context, tools and permissions that can be named,
versioned, inspected and replaced. The idea, and the word, are the
Intelligence Hub whitepaper's (section 4.4).

For now a Cogspec is two things, and both are things the catalogue already
has.

**A Cog extends an agent.** ``extends`` names an agent spec, by the extension
mechanism every spec uses (``docs/modularity/extension``): the Cog *is* that
agent — its model, its harness, its skills, its tools, its prompt — with what
the Cog says differently. Nothing of the agent is restated.

**A Cog is equipped with Frames.** ``frames`` names the Frames it works under
(``agentspecs.frames``), in order. They are what turns an agent into a worker
of a particular organization: its rules, its vocabulary, its style, the skills
the work depends on, and the Guards its output has to pass.

``resolve_cog`` flattens both: the agent the Cog extends, the Cog's own
changes, then the Frames — their skills, tools and MCP servers added to the
agent's, and their context rendered onto the end of its system prompt. What a
runtime receives is one flat spec that says which Frames oriented it and which
Guards it answers to.
"""

from __future__ import annotations

import copy
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..compose import CompositionError, merge_lists, resolve_spec
from ..frames import FrameContext, FrameError, compose_frames, load_raw_frames, render_frames

_ROOT = Path(__file__).parent.parent


class CogError(ValueError):
    """A Cog that cannot be resolved — named plainly."""


class CogKind(str, Enum):
    """What a Cog packages: the whitepaper's three types."""

    CONTEXT = "context"
    """The data and the context sent to a model it points to. What a Cogspec is today."""

    MODEL = "model"
    """The model itself, deployed to generate from inputs. Named, and not resolvable yet."""

    COMBINED = "combined"
    """Model and context together. Named, and not resolvable yet."""


#: The kinds `resolve_cog` knows how to resolve. The others package model
#: weights, which a Cogspec does not describe yet: resolving one as a context
#: Cog would hand back something plausible and wrong.
RESOLVABLE_KINDS = frozenset({CogKind.CONTEXT})


class CogSpec(BaseModel):
    """Specification for a Cog, as it is written.

    Any other field is an agent field the Cog overrides or adds to, by the
    rules of extension: a scalar replaces the agent's, a list appends to it.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique Cog identifier")
    version: str = Field(default="0.0.1", description="Cog spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What the Cog does, and under which context")
    extends: str = Field(
        ...,
        description="The agent spec the Cog extends, `id` or `id:version`",
    )
    frames: List[str] = Field(
        ...,
        description="The Frames the Cog works under, in order, `id` or `id:version`",
    )
    kind: CogKind = Field(default=CogKind.CONTEXT, description="What the Cog packages")
    enabled: bool = Field(default=False, description="Whether the Cog is offered today")

    @field_validator("frames")
    @classmethod
    def _is_equipped(cls, frames: List[str]) -> List[str]:
        if not frames:
            raise ValueError("a Cog names at least one Frame: without one it is the agent it extends")
        return frames


def _id_of(ref: str) -> str:
    base, _, version = str(ref).rpartition(":")
    return base if base and "." in version else str(ref)


def _load_dir(directory: Path) -> Dict[str, Dict[str, Any]]:
    """Every YAML spec of a directory, and of its subdirectories, by id."""
    specs: Dict[str, Dict[str, Any]] = {}
    if not directory.is_dir():
        return specs
    for path in sorted(directory.rglob("*.yaml")):
        spec = yaml.safe_load(path.read_text()) or {}
        if spec.get("id"):
            specs[str(spec["id"])] = spec
    return specs


#: This package's own catalogues, read once. They do not change while the
#: process runs, and reading them is every agent YAML of the repository.
_DEFAULTS: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _default_catalogue(name: str) -> Dict[str, Dict[str, Any]]:
    """One of this package's catalogues — `agents`, `fragments`, `frames` — by id."""
    if name not in _DEFAULTS:
        folder = _ROOT / name
        _DEFAULTS[name] = load_raw_frames(folder) if name == "frames" else _load_dir(folder)
    return _DEFAULTS[name]


def load_raw_cogs(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Cog YAML of a directory as plain data, by id, unresolved."""
    folder = directory or Path(__file__).parent
    raw: Dict[str, Dict[str, Any]] = {}
    for path in sorted(folder.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("id") != path.stem:
            raise CogError(f"{path.name}: the file is named for id {path.stem!r}, the spec says {data.get('id')!r}")
        raw[path.stem] = data
    return raw


def resolve_cog(
    cog: Dict[str, Any],
    *,
    agents: Optional[Dict[str, Dict[str, Any]]] = None,
    fragments: Optional[Dict[str, Dict[str, Any]]] = None,
    frames: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """One Cog, flat: the agent it extends, its own changes, and its Frames.

    The result is an agent spec — every field an agent has, resolved — and
    four more: ``agent``, the id of the agent it extends; ``frames``, the
    Frames it names; ``kind``; and ``frame_context``, the merged context of
    those Frames, with their Guards. The Frames' skills, tools and MCP servers
    are appended to the agent's, and their context, rendered, to its system
    prompt.

    Parameters
    ----------
    cog
        The Cog as written.
    agents, fragments, frames
        The catalogues to resolve against, by id; this package's when omitted.
    """
    agents = agents if agents is not None else _default_catalogue("agents")
    fragments = fragments if fragments is not None else _default_catalogue("fragments")
    frames = frames if frames is not None else _default_catalogue("frames")
    spec = CogSpec(**cog)

    if spec.kind not in RESOLVABLE_KINDS:
        raise CogError(
            f"Cog {spec.id!r} is of kind {spec.kind.value!r}, which cannot be resolved yet: "
            "only a `context` Cog — an agent equipped with Frames — can"
        )
    if spec.id in agents:
        raise CogError(f"Cog {spec.id!r} has the id of an agent: a Cog extends an agent, it does not replace one")
    agent_id = _id_of(spec.extends)
    if agent_id not in agents:
        raise CogError(f"Cog {spec.id!r} extends {spec.extends!r}, which is not an agent spec")
    try:
        # A copy: the catalogues are shared, and a resolved spec is the caller's.
        flat = copy.deepcopy(resolve_spec(cog, agents, fragments))
        context: FrameContext = compose_frames(spec.frames, frames)
    except (CompositionError, FrameError) as error:
        raise CogError(f"Cog {spec.id!r}: {error}") from error

    for field in ("skills", "backend_tools", "mcp_servers"):
        brought = getattr(context, field)
        if brought:
            flat[field] = merge_lists(list(flat.get(field) or []), list(brought))
    rendered = render_frames(context)
    flat["system_prompt"] = f"{str(flat.get('system_prompt') or '').strip()}\n\n{rendered}".strip() + "\n"

    flat.pop("includes", None)
    flat.pop("extends", None)
    flat.update(
        {
            "id": spec.id,
            "version": spec.version,
            "agent": agent_id,
            "frames": list(context.frames),
            "kind": spec.kind.value,
            "enabled": spec.enabled,
            "frame_context": context.model_dump(mode="json"),
        }
    )
    return flat


def load_cogs(directory: Optional[Path] = None) -> Dict[str, CogSpec]:
    """Every Cog of a directory, validated and checked to resolve, as it is written."""
    raw = load_raw_cogs(directory)
    for cog in raw.values():
        resolve_cog(cog)
    return {identity: CogSpec(**cog) for identity, cog in raw.items()}


_RAW_COGS: Dict[str, Dict[str, Any]] = load_raw_cogs()

#: Every Cog, by id, as it is written.
COG_CATALOGUE: Dict[str, CogSpec] = load_cogs()


def get_cog(cog_id: str) -> Optional[CogSpec]:
    """A Cog as it is written, by `id` or `id:version`, or None."""
    return COG_CATALOGUE.get(_id_of(cog_id))


def get_resolved_cog(cog_id: str) -> Optional[Dict[str, Any]]:
    """A Cog, flat — see `resolve_cog` — or None."""
    cog = _RAW_COGS.get(_id_of(cog_id))
    return None if cog is None else resolve_cog(cog)


def list_cogs() -> List[CogSpec]:
    """Every Cog, as it is written."""
    return list(COG_CATALOGUE.values())


def cogs_using(frame_id: str) -> List[CogSpec]:
    """The Cogs that work under a Frame, directly or through a Frame that extends it."""
    wanted = _id_of(frame_id)
    using = []
    for identity, cog in _RAW_COGS.items():
        context = compose_frames(cog["frames"])
        if wanted in context.lineage:
            using.append(COG_CATALOGUE[identity])
    return using


__all__ = [
    "COG_CATALOGUE",
    "CogError",
    "CogKind",
    "CogSpec",
    "RESOLVABLE_KINDS",
    "cogs_using",
    "get_cog",
    "get_resolved_cog",
    "list_cogs",
    "load_cogs",
    "load_raw_cogs",
    "resolve_cog",
]
