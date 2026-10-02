# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Frame specifications.

A *Frame* is the context work happens in, written down: the rules, the
vocabulary, the goals, the style and the norms of an organization, a
department, a team, a project, a role or a relationship — and the skills, the
tools, the prompts and the Guards that put that context to work. It is read by
people and applied by Cogs (``agentspecs.cogs``). The idea, and the words, are
the Intelligence Hub whitepaper's (section 4.3).

A Frame is not a prompt. It has an owner who answers for it, a scope it
applies to and nowhere else, and a version; it is inherited and composed
rather than copied.

Two ideas carry the design, and both reuse what the catalogue already does.

**A Frame inherits with** ``extends``, exactly as an agent spec does
(``docs/modularity/extension``): one parent, a chain at most three deep, a
cycle refused by name. A project Frame extends its department's, which extends
the company's, so the chain of authority is a chain a person can read. Lists
append and are deduplicated, a child's scalar wins, ``terminology`` and
``guards`` merge entry by entry, and ``!remove`` / ``!replace`` say the rare
cases where appending is wrong.

**Several Frames compose.** A Cog names the Frames it works under, in order;
``compose_frames`` resolves each and merges them into the one context the Cog
is given. Two Frames that extend the same parent bring its rules once.

Resolution is done here, when the catalogue is read, so what reaches a runtime
is flat: a consumer never meets an unresolved ``extends``.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

#: How deep a chain of `extends` may go: the limit agent specs have.
MAX_EXTENDS_DEPTH = 3

#: Markers a child uses where appending to its parent's list is wrong.
REMOVE_PREFIX = "!remove "
REPLACE_MARKER = "!replace"

#: The fields of a Frame that are lists of text or of references: a child's
#: entries are appended to its parent's, deduplicated.
LIST_FIELDS = (
    "tags",
    "rules",
    "goals",
    "style",
    "norms",
    "process",
    "skills",
    "tools",
    "mcp_servers",
)


class FrameError(ValueError):
    """A Frame, or a graph of Frames, that cannot be resolved — named plainly."""


class FrameScope(str, Enum):
    """What a Frame applies to.

    A Frame applies where it should and not where it should not, so every one
    says which of these it is for.
    """

    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    TEAM = "team"
    PROJECT = "project"
    ROLE = "role"
    RELATIONSHIP = "relationship"


class GuardCategory(str, Enum):
    """What a Guard verifies: the whitepaper's seven categories (section 5.5)."""

    ALGORITHMIC = "algorithmic"
    """An output against a deterministic rule or a known result."""

    SOURCE_GROUNDING = "source-grounding"
    """Claims are supported by approved evidence."""

    CONSENSUS = "consensus"
    """Independent Cogs, prompts or models agree."""

    EXPERT = "expert"
    """A person judges sampled or high-risk outputs."""

    POLICY_SAFETY = "policy-safety"
    """The work stays inside what is allowed."""

    REGRESSION_DRIFT = "regression-drift"
    """An update has not changed behavior unacceptably."""

    OUTCOME = "outcome"
    """The intended result is produced."""


class FrameGuard(BaseModel):
    """A check a Frame requires of the output of work done under it.

    A Frame declares its Guards; what runs them is a runtime's. ``required``
    says whether the output counts before the Guard has passed.
    """

    id: str = Field(..., description="Identity within the Frame, and across the Frames it is merged with")
    category: GuardCategory = Field(..., description="What kind of check it is")
    description: str = Field(..., description="What is checked, written so that a person or a Cog can run it")
    required: bool = Field(
        default=True,
        description="Whether the output counts only once this Guard has passed",
    )


class FramePrompt(BaseModel):
    """A reusable prompt fragment a Cog loads into its context."""

    id: str = Field(..., description="Identity within the Frame")
    text: str = Field(..., description="The fragment")


class FrameSpec(BaseModel):
    """Specification for a Frame."""

    id: str = Field(..., description="Unique Frame identifier")
    version: str = Field(default="0.0.1", description="Frame spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What context the Frame carries, and for whom")
    scope: FrameScope = Field(..., description="What the Frame applies to")
    owner: str = Field(
        ...,
        description="The person or the group that manages the Frame and answers for it",
    )
    extends: str = Field(
        default="",
        description="The parent Frame, `id` or `id:version`; empty for a Frame that stands alone",
    )
    tags: List[str] = Field(default_factory=list)
    enabled: bool = Field(default=True, description="Whether a Cog may name it today")

    icon: str = Field(default="organization", description="Icon identifier")
    emoji: str = Field(default="\U0001f5bc️", description="Emoji representation")

    # -- The context: the why and the what of the work ------------------------
    rules: List[str] = Field(
        default_factory=list,
        description="What is and is not acceptable within the scope",
    )
    terminology: Dict[str, str] = Field(
        default_factory=dict,
        description="The words, names and definitions of the scope, by term",
    )
    goals: List[str] = Field(default_factory=list, description="What success looks like")
    style: List[str] = Field(
        default_factory=list,
        description="Tone of voice, formatting conventions, brand expression",
    )
    norms: List[str] = Field(
        default_factory=list,
        description="The expectations about how work gets done",
    )

    # -- The artifacts: the how and the with-what -----------------------------
    skills: List[str] = Field(
        default_factory=list,
        description="Skills the work depends on, `id` or `id:version` in the skill catalogue",
    )
    tools: List[str] = Field(
        default_factory=list,
        description="Tools the Frame expects to be available, in the tool catalogue",
    )
    mcp_servers: List[str] = Field(
        default_factory=list,
        description="MCP servers the Frame expects to be available, in the MCP server catalogue",
    )
    guards: List[FrameGuard] = Field(
        default_factory=list,
        description="The checks the output of work done under the Frame has to pass",
    )
    prompts: List[FramePrompt] = Field(
        default_factory=list,
        description="Reusable prompt fragments loaded into a Cog's context",
    )
    architecture: str = Field(
        default="",
        description="The software and system context that orients the work",
    )
    process: List[str] = Field(
        default_factory=list,
        description="The business process the work follows, step by step",
    )

    @field_validator("owner")
    @classmethod
    def _is_owned(cls, owner: str) -> str:
        if not owner.strip():
            raise ValueError("a Frame names its owner: somebody answers for it")
        return owner

    @field_validator("guards")
    @classmethod
    def _guards_are_uniquely_named(cls, guards: List[FrameGuard]) -> List[FrameGuard]:
        seen = set()
        for guard in guards:
            if guard.id in seen:
                raise ValueError(f"duplicate guard id {guard.id!r}")
            seen.add(guard.id)
        return guards


# ---------------------------------------------------------------------------
# Inheritance and composition
# ---------------------------------------------------------------------------


def _key_of(entry: Any) -> str:
    """The identity of a list entry: a reference without its version, or the text."""
    text = str(entry)
    base, _, version = text.rpartition(":")
    return base if base and " " not in text and "." in version else text


def merge_lists(parent: List[Any], child: List[Any]) -> List[Any]:
    """The child's entries appended to the parent's, deduplicated, honouring the markers.

    ``!replace`` starts from nothing; ``!remove x`` drops one entry the parent
    brought. The same two markers an agent spec has.
    """
    if REPLACE_MARKER in child:
        return merge_lists([], [entry for entry in child if entry != REPLACE_MARKER])
    removals = {
        _key_of(str(entry)[len(REMOVE_PREFIX) :])
        for entry in child
        if isinstance(entry, str) and entry.startswith(REMOVE_PREFIX)
    }
    merged: List[Any] = []
    seen: set = set()
    for entry in [*parent, *child]:
        if isinstance(entry, str) and entry.startswith(REMOVE_PREFIX):
            continue
        key = _key_of(entry)
        if key in removals or key in seen:
            continue
        seen.add(key)
        merged.append(entry)
    return merged


def _merge_keyed(parent: List[Dict[str, Any]], child: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Two lists of entries merged by `id`, the child winning field by field."""
    by_id: Dict[str, Dict[str, Any]] = {}
    for entry in [*parent, *child]:
        identity = str(entry.get("id"))
        by_id[identity] = {**by_id.get(identity, {}), **entry}
    return list(by_id.values())


def merge_frames(parent: Dict[str, Any], child: Dict[str, Any]) -> Dict[str, Any]:
    """A child Frame merged onto its parent, both as plain data."""
    merged = dict(parent)
    for field, value in child.items():
        if field == "extends":
            continue
        if field in LIST_FIELDS and isinstance(value, list):
            merged[field] = merge_lists(list(parent.get(field) or []), value)
        elif field == "terminology" and isinstance(value, dict):
            merged[field] = {**(parent.get(field) or {}), **value}
        elif field in ("guards", "prompts") and isinstance(value, list):
            merged[field] = _merge_keyed(list(parent.get(field) or []), value)
        else:
            merged[field] = value
    return merged


def _lookup(ref: str, frames: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    frame = frames.get(_key_of(ref)) or frames.get(ref)
    if frame is None:
        known = ", ".join(sorted(frames)) or "nothing"
        raise FrameError(f"Frame {ref!r} is not defined (known: {known})")
    return frame


def resolve_frame(
    frame: Dict[str, Any],
    frames: Dict[str, Dict[str, Any]],
    *,
    _seen: tuple = (),
) -> Dict[str, Any]:
    """One Frame with its chain of `extends` flattened into it.

    The result keeps the Frame's own identity — its id, name, scope and owner
    — and carries `lineage`, the ids it inherited from, nearest parent first:
    the chain of authority, kept so that it can be audited.
    """
    identity = str(frame.get("id") or "")
    if identity in _seen:
        raise FrameError("Circular Frame inheritance: " + " → ".join([*_seen, identity]))
    if len(_seen) >= MAX_EXTENDS_DEPTH:
        raise FrameError(
            f"Frame inheritance deeper than {MAX_EXTENDS_DEPTH} at {identity!r}: "
            "a chain nobody can read is worse than a repeated rule"
        )
    parent_ref = frame.get("extends")
    if not parent_ref:
        return {**frame, "lineage": []}
    parent = resolve_frame(_lookup(str(parent_ref), frames), frames, _seen=(*_seen, identity))
    resolved = merge_frames(parent, frame)
    resolved["lineage"] = [str(parent["id"]), *parent["lineage"]]
    return resolved


class FrameContext(BaseModel):
    """What a Cog is given: the Frames it works under, resolved and merged."""

    frames: List[str] = Field(default_factory=list, description="The Frames named, in order")
    lineage: List[str] = Field(
        default_factory=list,
        description="Every Frame that contributed, the named ones and those they inherit from",
    )
    names: Dict[str, str] = Field(default_factory=dict, description="The display name of each contributing Frame")
    owners: Dict[str, str] = Field(default_factory=dict, description="Who answers for each contributing Frame")
    rules: List[str] = Field(default_factory=list)
    terminology: Dict[str, str] = Field(default_factory=dict)
    goals: List[str] = Field(default_factory=list)
    style: List[str] = Field(default_factory=list)
    norms: List[str] = Field(default_factory=list)
    process: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    mcp_servers: List[str] = Field(default_factory=list)
    guards: List[FrameGuard] = Field(default_factory=list)
    prompts: List[FramePrompt] = Field(default_factory=list)
    architecture: str = Field(default="")


def compose_frames(
    refs: Iterable[str],
    frames: Optional[Dict[str, Dict[str, Any]]] = None,
) -> FrameContext:
    """The one context several Frames make, in the order they are named.

    Each is resolved, then merged onto the ones before it by the rules of
    inheritance: lists append and are deduplicated — so a parent two Frames
    share brings its rules once — and a later Frame's term or guard wins.
    """
    catalogue = frames if frames is not None else _RAW_FRAMES
    merged: Dict[str, Any] = {}
    named: List[str] = []
    lineage: List[str] = []
    architecture: List[str] = []
    for ref in refs:
        frame = resolve_frame(_lookup(str(ref), catalogue), catalogue)
        identity = str(frame["id"])
        if identity in named:
            raise FrameError(f"Frame {identity!r} is named twice")
        named.append(identity)
        for contributor in [*reversed(frame["lineage"]), identity]:
            if contributor not in lineage:
                lineage.append(contributor)
        text = str(frame.get("architecture") or "").strip()
        if text and text not in architecture:
            architecture.append(text)
        merged = merge_frames(
            merged,
            {key: value for key, value in frame.items() if key in LIST_FIELDS or key in ("terminology", "guards", "prompts")},
        )
    merged.pop("tags", None)
    return FrameContext(
        frames=named,
        lineage=lineage,
        names={identity: str(catalogue[identity].get("name") or identity) for identity in lineage},
        owners={identity: str(catalogue[identity].get("owner") or "") for identity in lineage},
        architecture="\n\n".join(architecture),
        **merged,
    )


def render_frames(context: FrameContext) -> str:
    """A Frame context as text: what is added to a Cog's instructions.

    Markdown, one section per kind of context, only the sections that have
    something in them. Skills, tools and MCP servers are not rendered: they
    are capability a Cog is given, not something it is told.
    """
    if not context.frames:
        return ""
    lines = [
        "## Frames",
        "",
        "You work under these Frames. They carry the context, the rules and the "
        "vocabulary of the people you work for, and they take precedence over "
        "your defaults.",
        "",
    ]
    for identity in context.lineage:
        owner = context.owners.get(identity)
        lines.append(f"- {context.names.get(identity, identity)}" + (f" — owned by {owner}" if owner else ""))

    def section(title: str, entries: Iterable[str], *, numbered: bool = False) -> None:
        entries = [str(entry).strip() for entry in entries if str(entry).strip()]
        if not entries:
            return
        lines.extend(["", f"### {title}", ""])
        for position, entry in enumerate(entries, start=1):
            lines.append(f"{position}. {entry}" if numbered else f"- {entry}")

    section("Rules", context.rules)
    section("Terminology", [f"**{term}**: {meaning}" for term, meaning in context.terminology.items()])
    section("Goals", context.goals)
    section("Style", context.style)
    section("Norms", context.norms)
    section("Process", context.process, numbered=True)
    if context.architecture:
        lines.extend(["", "### Architecture", "", context.architecture])
    for prompt in context.prompts:
        lines.extend(["", prompt.text.strip()])
    section(
        "Guards",
        [
            f"**{guard.id}** ({guard.category.value}{', required' if guard.required else ''}): {guard.description.strip()}"
            for guard in context.guards
        ],
    )
    if context.guards:
        lines.extend(["", "Check your output against every Guard before you hand it over, and say which you could not satisfy."])
    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# The catalogue
# ---------------------------------------------------------------------------


def load_raw_frames(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Frame YAML of a directory as plain data, by id, unresolved."""
    folder = directory or Path(__file__).parent
    raw: Dict[str, Dict[str, Any]] = {}
    for path in sorted(folder.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("id") != path.stem:
            raise FrameError(f"{path.name}: the file is named for id {path.stem!r}, the spec says {data.get('id')!r}")
        raw[path.stem] = data
    return raw


def load_frames(directory: Optional[Path] = None) -> Dict[str, FrameSpec]:
    """Every Frame of a directory, validated, as it is written (not resolved)."""
    raw = load_raw_frames(directory)
    for frame in raw.values():
        resolve_frame(frame, raw)
    return {identity: FrameSpec(**frame) for identity, frame in raw.items()}


_RAW_FRAMES: Dict[str, Dict[str, Any]] = load_raw_frames()

#: Every Frame, by id, as it is written.
FRAME_CATALOGUE: Dict[str, FrameSpec] = load_frames()


def get_frame(frame_id: str) -> Optional[FrameSpec]:
    """A Frame as it is written, by `id` or `id:version`, or None."""
    return FRAME_CATALOGUE.get(_key_of(frame_id))


def get_resolved_frame(frame_id: str) -> Optional[FrameSpec]:
    """A Frame with everything it inherits flattened into it, or None."""
    frame = _RAW_FRAMES.get(_key_of(frame_id))
    if frame is None:
        return None
    resolved = resolve_frame(frame, _RAW_FRAMES)
    return FrameSpec(**{key: value for key, value in resolved.items() if key != "lineage"})


def frame_lineage(frame_id: str) -> List[str]:
    """The Frames one inherits from, nearest parent first."""
    frame = _RAW_FRAMES.get(_key_of(frame_id))
    return [] if frame is None else list(resolve_frame(frame, _RAW_FRAMES)["lineage"])


def list_frames() -> List[FrameSpec]:
    """Every Frame, as it is written."""
    return list(FRAME_CATALOGUE.values())


__all__ = [
    "FRAME_CATALOGUE",
    "MAX_EXTENDS_DEPTH",
    "FrameContext",
    "FrameError",
    "FrameGuard",
    "FramePrompt",
    "FrameScope",
    "FrameSpec",
    "GuardCategory",
    "compose_frames",
    "frame_lineage",
    "get_frame",
    "get_resolved_frame",
    "list_frames",
    "load_frames",
    "load_raw_frames",
    "merge_frames",
    "merge_lists",
    "render_frames",
    "resolve_frame",
]
