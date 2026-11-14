# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Battle specifications.

A *Battle* is two or more contestants — each a scene of the catalogue played
whole, or one application — given the same goal at the same instant, under one
clock, and a referee that says who won. It composes scenes: it is not a second
notion beside them, and a contestant that is a scene plays as it does on its
own stage.

Three variants, one referee contract. A **race** ends when the first contestant
reports done, or the clock does; a **challenge** runs every contestant to the
clock and measures each outcome with a Guard, the highest measure wins; a
**game** gives the contestants the controls of an arena drawn in the page —
Pong, Space Invaders — as frontend tools, and the arena keeps the score, which
decides.

A Battle refuses, as it is read: fewer than two contestants, or two with one
id; a contestant that names a scene and an app, or neither; a scene, an app or
a Guard the catalogue does not hold; a game without an arena, or in one that
keeps no score; a contestant played by a decision model that is not an
application in the browser of a game, that overrides its application, or
whose model is not of the catalogue or answers no typed decisions; a referee that does not decide as its variant does — a race by
`first_done`, a game by `score`, a challenge by `measure`; a challenge without
a measure Guard, or one whose Guard has no number signal; a clock under ten
seconds; an empty goal.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..colors import check_color
from ..guards import get_guard, id_of, load_raw
from ..overrides import check_overrides, override_model_problem


class BattleError(ValueError):
    """A Battle that cannot be used — named plainly."""


class BattleVariant(str, Enum):
    """What kind of contest a Battle is."""

    #: The first contestant to report done wins; the clock ending first is a draw.
    RACE = "race"
    #: The contestants play an arena; its score decides.
    GAME = "game"
    #: Every contestant runs to the clock; a Guard measures each outcome.
    CHALLENGE = "challenge"


class BattleArena(str, Enum):
    """The arenas a Battle may be played in, each drawn in the page with its frontend tools.

    A game is played in one and decided by its score (`pong`, `invaders`). A
    race or a challenge may name one too, as the visual the contestants work
    in: a `deck` each builds slide by slide, a `sheet` each fills cell by
    cell (the user, 6 November 2026).
    """

    PONG = "pong"
    INVADERS = "invaders"
    DECK = "deck"
    SHEET = "sheet"


#: The arenas that keep a score: the only ones a game may be played in.
SCORED_ARENAS = frozenset({BattleArena.PONG, BattleArena.INVADERS})


class BattleDecision(str, Enum):
    """How a referee decides."""

    FIRST_DONE = "first_done"
    SCORE = "score"
    MEASURE = "measure"


#: The one way each variant is decided.
DECISION_OF_VARIANT: Dict[BattleVariant, BattleDecision] = {
    BattleVariant.RACE: BattleDecision.FIRST_DONE,
    BattleVariant.GAME: BattleDecision.SCORE,
    BattleVariant.CHALLENGE: BattleDecision.MEASURE,
}

#: The shortest clock a Battle may run on, in seconds.
MIN_CLOCK_SECONDS = 10

_ID = re.compile(r"^[a-z][a-z0-9-]*$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BattleContestant(_Strict):
    """One side of a Battle: a scene of the catalogue played whole, or one application."""

    id: str = Field(..., description="Its id in the Battle: `blue`, `red`, `left`…")
    name: str = Field(default="", description="The name the audience sees; the id, capitalised, when unsaid")
    scene: str = Field(default="", description="A scene of the catalogue, `id` or `id:version`, played whole")
    app: str = Field(default="", description="An application of the catalogue, `id` or `id:version`")
    runs_in: Optional[Literal["browser", "runtime"]] = Field(
        default=None, description="For an app: where it runs; a scene's cast says it"
    )
    color: str = Field(default="", description="Its colour on stage: a palette name or a hex")
    overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="What this contestant plays differently of its application: `model`, `instructions`, `skills`, `context` — for a scene, of every member played in the page",
    )
    decision_model: str = Field(
        default="",
        description=(
            "A game's contestant played by a decision model, `provider:name` of one answering typed decisions "
            "(the user, 10 November 2026): the page asks it a choice on what the arena shows its side and makes "
            "the move it chooses; its application gives the face, its agent does not play"
        ),
    )

    @field_validator("overrides")
    @classmethod
    def _overridable(cls, overrides: Dict[str, Any], info: Any) -> Dict[str, Any]:
        return check_overrides(overrides, f"contestant {info.data.get('id', '?')!r}")

    @field_validator("id")
    @classmethod
    def _a_slug(cls, identity: str) -> str:
        if not _ID.match(identity):
            raise ValueError(f"a contestant's id is a slug, `blue` or `left`, not {identity!r}")
        return identity

    @field_validator("color")
    @classmethod
    def _a_color(cls, color: str) -> str:
        return check_color(color) if color else color

    @model_validator(mode="after")
    def _a_scene_or_an_app(self) -> "BattleContestant":
        if bool(self.scene) == bool(self.app):
            raise ValueError(
                f"contestant {self.id!r} names a scene or an app, never both and never neither"
            )
        if self.scene and self.runs_in is not None:
            raise ValueError(
                f"contestant {self.id!r} plays a scene: its cast says where it runs, `runs_in` does not"
            )
        if self.decision_model:
            if not self.app or self.runs_in != "browser":
                raise ValueError(
                    f"contestant {self.id!r} is played by a decision model: it is an application that runs in the browser, where the arena is"
                )
            if self.overrides:
                raise ValueError(
                    f"contestant {self.id!r} is played by a decision model: its application's agent does not play, so nothing of it is overridden"
                )
        return self

    @property
    def plays(self) -> str:
        """What it plays: the scene's or the app's reference."""
        return self.scene or self.app

    @property
    def shown_as(self) -> str:
        """The name the audience sees."""
        return self.name or self.id.capitalize()


class BattleReferee(_Strict):
    """How the winner is decided."""

    decides_by: BattleDecision = Field(..., description="`first_done`, `score` or `measure`")
    measure: str = Field(
        default="",
        description="For `measure`: the Guard whose number signal scores each outcome, `id` or `id:version`",
    )

    @model_validator(mode="after")
    def _a_measure_when_measured(self) -> "BattleReferee":
        if self.decides_by is BattleDecision.MEASURE and not self.measure:
            raise ValueError("a referee that decides by `measure` names the Guard that measures")
        if self.decides_by is not BattleDecision.MEASURE and self.measure:
            raise ValueError(f"a referee that decides by `{self.decides_by.value}` names no measure")
        return self


class BattleEval(_Strict):
    """An eval of the catalogue that confirms a contestant's result (the user, 7 November 2026).

    Run on every contestant once the referee has a verdict, with `config` as
    the evaluator reads it (`expected_output`, `max_duration_ms`, a `rubric`
    and a `threshold` for the judge); the winner is declared only when its
    evals all pass, else the result shows what failed and no winner.
    """

    eval: str = Field(..., description="An eval of the catalogue, `id` or `id:version`: `contains`, `max-duration`, `llm-judge`…")
    config: Dict[str, Any] = Field(default_factory=dict, description="What the evaluator is given: `expected_output`, `max_duration_ms`, `rubric`, `threshold`")
    says: str = Field(default="", description="What passing confirms, in a sentence")

    @field_validator("says")
    @classmethod
    def _one_line(cls, says: str) -> str:
        return " ".join(says.split())


class BattleRehearsal(_Strict):
    """The Battle's tests: what a played Battle has to show."""

    expects: List[str] = Field(default_factory=list, description="One sentence per expectation")


class BattleSpec(_Strict):
    """Specification for a Battle: the contestants, the goal, the clock, the referee."""

    id: str = Field(..., description="Unique Battle identifier")
    version: str = Field(default="0.0.1", description="Battle spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What the Battle shows")
    variant: BattleVariant = Field(..., description="`race`, `game` or `challenge`")
    goal: str = Field(..., description="What every contestant is told, in the same words")
    clock_seconds: int = Field(..., description=f"How long it may run, at least {MIN_CLOCK_SECONDS}")
    contestants: List[BattleContestant] = Field(..., description="Two or more")
    referee: BattleReferee = Field(..., description="How the winner is decided")
    arena: Optional[BattleArena] = Field(
        default=None,
        description="The arena drawn in the page: a game's, which keeps the score; a deck or a sheet the contestants work in",
    )
    evals: List[BattleEval] = Field(
        default_factory=list,
        description="The evals that confirm each contestant's result once the referee has a verdict; the winner is declared only when its evals pass",
    )
    rehearsal: BattleRehearsal = Field(default_factory=BattleRehearsal, description="Its tests")
    enabled: bool = Field(default=True, description="Whether it may be played today")
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="trophy", description="Icon identifier")
    emoji: str = Field(default="\U0001f3c1", description="Emoji representation")

    @field_validator("goal")
    @classmethod
    def _a_goal(cls, goal: str) -> str:
        if not goal.strip():
            raise ValueError("a Battle says its goal: what every contestant is told")
        return " ".join(goal.split())

    @field_validator("clock_seconds")
    @classmethod
    def _a_clock(cls, seconds: int) -> int:
        if seconds < MIN_CLOCK_SECONDS:
            raise ValueError(f"a Battle's clock is at least {MIN_CLOCK_SECONDS} seconds, not {seconds}")
        return seconds

    @field_validator("contestants")
    @classmethod
    def _two_or_more(cls, contestants: List[BattleContestant]) -> List[BattleContestant]:
        if len(contestants) < 2:
            raise ValueError("a Battle has at least two contestants")
        ids = [contestant.id for contestant in contestants]
        if len(set(ids)) != len(ids):
            raise ValueError("each contestant of a Battle has its own id")
        return contestants

    @model_validator(mode="after")
    def _decided_as_its_variant(self) -> "BattleSpec":
        expected = DECISION_OF_VARIANT[self.variant]
        if self.referee.decides_by is not expected:
            raise ValueError(
                f"a {self.variant.value} is decided by `{expected.value}`, "
                f"not `{self.referee.decides_by.value}`"
            )
        if self.variant is BattleVariant.GAME and self.arena is None:
            raise ValueError("a game names its arena: " + ", ".join(arena.value for arena in SCORED_ARENAS))
        if self.variant is BattleVariant.GAME and self.arena not in SCORED_ARENAS:
            raise ValueError(
                f"a game is played in an arena that keeps a score, {', '.join(sorted(a.value for a in SCORED_ARENAS))}; "
                f"`{self.arena.value}` keeps none"
            )
        decided = [contestant.id for contestant in self.contestants if contestant.decision_model]
        if decided and self.variant is not BattleVariant.GAME:
            raise ValueError(
                f"contestant {decided[0]!r} is played by a decision model, which plays a game's arena alone; "
                f"a {self.variant.value} has none to play"
            )
        return self

    @property
    def decides_by(self) -> BattleDecision:
        """How it is decided."""
        return self.referee.decides_by


def _check_references(battle: BattleSpec) -> None:
    """Every scene, app and Guard a Battle names is in the catalogue, at that version."""
    # Imported here: the scenes and apps catalogues are heavy, and a Battle
    # read on its own stays light.
    from ..apps import get_app  # noqa: PLC0415
    from ..models import get_model  # noqa: PLC0415
    from ..scenes import get_scene  # noqa: PLC0415

    def versioned(ref: str, found: Any, what: str) -> None:
        if found is None:
            raise BattleError(f"battle {battle.id!r} names {what} {ref!r}, which is not in the catalogue")
        base, _, version = ref.rpartition(":")
        if base and "." in version and found.version != version:
            raise BattleError(
                f"battle {battle.id!r} names {what} {ref!r}; the catalogue has version {found.version}"
            )

    for contestant in battle.contestants:
        if contestant.scene:
            versioned(contestant.scene, get_scene(contestant.scene), "a scene")
        else:
            versioned(contestant.app, get_app(contestant.app), "an app")
        said = override_model_problem(contestant.overrides, f"battle {battle.id!r}'s contestant {contestant.id!r}")
        if said:
            raise BattleError(said)
        if contestant.decision_model:
            decider = get_model(contestant.decision_model)
            if decider is None:
                raise BattleError(
                    f"battle {battle.id!r}'s contestant {contestant.id!r} is played by {contestant.decision_model!r}, which is not a model of the catalogue"
                )
            if "decisions" not in decider.capabilities:
                raise BattleError(
                    f"battle {battle.id!r}'s contestant {contestant.id!r} is played by {contestant.decision_model!r}, which answers no typed decisions"
                )
    for one in battle.evals:
        found = EVALS_RAW.get(id_of(one.eval))
        versioned(one.eval, _AsVersion(found) if found else None, "an eval")
        if found and id_of(one.eval) not in BATTLE_EVALS:
            raise BattleError(
                f"battle {battle.id!r} names eval {one.eval!r}, which a Battle cannot run: one of {', '.join(sorted(BATTLE_EVALS))}"
            )
    if battle.referee.measure:
        guard = get_guard(battle.referee.measure)
        versioned(battle.referee.measure, guard, "a Guard")
        assert guard is not None
        if not any(signal.type == "number" for signal in guard.signals):
            raise BattleError(
                f"battle {battle.id!r} measures with Guard {guard.id!r}, which has no number signal"
            )


#: The evals a Battle runs where it plays, on each contestant's result: the
#: expected-output checks, the clock, and the judge with a rubric. The others
#: of the catalogue need a trace or a report a Battle does not have.
BATTLE_EVALS = frozenset({"contains", "equals", "equals-expected", "max-duration", "llm-judge"})

#: The evals of the catalogue, as plain data by id: a Battle's `evals` name them.
EVALS_RAW: Dict[str, Dict[str, Any]] = load_raw(Path(__file__).parent.parent / "evals")


class _AsVersion:
    """A raw spec, read for its version as a model is."""

    def __init__(self, raw: Dict[str, Any]) -> None:
        self.version = str(raw.get("version", "0.0.1"))


def load_raw_battles(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Battle YAML of a directory as plain data, by id."""
    return load_raw(directory or Path(__file__).parent)


def load_battles(directory: Optional[Path] = None, check: bool = True) -> Dict[str, BattleSpec]:
    """Every Battle of a directory, validated; with `check`, its references too."""
    battles = {identity: BattleSpec(**battle) for identity, battle in load_raw_battles(directory).items()}
    if check:
        for battle in battles.values():
            _check_references(battle)
    return battles


#: Every Battle, by id.
BATTLE_CATALOGUE: Dict[str, BattleSpec] = load_battles()


def get_battle(battle_id: str) -> Optional[BattleSpec]:
    """A Battle, by `id` or `id:version`, or None."""
    return BATTLE_CATALOGUE.get(id_of(battle_id))


def list_battles(variant: Optional[BattleVariant] = None) -> List[BattleSpec]:
    """Every Battle, or those of one variant."""
    return [battle for battle in BATTLE_CATALOGUE.values() if variant is None or battle.variant is variant]


__all__ = [
    "BATTLE_CATALOGUE",
    "BATTLE_EVALS",
    "DECISION_OF_VARIANT",
    "MIN_CLOCK_SECONDS",
    "SCORED_ARENAS",
    "BattleArena",
    "BattleContestant",
    "BattleDecision",
    "BattleError",
    "BattleEval",
    "BattleReferee",
    "BattleRehearsal",
    "BattleSpec",
    "BattleVariant",
    "check_battle",
    "get_battle",
    "list_battles",
    "load_battles",
    "load_raw_battles",
]


def check_battle(battle: BattleSpec) -> BattleSpec:
    """A Battle whose references are all in the catalogue; raised otherwise."""
    _check_references(battle)
    return battle
