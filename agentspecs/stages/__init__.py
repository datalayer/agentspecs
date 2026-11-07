# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Stage specifications.

A *Stage* is something of the catalogue put on stage: a scene played whole,
one application, or a Battle — and where it plays. It composes what the
catalogue already holds; it is not a second notion beside Scenes,
Applications and Battles. A Stage says:

- what is on it: exactly one of `scene`, `app` and `battle`, by `id` or
  `id:version`;
- where its members play on Datalayer: `deployments`, each member of the
  scene (or the application itself) to the slug of the deployment that
  answers for it — the demo account's, for the Stages Datalayer keeps
  running; nothing for a scripted scene, which plays in the page, and
  nothing for a Battle, which plays on the visitor's own key;
- whether it has a page of its own that needs no account: `public`.

Its name, its face and its description are what it stages says of itself,
unless the Stage says otherwise.

A Stage refuses, as it is read: two of `scene`, `app` and `battle`, or none;
a scene, an application or a Battle the catalogue does not hold; a member in
`deployments` that is not on the scene's stage; deployments on a scripted
scene or on a Battle; an id or a slug that is not one.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..guards import id_of, load_raw


class StageError(ValueError):
    """A Stage that cannot be used — named plainly."""


class StageKind(str, Enum):
    """What is on a Stage."""

    #: A scene of the catalogue, played whole.
    SCENE = "scene"
    #: One application of the catalogue.
    APP = "app"
    #: A Battle of the catalogue.
    BATTLE = "battle"


_ID = re.compile(r"^[a-z][a-z0-9-]*$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StageSpec(_Strict):
    """Specification for a Stage: what is on it, where it plays, who may watch."""

    id: str = Field(..., description="Unique Stage identifier")
    version: str = Field(default="0.0.1", description="Stage spec version")
    name: str = Field(default="", description="Display name; what it stages is named when unsaid")
    description: str = Field(default="", description="What it shows; what it stages says when unsaid")
    scene: str = Field(default="", description="A scene of the catalogue, `id` or `id:version`, played whole")
    app: str = Field(default="", description="An application of the catalogue, `id` or `id:version`")
    battle: str = Field(default="", description="A Battle of the catalogue, `id` or `id:version`")
    deployments: Dict[str, str] = Field(
        default_factory=dict,
        description="Each member on a runtime to the slug of the deployment that answers for it on Datalayer",
    )
    public: bool = Field(default=False, description="Whether it has a page of its own that needs no account")
    enabled: bool = Field(default=True, description="Whether it may be watched today")
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="", description="Icon identifier; what it stages has when unsaid")
    emoji: str = Field(default="", description="Its face: one emoji; what it stages wears when unsaid")

    @field_validator("id")
    @classmethod
    def _a_slug(cls, identity: str) -> str:
        if not _ID.match(identity):
            raise ValueError(f"a Stage's id is a slug, `sales-and-accounting`, not {identity!r}")
        return identity

    @field_validator("deployments")
    @classmethod
    def _slugs(cls, deployments: Dict[str, str]) -> Dict[str, str]:
        for member, slug in deployments.items():
            if not _ID.match(member):
                raise ValueError(f"a deployment names a member by its id, a slug, not {member!r}")
            if not _ID.match(slug):
                raise ValueError(f"member {member!r} is deployed at a slug, `demo-accounting`, not {slug!r}")
        return deployments

    @model_validator(mode="after")
    def _one_thing_on_it(self) -> "StageSpec":
        named = [kind for kind, ref in (("scene", self.scene), ("app", self.app), ("battle", self.battle)) if ref]
        if len(named) != 1:
            raise ValueError(
                f"stage {self.id!r} puts one thing on stage: a `scene`, an `app` or a `battle`, "
                f"not {', '.join(named) if named else 'nothing'}"
            )
        if self.battle and self.deployments:
            raise ValueError(f"stage {self.id!r} stages a Battle, which plays on the visitor's key: it names no deployments")
        return self

    @property
    def kind(self) -> StageKind:
        """What is on it."""
        return StageKind.SCENE if self.scene else StageKind.APP if self.app else StageKind.BATTLE

    @property
    def stages(self) -> str:
        """What it stages: the scene's, the app's or the Battle's reference."""
        return self.scene or self.app or self.battle


def _versioned(stage: StageSpec, ref: str, found: Any, what: str) -> Any:
    """What a reference names, in the catalogue at that version; raised otherwise."""
    if found is None:
        raise StageError(f"stage {stage.id!r} names {what} {ref!r}, which is not in the catalogue")
    base, _, version = ref.rpartition(":")
    if base and "." in version and found.version != version:
        raise StageError(f"stage {stage.id!r} names {what} {ref!r}; the catalogue has version {found.version}")
    return found


def _members_of(scene: Any) -> List[str]:
    """The ids of a scene's members: its cast's, or its team's when it writes no cast."""
    members = [member.member for member in getattr(scene, "cast", []) or []]
    if not members and getattr(scene, "team", ""):
        from ..teams import get_team  # noqa: PLC0415

        team = get_team(scene.team)
        members = [member.id for member in team.members] if team is not None else []
    return members


def staged_of(stage: StageSpec) -> Any:
    """What a Stage stages, from the catalogue: the scene, the app or the Battle; raised when it is not there."""
    # Imported here: the catalogues are heavy, and a Stage read on its own stays light.
    if stage.scene:
        from ..scenes import get_scene  # noqa: PLC0415

        return _versioned(stage, stage.scene, get_scene(stage.scene), "a scene")
    if stage.app:
        from ..apps import get_app  # noqa: PLC0415

        return _versioned(stage, stage.app, get_app(stage.app), "an app")
    from ..battles import get_battle  # noqa: PLC0415

    return _versioned(stage, stage.battle, get_battle(stage.battle), "a Battle")


def _check_references(stage: StageSpec) -> Any:
    """What a Stage names is in the catalogue, and its deployments are its members'."""
    staged = staged_of(stage)
    if stage.scene:
        kind = getattr(staged, "kind", None)
        if getattr(kind, "value", kind) == "scripted" and stage.deployments:
            raise StageError(f"stage {stage.id!r} stages a scripted scene, which plays in the page: it names no deployments")
        members = _members_of(staged)
        for member in stage.deployments:
            if members and member not in members:
                raise StageError(
                    f"stage {stage.id!r} deploys {member!r}, who is not on the stage of scene {staged.id!r} "
                    f"({', '.join(members)})"
                )
    elif stage.app:
        for member in stage.deployments:
            if member != staged.id:
                raise StageError(f"stage {stage.id!r} deploys {member!r}; the one application on it is {staged.id!r}")
    return staged


def resolve_stage(stage: StageSpec) -> StageSpec:
    """A Stage with its name, description, icon and face: its own, or what it stages says."""
    staged = _check_references(stage)
    filled = {
        "name": stage.name or getattr(staged, "name", "") or stage.id,
        "description": " ".join(str(stage.description or getattr(staged, "description", "") or "").split()),
        "icon": stage.icon or str(getattr(staged, "icon", "") or ""),
        "emoji": stage.emoji or str(getattr(staged, "emoji", "") or ""),
    }
    return stage.model_copy(update=filled)


def check_stage(stage: StageSpec) -> StageSpec:
    """A Stage whose references are all in the catalogue; raised otherwise."""
    _check_references(stage)
    return stage


def load_raw_stages(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Stage YAML of a directory as plain data, by id."""
    return load_raw(directory or Path(__file__).parent)


def load_stages(directory: Optional[Path] = None, check: bool = True) -> Dict[str, StageSpec]:
    """Every Stage of a directory, validated; with `check`, its references too, and each resolved."""
    stages = {identity: StageSpec(**stage) for identity, stage in load_raw_stages(directory).items()}
    if check:
        stages = {identity: resolve_stage(stage) for identity, stage in stages.items()}
    return stages


#: Every Stage, by id, resolved.
STAGE_CATALOGUE: Dict[str, StageSpec] = load_stages()


def get_stage(stage_id: str) -> Optional[StageSpec]:
    """A Stage, by `id` or `id:version`, or None."""
    return STAGE_CATALOGUE.get(id_of(stage_id))


def list_stages(kind: Optional[StageKind] = None, public: Optional[bool] = None) -> List[StageSpec]:
    """Every Stage, or those of one kind, or the public ones."""
    return [
        stage
        for stage in STAGE_CATALOGUE.values()
        if (kind is None or stage.kind is kind) and (public is None or stage.public is public)
    ]


__all__ = [
    "STAGE_CATALOGUE",
    "StageError",
    "StageKind",
    "StageSpec",
    "check_stage",
    "get_stage",
    "list_stages",
    "load_raw_stages",
    "load_stages",
    "resolve_stage",
    "staged_of",
]
