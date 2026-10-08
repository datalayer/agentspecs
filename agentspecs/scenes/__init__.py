# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Scene specifications: the scene spec.

A *scene* stages a team (LOOP A-11, decided 2026-10-07). The team says who is
on stage — its members, their roles, who asks whom over what
(:mod:`agentspecs.teams`); the scene says what happens there, and nothing of
membership twice. What a scene spec holds:

- **who** — ``team``, the team it stages, or a ``cast`` written inline that
  makes one; on either, each cast member's ``persona`` on stage (the name the
  audience sees, its face, one line of *who I am here*) and its ``brief``,
  laid over its application's instructions;
- **its face** — ``name``, ``description``, ``icon`` and ``emoji``, exactly as
  an application has them: the tabs and the lists draw the emoji before the
  name;
- **the setting** — the systems on stage (the MCP servers the cast reaches,
  each with the name the audience reads), the shared Frames, the data in
  play, the period and the language, and ``assumes``: what the audience is
  told before it starts;
- **the script** — beats, in order: a ``cue`` (an opener the audience may
  say, a schedule or an event), the ``moves`` (who asks whom over what, for
  what, with which tool, and what kind of answer comes back), ``expect`` in
  words, ``narration`` for the audience, what the beat ``shows`` — a table, a
  chart, a notebook — so the page can promise it, its ``pace``, and the
  ``branch`` it may take on a ``decision``;
- **the stage directions** — where each member stands, whose balloon opens
  first, what the transcript shows and withholds, which inspectors are
  offered, how long the scene plays before it rests;
- **the audience** — who may watch and ask, and what an ask may cost;
- **the rehearsal** — for each beat, the shape the transcript must take, the
  words that must and must not appear, the time it may take; a recording for
  when the scene cannot play live; what was ``verified``;
- **the deployment** — under which account the scene plays, on which page,
  and where each member on a runtime is served, by the name of the variable
  its address is read from at build.

What is wrong is said in sentences (:func:`scene_problems`): a cast member
not in the team, a beat's mover not in the cast, a move over ``mcp`` to one
that is not a system, a cue nobody answers, a tool no connection offers, a
visitor audience on a scene whose runtime members have no address.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ..actions import ActionClass, matches, server_specs, server_tool_classes
from ..apps import APP_CATALOGUE, AppSpec, AppVerified, app_setup
from ..teams import (
    TeamExecutionMode,
    TeamLink,
    TeamMember,
    TeamPlace,
    TeamProtocol,
    TeamRole,
    TeamSpec,
    TeamSupervisor,
    get_team,
)

#: The version of the spec itself. A reader refuses one it does not know.
SCENE_SCHEMA = "loop.scene/v1"

#: Every version of the spec this package reads.
KNOWN_SCHEMAS = (SCENE_SCHEMA,)

#: How long something takes, as a person writes it: `30s`, `10m`, `1h`, `500ms`.
DURATION = r"[1-9]\d*(?:ms|s|m|h)"

#: The name of the variable an address is read from at build.
ADDRESS_VARIABLE = r"[A-Z][A-Z0-9_]*"

#: A language tag, `en` or `fr-BE`.
LANGUAGE = r"[a-z]{2,3}(?:-[A-Z]{2})?"

#: The audience, as the transcript names it (*You → Sales*).
AUDIENCE = "You"


class SceneError(ValueError):
    """A scene that cannot be played — named plainly."""


class _Strict(BaseModel):
    """A part of the spec: a key it does not know is a mistake, said as one."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _is_a_face(emoji: str, what: str) -> str:
    """One emoji, as an application's face is checked."""
    face = emoji.strip()
    if not face or len(face) > 16 or any(character.isalnum() or character.isspace() for character in face):
        raise ValueError(f"{what} is one emoji, its face")
    return face


# --- who is on stage -------------------------------------------------------------------


class ScenePersona(_Strict):
    """How a member appears to the audience, in this scene."""

    name: str = Field(default="", description="The name the audience sees; its application's when unsaid")
    face: str = Field(default="", description="One emoji; its application's when unsaid")
    line: str = Field(default="", description="One line of *who I am here*")

    @field_validator("face")
    @classmethod
    def _one_emoji(cls, face: str) -> str:
        return _is_a_face(face, "a persona's `face`") if face.strip() else ""


class SceneCastMember(_Strict):
    """A member of the cast.

    On a staged team, it names a member of the team (`member`) and says only
    how it appears here (`persona`) and what it is for in this scene
    (`brief`). Written inline — a scene with no `team` — it is the member:
    what it is (`app`, `ref` or `server`), its `role`, where it `runs_in`
    and whom it `talks_to`, as a team member says them.
    """

    member: str = Field(..., description="Its id: in the team, or in this cast")
    app: str = Field(default="", description="Inline: the application it is, `id` or `id:version`")
    ref: str = Field(default="", description="Inline: the agent it is, `id` or `id:version`")
    server: str = Field(default="", description="Inline: the MCP server it is, a system of the scene")
    role: Optional[TeamRole] = Field(default=None, description="Inline: what it is for, structurally")
    runs_in: Optional[TeamPlace] = Field(default=None, description="Inline: `browser` or `runtime`")
    talks_to: List[TeamLink] = Field(default_factory=list, description="Inline: whom it asks, and over what")
    persona: ScenePersona = Field(default_factory=ScenePersona, description="How it appears on stage")
    brief: str = Field(default="", description="What it is for in this scene, over its application's instructions")

    @property
    def is_defined(self) -> bool:
        """Whether the member is written here rather than taken from a team."""
        return bool(self.app or self.ref or self.server)

    def as_team_member(self) -> TeamMember:
        """The team member an inline cast member is."""
        return TeamMember(
            id=self.member,
            app=self.app,
            ref=self.ref,
            server=self.server,
            role=self.role or TeamRole.CONTRIBUTOR,
            runs_in=self.runs_in,
            talks_to=list(self.talks_to),
            name=self.persona.name,
            goal=self.brief,
        )


# --- the setting -----------------------------------------------------------------------


class SceneSystem(_Strict):
    """A system on stage: an MCP server of the catalogue the cast reaches."""

    server: str = Field(..., description="An MCP server of the catalogue, `id` or `id:version`")
    shown_as: str = Field(
        default="", alias="as", description="The name the audience reads on the graph and in the transcript"
    )
    holds: str = Field(default="", description="What it holds in this scene: *Datalayer's own books, March 2026*")

    @property
    def id(self) -> str:
        """The server's id, without its version."""
        return self.server.split(":")[0]

    @property
    def name(self) -> str:
        """What the audience reads: `as`, or the id."""
        return self.shown_as or self.id


class SceneSetting(_Strict):
    """The stage: what is on it, and what the audience is told."""

    systems: List[SceneSystem] = Field(default_factory=list, description="The systems the cast reaches")
    frames: List[str] = Field(default_factory=list, description="The Frames the scene plays under, over the team's")
    contents: List[str] = Field(default_factory=list, description="The data in play: documents and datasets")
    period: str = Field(default="", description="When the scene plays, in words: *March 2026*")
    language: str = Field(default="", pattern=rf"^(?:{LANGUAGE})?$", description="The language it plays in, `en`")
    assumes: str = Field(default="", description="What the audience is told before it starts, one line")

    def system(self, name: str) -> Optional[SceneSystem]:
        """A system by its id, its reference or the name the audience reads, whatever the case."""
        wanted = name.strip().lower()
        for system in self.systems:
            if wanted in (system.id, system.server.lower(), system.name.lower()):
                return system
        return None


# --- the script ------------------------------------------------------------------------


class SceneCue(_Strict):
    """What starts a beat: something the audience says, a schedule, or an event."""

    say: str = Field(default="", description="An opener the audience may say: the entry's suggestion on the page")
    schedule: str = Field(default="", description="A schedule, when the beat starts by itself")
    event: str = Field(default="", description="An event, when something happening starts it")

    @model_validator(mode="after")
    def _one_of_them(self) -> "SceneCue":
        if sum(1 for given in (self.say, self.schedule, self.event) if given.strip()) != 1:
            raise ValueError("a cue is one of `say`, `schedule` or `event`")
        return self

    @property
    def text(self) -> str:
        """The cue, whichever kind it is."""
        return (self.say or self.schedule or self.event).strip()


class AnswerKind(str, Enum):
    """What kind of answer comes back, and what the page shows."""

    WORDS = "words"
    TABLE = "table"
    CHART = "chart"
    NOTEBOOK = "notebook"
    MAP = "map"
    FILE = "file"
    IMAGE = "image"
    #: The sources it read, as cards that open (the catalog's Evidence).
    SOURCES = "sources"
    #: A choice as buttons that answer the application.
    CHOICE = "choice"
    #: A choice whose action does more than read: asked of a person, refused to a visitor.
    APPROVAL = "approval"


class Pace(str, Enum):
    """How fast a beat plays for the audience."""

    QUICK = "quick"
    STEADY = "steady"
    SLOW = "slow"


class SceneMove(_Strict):
    """One member asking another over a protocol, or answering the audience."""

    who: str = Field(..., description="The member moving, by its id in the cast")
    asks: str = Field(default="", description="Whom: a member or a system; nobody when it answers the audience")
    over: Optional[TeamProtocol] = Field(default=None, description="`a2a` to a member, `mcp` to a system")
    what: str = Field(default="", description="What it asks for, or what it answers, in words")
    tool: str = Field(default="", description="Over `mcp`: the tool, by name or pattern (`odoo_accounting_*`)")
    does: Optional[ActionClass] = Field(default=None, description="The kind of tool: `read`, `write`, …")
    answers: Optional[AnswerKind] = Field(default=None, description="What kind of answer comes back")

    @model_validator(mode="after")
    def _fits_together(self) -> "SceneMove":
        if not self.asks:
            if self.over is not None or self.tool or self.does is not None:
                raise ValueError(f"'{self.who}' answers the audience: no `over`, no `tool`, no `does`")
            if self.answers is None:
                raise ValueError(f"'{self.who}' answers the audience: say what kind of answer (`answers`)")
        elif (self.tool or self.does is not None) and self.over is TeamProtocol.A2A:
            raise ValueError(f"'{self.who}' asks '{self.asks}' over a2a: a tool is asked over mcp")
        return self


class SceneBranch(_Strict):
    """What a beat does instead when a decision holds."""

    decision: str = Field(..., description="When, in words: *the books hold no open invoice*")
    expect: str = Field(default="", description="What happens then, in words")
    moves: List[SceneMove] = Field(default_factory=list, description="The moves then, when they differ")
    then: str = Field(default="", description="The beat that follows, by id, when the script goes on elsewhere")


class SceneBeat(_Strict):
    """One beat of the script."""

    id: str = Field(..., description="Its id: what the rehearsal and a branch name")
    cue: SceneCue = Field(..., description="What starts it")
    narration: str = Field(default="", description="One line for the audience, read in the transcript")
    moves: List[SceneMove] = Field(default_factory=list, description="Who asks whom over what, in order")
    expect: str = Field(..., description="What should happen, in words")
    shows: List[AnswerKind] = Field(
        default_factory=list, description="What the page shows: the answers to the audience when unsaid"
    )
    pace: Optional[Pace] = Field(default=None, description="Its pace; the stage's when unsaid")
    branch: List[SceneBranch] = Field(default_factory=list, description="What it does instead, on a decision")

    @field_validator("expect")
    @classmethod
    def _says_something(cls, expect: str) -> str:
        if not expect.strip():
            raise ValueError("a beat says what to expect")
        return expect.strip()

    @property
    def shown(self) -> List[AnswerKind]:
        """What the beat shows: `shows`, else the kinds of its answers to the audience."""
        if self.shows:
            return list(self.shows)
        kinds: List[AnswerKind] = []
        for move in self.moves:
            if not move.asks and move.answers is not None and move.answers not in kinds:
                kinds.append(move.answers)
        return kinds


# --- the stage directions --------------------------------------------------------------


class StagePosition(_Strict):
    """Where a member stands: fractions of the box, left to right and top to bottom."""

    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)


class Withheld(str, Enum):
    """What the transcript does not show."""

    CREDENTIALS = "credentials"
    IDS = "ids"
    ADDRESSES = "addresses"
    AMOUNTS = "amounts"


class Inspector(str, Enum):
    """The inspectors a page may offer under a scene."""

    AGENT = "agent"
    TOOLS = "tools"
    A2A = "a2a"
    NOTEBOOK = "notebook"
    COST = "cost"


class SceneTranscript(_Strict):
    """What the transcript shows."""

    tools: bool = Field(default=True, description="Whether tool lines are shown")
    narration: bool = Field(default=True, description="Whether the beats' narration is read in it")
    withhold: List[Withheld] = Field(default_factory=list, description="Words withheld: credentials, ids, …")


class SceneStage(_Strict):
    """Directions for the page."""

    positions: Dict[str, StagePosition] = Field(default_factory=dict, description="Where each member stands")
    opens_first: str = Field(default="", description="Whose balloon opens first; the entry's when unsaid")
    transcript: SceneTranscript = Field(default_factory=SceneTranscript, description="What the transcript shows")
    inspectors: List[Inspector] = Field(default_factory=list, description="The inspectors offered")
    rests_after: str = Field(
        default="", pattern=rf"^(?:{DURATION})?$", description="How long the scene plays before it rests"
    )
    pace: Pace = Field(default=Pace.STEADY, description="The pace of the beats that say none")


# --- the audience ----------------------------------------------------------------------


class Watchers(str, Enum):
    """Who may watch and ask."""

    VISITORS = "visitors"
    SIGNED_IN = "signed-in"
    NOBODY = "nobody"


class SceneAudience(_Strict):
    """Who may watch and ask, and what an ask may cost."""

    who: Watchers = Field(default=Watchers.SIGNED_IN, description="`visitors`, `signed-in`, or `nobody`")
    ceiling_per_ask: float = Field(default=0, ge=0, description="What one ask may cost, in USD; the site's when 0")
    asks_a_day: int = Field(default=0, ge=0, description="How many asks a visitor gets a day; the site's when 0")


# --- the rehearsal ---------------------------------------------------------------------

_ASK = re.compile(r"^(?P<who>[^→:]+?)\s*→\s*(?P<whom>[^:]+?)(?::\s*(?P<detail>.+))?$")
_ANSWER = re.compile(r"^(?P<who>[^→:]+?):\s*(?P<detail>.+)$")
_KIND = re.compile(
    r"^(?:an?\s+)?(?P<kind>words|table|chart|notebook|map|file|image|sources|choice|approval)$"
)


@dataclass(frozen=True)
class TranscriptLine:
    """One line of the transcript's shape: who, whom (nobody for an answer), and the detail."""

    who: str
    whom: str = ""
    detail: str = ""

    @property
    def is_answer(self) -> bool:
        return not self.whom

    @property
    def kind(self) -> Optional[AnswerKind]:
        """The kind of answer the line names (*a table*), when it names one."""
        found = _KIND.match(self.detail.strip())
        return AnswerKind(found.group("kind")) if found else None


def parse_line(text: str) -> TranscriptLine:
    """A line of the transcript's shape, as the transcript writes it.

    *Sales → Accounting* (an ask), *Accounting → Odoo: odoo_accounting_\\** (a
    tool), *Accounting: a table* (an answer). Refused when it is neither.
    """
    asked = _ASK.match(text.strip())
    if asked:
        return TranscriptLine(asked.group("who").strip(), asked.group("whom").strip(), (asked.group("detail") or "").strip())
    answered = _ANSWER.match(text.strip())
    if answered:
        return TranscriptLine(answered.group("who").strip(), "", answered.group("detail").strip())
    raise ValueError(f"the line {text!r} is neither an ask (`A → B`) nor an answer (`A: …`)")


class RehearsalBeat(_Strict):
    """What a beat's transcript must look like."""

    beat: str = Field(..., description="The beat, by id")
    lines: List[str] = Field(
        default_factory=list,
        description="The shape, in order: `Sales → Accounting`, `Accounting → Odoo: odoo_accounting_*`, `Accounting: a table`",
    )
    must_say: List[str] = Field(default_factory=list, description="Words that must appear")
    must_not_say: List[str] = Field(default_factory=list, description="Words that must not")
    within: str = Field(default="", pattern=rf"^(?:{DURATION})?$", description="The time the beat may take")

    @field_validator("lines")
    @classmethod
    def _are_lines(cls, lines: List[str]) -> List[str]:
        for line in lines:
            parse_line(line)
        return lines

    def parsed(self) -> List[TranscriptLine]:
        """The lines, parsed."""
        return [parse_line(line) for line in self.lines]


class SceneRecording(_Strict):
    """A transcript recorded once, played when the scene cannot play live (LOOP H-08)."""

    path: str = Field(..., description="Its file, beside the scenes: `sales-and-accounting/recording.json`")
    taken: str = Field(default="", description="When it was recorded")
    note: str = Field(default="", description="What the audience is told: *recorded on 2026-10-07*")


class SceneRehearsal(_Strict):
    """The scene's tests: a passing rehearsal is the gallery's *Live*."""

    beats: List[RehearsalBeat] = Field(default_factory=list, description="Each beat's expected shape")
    within: str = Field(default="", pattern=rf"^(?:{DURATION})?$", description="The time the whole scene may take")
    recording: Optional[SceneRecording] = Field(default=None, description="A recording, for when it cannot play live")
    verified: AppVerified = Field(
        default_factory=lambda: AppVerified(),
        description="What was verified live, what runs on recorded data, and what is not verified yet",
    )


class ScenePlayedBeat(_Strict):
    """One beat of a rehearsal that was played: its verdict, in the Validate tab's words."""

    beat: str = Field(..., description="The beat, by id")
    state: str = Field(..., pattern=r"^(?:passed|failed|not_run)$", description="`passed`, `failed` or `not_run`")
    says: str = Field(default="", description="What differed, or why it was not run")
    seconds: float = Field(default=0.0, ge=0.0, description="How long it took")


class ScenePlayed(_Strict):
    """What came of the last rehearsal `loop scenes rehearse --cloud` played (LOOP A-14).

    Written by the command to the scene's file beside the specs
    (:func:`played_path`: ``<id>/rehearsal.json``), never by hand; read by
    :func:`scene_played`. A scene is *Live* when it ``passed``; one that did
    not says so with its ``says``. The hand-written ``verified`` sentences stay
    what a person says of the scene beside it.
    """

    at: str = Field(..., description="When it was played, ISO 8601")
    where: str = Field(default="on Datalayer", description="Where it was played: *on Datalayer*")
    passed: bool = Field(..., description="Whether every beat passed")
    says: str = Field(..., description="The verdict in one sentence: *Rehearsal: 4 of 4 beats passed. The scene is Live.*")
    beats: List[ScenePlayedBeat] = Field(default_factory=list, description="Each beat's verdict")
    runtime: str = Field(default="", description="The agent-runtimes that played it, by version")


# --- the deployment --------------------------------------------------------------------


class SceneDeployment(_Strict):
    """Where the scene plays."""

    account: str = Field(default="", description="Under which account the scene plays: `demo`")
    page: str = Field(default="", description="The page it plays on: the entry's address")
    addresses: Dict[str, str] = Field(
        default_factory=dict,
        description="For each member on a runtime, the variable its address is read from at build",
    )

    @field_validator("addresses")
    @classmethod
    def _are_variables(cls, addresses: Dict[str, str]) -> Dict[str, str]:
        for member, variable in addresses.items():
            if not re.fullmatch(ADDRESS_VARIABLE, variable):
                raise ValueError(f"the address of '{member}' is read from a variable, `DATALAYER_…_A2A_URL`")
        return addresses


# --- the scene -------------------------------------------------------------------------


class SceneSpec(_Strict):
    """Specification for a scene: a team, staged."""

    schema_: str = Field(default=SCENE_SCHEMA, alias="schema", description="The version of the spec itself")
    id: str = Field(..., description="Unique scene identifier")
    version: str = Field(default="0.0.1", description="Scene version")
    name: str = Field(..., description="Display name: the tab's")
    description: str = Field(default="", description="What happens in it, in a sentence")
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="people", description="Icon identifier")
    emoji: str = Field(default="\U0001f440", description="Its face: one emoji, drawn before its name")

    team: str = Field(default="", description="The team it stages, `id` or `id:version`")
    entry: str = Field(default="", description="The member the audience talks to; the team's entry when unsaid")
    cast: List[SceneCastMember] = Field(default_factory=list, description="The cast: personas and briefs, or the members")
    setting: SceneSetting = Field(default_factory=SceneSetting, description="The stage")
    script: List[SceneBeat] = Field(default_factory=list, description="The beats, in order")
    stage: SceneStage = Field(default_factory=SceneStage, description="Directions for the page")
    audience: SceneAudience = Field(default_factory=SceneAudience, description="Who may watch and ask")
    rehearsal: SceneRehearsal = Field(default_factory=SceneRehearsal, description="Its tests")
    deployment: SceneDeployment = Field(default_factory=SceneDeployment, description="Where it plays")

    @field_validator("schema_")
    @classmethod
    def _known(cls, schema: str) -> str:
        if schema not in KNOWN_SCHEMAS:
            raise ValueError(f"schema {schema!r} is not one this package reads: {', '.join(KNOWN_SCHEMAS)}")
        return schema

    @field_validator("emoji")
    @classmethod
    def _one_emoji(cls, emoji: str) -> str:
        return _is_a_face(emoji, "a scene's `emoji`")

    @model_validator(mode="after")
    def _stages_somebody(self) -> "SceneSpec":
        if not self.team and not self.cast:
            raise ValueError("the scene stages nobody: it names a `team`, or writes its `cast`")
        seen = set()
        for member in self.cast:
            if member.member in seen:
                raise ValueError(f"the cast names '{member.member}' twice")
            seen.add(member.member)
        beats = set()
        for beat in self.script:
            if beat.id in beats:
                raise ValueError(f"the script has two beats named '{beat.id}'")
            beats.add(beat.id)
        return self

    # -- what it stages ----------------------------------------------------------------

    def team_of(self) -> TeamSpec:
        """The team on stage: the one it names, or the one its cast makes.

        Raises:
            SceneError: when the team is not in the catalogue, or the cast makes none.
        """
        if self.team:
            team = get_team(self.team.split(":")[0])
            if team is None:
                raise SceneError(f"There is no team named {self.team!r}.")
            return team
        entry = self.entry or next(
            (member.member for member in self.cast if member.role is TeamRole.INITIATOR), self.cast[0].member
        )
        front = next((member for member in self.cast if member.member == entry), None)
        if front is None:
            raise SceneError(f"The scene enters at '{entry}', which is not in its cast.")
        try:
            return TeamSpec(
                id=self.id,
                version=self.version,
                name=self.name,
                description=self.description,
                tags=list(self.tags),
                icon=self.icon,
                emoji=self.emoji,
                orchestration_protocol="a2a",
                execution_mode=TeamExecutionMode.SUPERVISOR,
                supervisor=TeamSupervisor(name=front.persona.name or front.member, app=front.app, ref=front.ref),
                entry=entry,
                agents=[member.as_team_member() for member in self.cast],
            )
        except ValidationError as error:
            why = "; ".join(issue["msg"].removeprefix("Value error, ") for issue in error.errors())
            raise SceneError(f"Its cast makes no team: {why}") from None
        except ValueError as error:
            raise SceneError(f"Its cast makes no team: {error}") from None

    def entry_of(self, team: Optional[TeamSpec] = None) -> str:
        """The member the audience talks to."""
        team = team or self.team_of()
        return self.entry or team.entry or team.agents[0].id

    def cast_member(self, member_id: str) -> Optional[SceneCastMember]:
        """What the cast says of a member, or None."""
        for member in self.cast:
            if member.member == member_id:
                return member
        return None

    def cast_of(self) -> List[SceneCastMember]:
        """The whole cast, resolved: every member of the team, each with its persona filled.

        The persona's name is the cast's, else the application's, else the
        member's display name; its face the cast's, else the application's;
        the brief the cast's, else the member's goal in the team.
        """
        team = self.team_of()
        resolved: List[SceneCastMember] = []
        for member in team.agents:
            said = self.cast_member(member.id)
            app = APP_CATALOGUE.get(member.app.split(":")[0]) if member.app else None
            persona = said.persona if said else ScenePersona()
            resolved.append(
                SceneCastMember(
                    member=member.id,
                    app=member.app,
                    ref=member.ref,
                    server=member.server,
                    role=member.role,
                    runs_in=member.runs_in,
                    talks_to=list(member.talks_to),
                    persona=ScenePersona(
                        name=persona.name or (app.name if app else member.display_name),
                        face=persona.face or (app.emoji if app else ""),
                        line=persona.line,
                    ),
                    brief=(said.brief if said else "") or member.goal,
                )
            )
        return resolved

    def cues(self) -> List[str]:
        """What the audience may say, in the script's order: the entry's suggestions on the page."""
        return [beat.cue.say.strip() for beat in self.script if beat.cue.say.strip()]

    def beat(self, beat_id: str) -> Optional[SceneBeat]:
        """A beat by id, or None."""
        for beat in self.script:
            if beat.id == beat_id:
                return beat
        return None

    def referenced_servers(self) -> List[str]:
        """Every system of the setting, by reference."""
        return list(dict.fromkeys(system.server for system in self.setting.systems))

    def referenced_frames(self) -> List[str]:
        """Every Frame of the setting, in order."""
        return list(self.setting.frames)


# --- what is wrong, in sentences -------------------------------------------------------


def _id_of(ref: str) -> str:
    return ref.split(":")[0]


def _app_of(member: TeamMember) -> Optional[AppSpec]:
    return APP_CATALOGUE.get(_id_of(member.app)) if member.app else None


def _reaches(member: TeamMember, team: TeamSpec, server_id: str) -> bool:
    """Whether a member reaches a system: through its application's connection, or a team link."""
    app = _app_of(member)
    if app is not None and any(_id_of(connection.server) == server_id for connection in app.connections):
        return True
    for link in member.talks_to:
        asked = team.member(link.member)
        if link.over is TeamProtocol.MCP and asked is not None and _id_of(asked.server) == server_id:
            return True
    return False


def _tool_problem(member: TeamMember, name: str, server_id: str, tool: str, does: Optional[ActionClass]) -> Optional[str]:
    """Why a tool of a system is not one a member may use, or None."""
    app = _app_of(member)
    if app is not None:
        connections = [connection for connection in app.connections if _id_of(connection.server) == server_id]
        if connections and not any(connection.reaches(tool) for connection in connections):
            return f"'{tool}', a tool no connection of {name} offers."
    server = server_specs().get(server_id)
    declared = list(((server or {}).get("actions") or {}).get("tools") or {})
    if declared and not any(matches(known, tool) or matches(tool, known) for known in declared):
        return f"'{tool}', which {server_id} does not offer."
    if does is not None and server is not None and tool in declared:
        classes = server_tool_classes(server, tool, {})
        if classes and does not in classes:
            return f"'{tool}' to {does.value}, and it {', '.join(item.value for item in classes)}s."
    return None


def _names(scene: SceneSpec, cast: List[SceneCastMember]) -> Dict[str, str]:
    """Every name the transcript may use, to the id it stands for."""
    names: Dict[str, str] = {AUDIENCE: AUDIENCE}
    for member in cast:
        names[member.member] = member.member
        names[member.persona.name] = member.member
    for system in scene.setting.systems:
        names[system.id] = system.id
        names[system.server] = system.id
        names[system.name] = system.id
        names[system.name.lower()] = system.id
    return names


def scene_problems(scene: SceneSpec) -> List[str]:
    """What stops a scene from being played, in sentences; empty when nothing does."""
    from ..frames import get_frame

    problems: List[str] = []
    try:
        team = scene.team_of()
    except SceneError as error:
        return [str(error)]
    ids = {member.id for member in team.agents}
    if scene.team:
        for said in scene.cast:
            if said.member not in ids:
                problems.append(f"The cast names '{said.member}', which is not a member of the team '{team.id}'.")
            elif said.is_defined or said.role is not None or said.runs_in is not None or said.talks_to:
                problems.append(
                    f"The cast member '{said.member}' is the team's: it says its persona and its brief, nothing of what it is."
                )
    if scene.entry and scene.entry not in ids:
        problems.append(f"The scene enters at '{scene.entry}', which is not in its cast.")
    entry = scene.entry_of(team)
    front = team.member(entry)
    if front is not None and front.is_server:
        problems.append(f"The scene enters at '{entry}', a system: the audience talks to an agent.")
    cast = scene.cast_of()
    faces = [member.persona.face for member in cast if member.persona.face]
    if scene.emoji in faces:
        problems.append(f"The scene wears {scene.emoji}, a member's face: a scene has a face of its own.")
    # The setting.
    systems = {system.id: system for system in scene.setting.systems}
    for system in scene.setting.systems:
        if system.id not in server_specs():
            problems.append(f"There is no MCP server named {system.server!r}.")
        elif not any(_reaches(member, team, system.id) or _id_of(member.server) == system.id for member in team.agents):
            problems.append(f"The system '{system.name}' ({system.id}) is on stage, and no member of the cast reaches it.")
    for ref in scene.setting.frames:
        if get_frame(_id_of(ref)) is None:
            problems.append(f"There is no Frame named {ref!r}.")
    # The script.
    links = {(who, whom) for who, whom, _ in team.links()}
    beats = {beat.id for beat in scene.script}
    for beat in scene.script:
        answered = False
        for move in beat.moves + [move for branch in beat.branch for move in branch.moves]:
            problems.extend(_move_problems(beat, move, team, scene.setting, links, cast))
            answered = answered or move.who == entry
        if not answered:
            problems.append(f"Beat '{beat.id}': its cue is answered by nobody — no move is the entry's ('{entry}').")
        for branch in beat.branch:
            if branch.then and branch.then not in beats:
                problems.append(f"Beat '{beat.id}': its branch goes on to '{branch.then}', which is no beat.")
    # The stage directions.
    for member_id in scene.stage.positions:
        if member_id not in ids:
            problems.append(f"The stage places '{member_id}', which is not in the cast.")
    if scene.stage.opens_first and scene.stage.opens_first not in ids:
        problems.append(f"The balloon of '{scene.stage.opens_first}' opens first, and it is not in the cast.")
    # The audience, and where the scene plays.
    for member_id in scene.deployment.addresses:
        member = team.member(member_id)
        if member is None:
            problems.append(f"An address is read for '{member_id}', which is not in the cast.")
        elif member.runs_in is TeamPlace.BROWSER:
            problems.append(f"'{member_id}' runs in the browser: it has no address.")
    if scene.audience.who is Watchers.VISITORS:
        for member in team.agents:
            if member.runs_in is TeamPlace.RUNTIME and member.id not in scene.deployment.addresses:
                problems.append(
                    f"Visitors may watch, and '{member.id}' runs on a runtime with no address: "
                    "deployment.addresses names none for it."
                )
    # The rehearsal.
    names = _names(scene, cast)
    rehearsed = set()
    for rehearsal in scene.rehearsal.beats:
        if rehearsal.beat not in beats:
            problems.append(f"The rehearsal names the beat '{rehearsal.beat}', which is not in the script.")
        if rehearsal.beat in rehearsed:
            problems.append(f"The rehearsal names the beat '{rehearsal.beat}' twice.")
        rehearsed.add(rehearsal.beat)
        for line in rehearsal.parsed():
            for name in (line.who, line.whom):
                if name and name not in names:
                    problems.append(f"The rehearsal of '{rehearsal.beat}' names '{name}', which is not on stage.")
            whom = names.get(line.whom, "")
            if whom in systems and line.detail and names.get(line.who, "") in ids:
                member = team.member(names[line.who])
                why = _tool_problem(member, _persona_name(cast, member.id), whom, line.detail, None)  # type: ignore[arg-type]
                if why:
                    problems.append(f"The rehearsal of '{rehearsal.beat}' expects {why}")
    recording = scene.rehearsal.recording
    if recording is not None and not (Path(__file__).parent / recording.path).is_file():
        problems.append(f"The recording '{recording.path}' is not beside the scenes.")
    return problems


def _persona_name(cast: List[SceneCastMember], member_id: str) -> str:
    for member in cast:
        if member.member == member_id:
            return member.persona.name
    return member_id


def _move_problems(
    beat: SceneBeat,
    move: SceneMove,
    team: TeamSpec,
    setting: SceneSetting,
    links: set,
    cast: List[SceneCastMember],
) -> List[str]:
    """What is wrong with one move of a beat, in sentences."""
    where = f"Beat '{beat.id}':"
    mover = team.member(move.who)
    if mover is None:
        return [f"{where} '{move.who}' moves, and is not in the cast."]
    if mover.is_server:
        return [f"{where} '{move.who}' moves, and a system answers tool by tool: it asks nobody."]
    if not move.asks:
        return []
    asked = team.member(move.asks)
    system = setting.system(move.asks)
    if asked is not None and asked.is_server:
        system = system or SceneSystem(server=asked.server)
    if system is not None:
        if move.over is TeamProtocol.A2A:
            return [f"{where} '{move.who}' asks '{move.asks}' over a2a, a system: a system is asked over mcp."]
        if not _reaches(mover, team, system.id):
            return [f"{where} '{move.who}' asks '{move.asks}' ({system.id}), which it reaches through no connection."]
        if move.tool:
            why = _tool_problem(mover, _persona_name(cast, mover.id), system.id, move.tool, move.does)
            return [f"{where} '{move.who}' asks '{move.asks}' for {why}"] if why else []
        return []
    if move.over is TeamProtocol.MCP:
        return [f"{where} '{move.who}' asks '{move.asks}' over mcp, which is not a system of the scene."]
    if asked is None:
        return [f"{where} '{move.who}' asks '{move.asks}', which is not in the cast."]
    if (move.who, move.asks) not in links:
        return [f"{where} '{move.who}' asks '{move.asks}', which the team does not have it talk to."]
    return []


def scene_setup(scene: SceneSpec) -> List[str]:
    """What a scene names that is not offered today, in sentences: its members' applications' setup."""
    setup: List[str] = []
    for member in scene.team_of().agents:
        app = _app_of(member)
        for sentence in app_setup(app) if app is not None else []:
            if sentence not in setup:
                setup.append(sentence)
    return setup


# --- reading and writing ---------------------------------------------------------------


def parse_scene(data: Mapping[str, Any]) -> SceneSpec:
    """A scene from plain data; what is wrong is said in sentences."""
    try:
        return SceneSpec(**dict(data))
    except ValidationError as error:
        raise SceneError(_sentences(error, str(data.get("id", "the scene")))) from None


def _sentences(error: ValidationError, identity: str) -> str:
    lines = []
    for issue in error.errors():
        where = ".".join(str(part) for part in issue["loc"]).replace("schema_", "schema").replace("shown_as", "as")
        message = issue["msg"].removeprefix("Value error, ")
        if issue["type"] == "extra_forbidden":
            message = "is not a field of the spec"
        elif issue["type"] == "missing":
            message = "is missing"
        lines.append(
            f"{where} {message}"
            if where and issue["type"] in ("extra_forbidden", "missing")
            else f"{where}: {message}"
            if where
            else message
        )
    return f"{identity}: " + "; ".join(lines)


def load_scene(path: Path) -> SceneSpec:
    """A scene from a YAML file."""
    return parse_scene(yaml.safe_load(Path(path).read_text()) or {})


def load_raw_scenes(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every scene YAML of a directory as plain data, by id; the file is named for the id."""
    raw: Dict[str, Dict[str, Any]] = {}
    for path in sorted((directory or Path(__file__).parent).glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("id") != path.stem:
            raise SceneError(f"{path.name}: the file is named for id {path.stem!r}, the spec says {data.get('id')!r}")
        raw[path.stem] = data
    return raw


def load_scenes(directory: Optional[Path] = None) -> Dict[str, SceneSpec]:
    """Every scene of a directory, validated, its references resolved."""
    scenes: Dict[str, SceneSpec] = {}
    for identity, data in load_raw_scenes(directory).items():
        scene = parse_scene(data)
        problems = scene_problems(scene)
        if problems:
            raise SceneError(f"{identity}: " + " ".join(problems))
        scenes[identity] = scene
    return scenes


def dump_scene(scene: SceneSpec) -> Dict[str, Any]:
    """A scene as the plain data its file holds: `schema` first, nothing at its default."""
    data = json.loads(scene.model_dump_json(by_alias=True, exclude_defaults=True))
    return {"schema": scene.schema_, **{key: value for key, value in data.items() if key != "schema"}}


# --- the rehearsal that was played -----------------------------------------------------


def played_path(scene_id: str, directory: Optional[Path] = None) -> Path:
    """Where a scene's last rehearsal is kept: ``<id>/rehearsal.json`` beside the specs."""
    return (directory or Path(__file__).parent) / _id_of(scene_id) / "rehearsal.json"


def scene_played(scene_id: str, directory: Optional[Path] = None) -> Optional[ScenePlayed]:
    """What the last rehearsal of a scene found, or None when none was played.

    A file that is not a rehearsal's result is refused in a sentence
    (`SceneError`), never read as a pass.
    """
    path = played_path(scene_id, directory)
    if not path.is_file():
        return None
    try:
        return ScenePlayed.model_validate(json.loads(path.read_text()))
    except (ValueError, ValidationError) as error:
        raise SceneError(f"{path.name} of '{_id_of(scene_id)}' is not a rehearsal's result: {error}") from None


def write_played(scene_id: str, played: ScenePlayed, directory: Optional[Path] = None) -> Path:
    """Keep what a rehearsal found as the scene's last, and say where."""
    path = played_path(scene_id, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(played.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n")
    return path


def json_schema() -> Dict[str, Any]:
    """The JSON Schema of the scene spec, for editors and for validation outside Python."""
    schema = SceneSpec.model_json_schema(by_alias=True)
    schema["properties"]["schema"] = {
        "description": "The version of the spec itself",
        "title": "Schema",
        **({"const": SCENE_SCHEMA} if len(KNOWN_SCHEMAS) == 1 else {"enum": list(KNOWN_SCHEMAS)}),
        "default": SCENE_SCHEMA,
    }
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"https://agentspecs.datalayer.tech/schemas/{SCENE_SCHEMA}.json"
    schema["title"] = "Scene spec"
    return schema


#: Where the published JSON Schema is kept, beside the specs.
SCHEMA_PATH = Path(__file__).parent / "loop.scene.schema.json"


def schema_text() -> str:
    """The JSON Schema as it is written to :data:`SCHEMA_PATH`."""
    return json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"


#: Every scene of the catalogue, by id.
SCENE_CATALOGUE: Dict[str, SceneSpec] = load_scenes()


def get_scene(scene_id: str) -> Optional[SceneSpec]:
    """A scene, by `id` or `id:version`, or None."""
    return SCENE_CATALOGUE.get(_id_of(scene_id))


def list_scenes(tag: Optional[str] = None) -> List[SceneSpec]:
    """Every scene, or those carrying a tag."""
    return [scene for scene in SCENE_CATALOGUE.values() if tag is None or tag in scene.tags]


def scenes_staging(team_ref: str) -> List[SceneSpec]:
    """Every scene that stages a team, by its id with or without a version."""
    wanted = _id_of(team_ref)
    return [scene for scene in SCENE_CATALOGUE.values() if scene.team and _id_of(scene.team) == wanted]


__all__ = [
    "ADDRESS_VARIABLE",
    "AUDIENCE",
    "AnswerKind",
    "DURATION",
    "Inspector",
    "KNOWN_SCHEMAS",
    "LANGUAGE",
    "Pace",
    "RehearsalBeat",
    "SCENE_CATALOGUE",
    "SCENE_SCHEMA",
    "SCHEMA_PATH",
    "SceneAudience",
    "SceneBeat",
    "SceneBranch",
    "SceneCastMember",
    "SceneCue",
    "SceneDeployment",
    "SceneError",
    "SceneMove",
    "ScenePersona",
    "ScenePlayed",
    "ScenePlayedBeat",
    "SceneRecording",
    "SceneRehearsal",
    "SceneSetting",
    "SceneSpec",
    "SceneStage",
    "SceneSystem",
    "SceneTranscript",
    "StagePosition",
    "TranscriptLine",
    "Watchers",
    "Withheld",
    "dump_scene",
    "get_scene",
    "json_schema",
    "list_scenes",
    "load_raw_scenes",
    "load_scene",
    "load_scenes",
    "parse_line",
    "parse_scene",
    "played_path",
    "scene_played",
    "scene_problems",
    "scene_setup",
    "scenes_staging",
    "schema_text",
    "write_played",
]
