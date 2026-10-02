# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Application specifications: the Appspec.

An *application* is what a person uses and relies on: an agent with an
interface, rules, tests and a place to run. Four kinds — a **chat**, a
**widget** (inputs and outputs, no conversation needed), a **decision**
(alternatives ranked on criteria) and a **worker** (a goal, triggers, an
activity feed) — and one spec for all four.

The spec **stands alone**. It carries its own agent, rules, tests and record
in plain fields, so that somebody who never wrote code could read it aloud. It
is not an Op and does not resolve to one; the Guards, Gates and Tracks of the
catalogue stay available under ``checks`` for a builder who wants their rigour,
and nobody has to name one.

What it says:

- **who does the work** — ``agent`` (an agent or a Cog of the catalogue) or
  ``team``, with the ``instructions`` and ``model`` this application changes;
- **what it works under and knows** — ``context`` (Frames) and ``contents``;
- **who it is** — its ``name``, and its ``emoji``: the face it is known by
  wherever it appears;
- **what it reaches** — ``connections``: an MCP server, how far (``read`` or
  ``write``), and in whose name (the builder's, or each user's); and
  ``permissions``: the Spaces it reads or writes, and what it may do on its
  own computer. An application reaches nothing it does not name here;
- **when it acts alone, and when it asks** — ``rules``, in four behaviours;
- **what the user sees** — ``interface``;
- **how it is verified** — ``tests``;
- **what is kept of what it did** — ``record``;
- **where it goes** — ``deployment``.

A rule is written in a person's words (``action``) and applies to what a tool
does (``applies_to``): a class of action — see :mod:`agentspecs.actions` — or
named tools. The words are read by people; the classes are what is enforced.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ..actions import (
    ActionClass,
    ActionError,
    classes_from,
    classes_of,
    is_pattern,
    matches,
    server_tool_conditions,
    split_ref,
)

_ROOT = Path(__file__).parent.parent

#: The version of the spec itself. A reader refuses one it does not know.
APP_SCHEMA = "loop.app/v1"

#: Every version of the spec this package reads.
KNOWN_SCHEMAS = (APP_SCHEMA,)

#: The share of test conversations that has to pass for an application to be ready.
DEFAULT_READY_AT = 0.8


class AppError(ValueError):
    """An application that cannot be used — named plainly."""


class AppKind(str, Enum):
    """What kind of application it is: what its user meets."""

    CHAT = "chat"
    """A conversation, with starters, settings, and widgets in the answers."""

    WIDGET = "widget"
    """A page of inputs and outputs: fill, run, read."""

    DECISION = "decision"
    """Alternatives, criteria, a ranking the user adjusts, a saved decision."""

    WORKER = "worker"
    """A goal, triggers, an activity feed; it reports back and asks for approval."""


class Behaviour(str, Enum):
    """What an application does when it meets an action: the four a person chooses from."""

    DO_IT = "do_it"
    """It takes the action without asking."""

    IF_ASKED = "if_asked"
    """Only what the person approved in advance: an action, a scope, an end."""

    ASK_FIRST = "ask_first"
    """It waits for an approval."""

    LEAVE_TO_ME = "leave_to_me"
    """It never does it, and hands it over."""


#: From the freest to the most restricted; a tool of several classes takes the last that applies.
_STRICTNESS = (Behaviour.DO_IT, Behaviour.IF_ASKED, Behaviour.ASK_FIRST, Behaviour.LEAVE_TO_ME)


def strictest(behaviours: Sequence[Behaviour]) -> Behaviour:
    """The most restricted of several behaviours."""
    return max(behaviours, key=_STRICTNESS.index)


class Access(str, Enum):
    """How far a connection goes."""

    READ = "read"
    WRITE = "write"


class ActsAs(str, Enum):
    """In whose name a connection acts."""

    OWNER = "owner"
    """The builder's account, for everybody who uses the application."""

    USER = "user"
    """Each user's own account, asked of them when they first need it."""


class Layout(str, Enum):
    """How the application is laid out."""

    CHAT = "chat"
    PAGE = "page"
    SPLIT = "split"


#: The layout a kind starts with.
DEFAULT_LAYOUTS = {
    AppKind.CHAT: Layout.CHAT,
    AppKind.WIDGET: Layout.PAGE,
    AppKind.DECISION: Layout.PAGE,
    AppKind.WORKER: Layout.SPLIT,
}


class Accent(str, Enum):
    """The one colour of an application; everything else is neutral."""

    GREEN = "green"
    ROSE = "rose"
    SKY = "sky"
    LIME = "lime"
    SUN = "sun"
    VIOLET = "violet"


class _Strict(BaseModel):
    """A part of the spec: a key it does not know is a mistake, said as one."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- what it reaches, and its rules ---------------------------------------------------


class AppConnection(_Strict):
    """Something the application reaches."""

    server: str = Field(..., description="An MCP server of the catalogue, `id` or `id:version`")
    access: Access = Field(default=Access.READ, description="How far: `read`, or `write`")
    acts_as: ActsAs = Field(
        default=ActsAs.OWNER,
        alias="as",
        description="In whose name: `owner` (the builder's account) or `user` (each user's own)",
    )
    only: List[str] = Field(
        default_factory=list,
        description=(
            "The tools of the server the application may use, by name or pattern (`*gmail*`: "
            "`*` is any run of characters, `?` any one); all of them when empty. "
            "A tool left out is not reached at all"
        ),
    )

    def reaches(self, tool_name: str) -> bool:
        """Whether the connection lets the application use a tool of its server."""
        return not self.only or any(matches(tool_name, pattern) for pattern in self.only)


class AppRule(_Strict):
    """When the application acts alone, and when it asks."""

    action: str = Field(..., description="The action, in the words a person reads: `Send an email`")
    applies_to: Union[str, List[str]] = Field(
        ...,
        description=(
            "What the rule applies to: a class of action (`read`, `write`, `send`, `buy`, "
            "`delete`, `publish`), or named tools (`server.tool`, or a tool id)"
        ),
    )
    behaviour: Behaviour = Field(..., description="`do_it`, `if_asked`, `ask_first` or `leave_to_me`")

    @field_validator("action")
    @classmethod
    def _says_something(cls, action: str) -> str:
        if not action.strip():
            raise ValueError("a rule names its action in words")
        return action.strip()

    @property
    def targets(self) -> List[str]:
        """What the rule applies to, as a list."""
        return [self.applies_to] if isinstance(self.applies_to, str) else list(self.applies_to)

    @property
    def classes(self) -> Tuple[ActionClass, ...]:
        """The classes of action the rule applies to."""
        return tuple(ActionClass(item) for item in self.targets if item in _CLASS_NAMES)

    @property
    def tools(self) -> List[str]:
        """The tools the rule names."""
        return [item for item in self.targets if item not in _CLASS_NAMES]

    @model_validator(mode="after")
    def _applies_to_something(self) -> "AppRule":
        if not self.targets or any(not str(item).strip() for item in self.targets):
            raise ValueError(f"the rule {self.action!r} applies to a class of action or to named tools")
        if len(set(self.targets)) != len(self.targets):
            raise ValueError(f"the rule {self.action!r} names the same thing twice")
        return self


_CLASS_NAMES = frozenset(item.value for item in ActionClass)


# --- what the user sees ----------------------------------------------------------------


class AppStarter(_Strict):
    """A first message offered to the user."""

    label: str = Field(..., description="What the button says")
    message: str = Field(..., description="What is sent when it is chosen")


class SettingType(str, Enum):
    """What a setting is set with."""

    SELECT = "select"
    TEXT = "text"
    TOGGLE = "toggle"
    SLIDER = "slider"
    NUMBER = "number"


class AppSetting(_Strict):
    """Something the user may set for their session."""

    id: str = Field(..., description="The name the application reads it by")
    type: SettingType = Field(..., description="`select`, `text`, `toggle`, `slider` or `number`")
    label: str = Field(..., description="What the user reads")
    options: List[str] = Field(default_factory=list, description="For a select: its options")
    default: Optional[Union[str, bool, float]] = Field(default=None, description="Its value at the start")
    min: Optional[float] = Field(default=None, description="For a slider or a number: the least")
    max: Optional[float] = Field(default=None, description="For a slider or a number: the most")

    @model_validator(mode="after")
    def _is_settable(self) -> "AppSetting":
        if self.type is SettingType.SELECT and len(self.options) < 2:
            raise ValueError(f"the setting {self.id!r} is a select: give it at least two options")
        if self.type is not SettingType.SELECT and self.options:
            raise ValueError(f"the setting {self.id!r} is not a select: it has no options")
        return self


class AppSurface(_Strict):
    """The component tree the user meets, over the approved catalog (A2UI)."""

    protocol: str = Field(default="a2ui/v0.9", description="The protocol the tree is written in")
    components: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="The components, as the protocol's `updateComponents` carries them",
    )
    composed_by: str = Field(default="", description="Who composed it: a model's id, `developer`, `template`")
    composed_at: str = Field(default="", description="When, as an ISO date")

    @field_validator("components")
    @classmethod
    def _is_a_tree(cls, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        identities = []
        for component in components:
            if not component.get("id") or not component.get("component"):
                raise ValueError("every component of a surface has an `id` and a `component`")
            identities.append(component["id"])
        if len(set(identities)) != len(identities):
            raise ValueError("two components of the surface have the same id")
        if components and "root" not in identities:
            raise ValueError("a surface starts from the component whose id is `root`")
        return components


class AppInterface(_Strict):
    """What the user sees."""

    layout: Optional[Layout] = Field(default=None, description="`chat`, `page` or `split`; the kind's own when unsaid")
    accent: Accent = Field(default=Accent.GREEN, description="The application's one colour")
    welcome: str = Field(default="", description="What the application says first")
    starters: List[AppStarter] = Field(default_factory=list, description="First messages offered to the user")
    settings: List[AppSetting] = Field(default_factory=list, description="What the user may set")
    components: List[str] = Field(
        default_factory=list,
        description="The components of the catalog the surface may use; the kind's own when empty",
    )
    surface: Optional[AppSurface] = Field(default=None, description="The component tree, when there is one")

    @model_validator(mode="after")
    def _names_are_distinct(self) -> "AppInterface":
        identities = [setting.id for setting in self.settings]
        if len(set(identities)) != len(identities):
            raise ValueError("two settings have the same id")
        return self


# --- how it is verified, and what is kept -------------------------------------------


class AppTestCase(_Strict):
    """An example of what the application should do, in plain words."""

    ask: str = Field(..., description="What it is asked")
    expect: str = Field(..., description="What it should do")


class AppTests(_Strict):
    """How the application is verified."""

    ready_at: float = Field(
        default=DEFAULT_READY_AT,
        ge=0,
        le=1,
        description="The share of tests that has to pass for the application to be ready",
    )
    evalset: str = Field(default="", description="An evalset its runs validate against, when one is chosen")
    cases: List[AppTestCase] = Field(default_factory=list, description="Its test conversations")


class RecordItem(str, Enum):
    """What an application may keep of what it did."""

    CONVERSATIONS = "conversations"
    ACTIONS = "actions"
    DECISIONS = "decisions"
    APPROVALS = "approvals"
    CHECKS = "checks"
    SOURCES = "sources"
    OUTPUTS = "outputs"
    FEEDBACK = "feedback"


_RETENTION = re.compile(r"^(?P<count>[1-9]\d*)_(?P<unit>day|days|month|months|year|years)$")
_DAYS = {"day": 1, "month": 30, "year": 365}


def retention_days(keep_for: str) -> int:
    """A retention as days: `90_days`, `18_months`, `1_years`."""
    matched = _RETENTION.match(keep_for.strip())
    if matched is None:
        raise AppError(f"cannot read the retention {keep_for!r}: write `90_days`, `18_months` or `1_years`")
    return int(matched.group("count")) * _DAYS[matched.group("unit").rstrip("s")]


class AppRecord(_Strict):
    """What is kept of what the application did, and for how long."""

    keep_for: str = Field(default="1_years", description="How long: `90_days`, `18_months`, `1_years`")
    include: List[RecordItem] = Field(
        default_factory=lambda: [RecordItem.CONVERSATIONS, RecordItem.ACTIONS, RecordItem.APPROVALS],
        description="What is kept",
    )

    @field_validator("keep_for")
    @classmethod
    def _is_a_retention(cls, keep_for: str) -> str:
        retention_days(keep_for)
        return keep_for.strip()

    @property
    def retention_days(self) -> int:
        """The retention, as days."""
        return retention_days(self.keep_for)


class AppChecks(_Strict):
    """Optional: checks from the catalogue, for a builder who wants them."""

    guards: List[str] = Field(default_factory=list, description="Guards, `id` or `id:version`")
    gates: List[str] = Field(default_factory=list, description="Gates, `id` or `id:version`")
    track: str = Field(default="", description="A Track, `id` or `id:version`")


# --- what else it may reach -------------------------------------------------------------


class AppSpaceGrant(_Strict):
    """A Space the application may reach."""

    space: str = Field(..., description="The Space, by its handle or its id")
    access: Access = Field(default=Access.READ, description="`read`, or `write`")


class AppComputer(_Strict):
    """What the application may do on its own computer. Each is off until it is turned on."""

    browse: bool = Field(default=False, description="Open pages in a browser")
    files: bool = Field(default=False, description="Read and write files")
    shell: bool = Field(default=False, description="Run commands")


class AppPermissions(_Strict):
    """What the application may reach beside its connections. Nothing, unless said."""

    spaces: List[AppSpaceGrant] = Field(default_factory=list, description="The Spaces it reads or writes")
    computer: AppComputer = Field(default_factory=AppComputer, description="Its computer: browse, files, shell")

    @model_validator(mode="after")
    def _grants_a_space_once(self) -> "AppPermissions":
        spaces = [grant.space for grant in self.spaces]
        if len(set(spaces)) != len(spaces):
            raise ValueError("the application is granted the same Space twice")
        return self


# --- where it goes ----------------------------------------------------------------------


class Visibility(str, Enum):
    """Who can open a hosted application."""

    PRIVATE = "private"
    INVITED = "invited"
    ORGANIZATION = "organization"
    LINK = "link"
    PUBLIC = "public"


class EmbedMode(str, Enum):
    """How an application sits in another product's page."""

    INLINE = "inline"
    BUBBLE = "bubble"
    PANEL = "panel"


class HostedDeployment(_Strict):
    """The application at an address of its own."""

    visibility: Visibility = Field(default=Visibility.PRIVATE, description="Who can open it")
    slug: str = Field(default="", description="The readable part of its address")

    @field_validator("slug")
    @classmethod
    def _is_a_slug(cls, slug: str) -> str:
        if slug and not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", slug):
            raise ValueError(f"cannot use {slug!r} in an address: lower-case letters, digits and hyphens")
        return slug


_ORIGIN = re.compile(r"^https://[A-Za-z0-9.-]+(?::\d+)?$|^http://(?:localhost|127\.0\.0\.1)(?::\d+)?$")


class EmbeddedDeployment(_Strict):
    """The application inside another product's page."""

    mode: EmbedMode = Field(default=EmbedMode.INLINE, description="`inline`, `bubble` or `panel`")
    origins: List[str] = Field(default_factory=list, description="The origins allowed to embed it")

    @field_validator("origins")
    @classmethod
    def _are_origins(cls, origins: List[str]) -> List[str]:
        for origin in origins:
            if not _ORIGIN.match(origin):
                raise ValueError(
                    f"{origin!r} is not an origin: write `https://example.com`, without a path"
                )
        return origins


class AppDeployment(_Strict):
    """Where the application goes."""

    hosted: Optional[HostedDeployment] = Field(default=None, description="At an address of its own")
    embedded: Optional[EmbeddedDeployment] = Field(default=None, description="Inside another product")


# --- a worker's own ---------------------------------------------------------------------


class TriggerType(str, Enum):
    """What starts a worker: the trigger kinds of the catalogue."""

    SCHEDULE = "schedule"
    EVENT = "event"
    ONCE = "once"


class AppTrigger(_Strict):
    """What starts a worker's work."""

    type: TriggerType = Field(..., description="`schedule`, `event` or `once`")
    cron: str = Field(default="", description="For a schedule: a cron expression, `0 8 * * *`")
    event: str = Field(default="", description="For an event: its name, `email_received`")
    at: str = Field(default="", description="For once: when, as an ISO date")
    description: str = Field(default="", description="What it is, in words: `Every morning at 8`")
    prompt: str = Field(default="", description="What the worker is told when it fires")

    @model_validator(mode="after")
    def _says_when(self) -> "AppTrigger":
        needs = {TriggerType.SCHEDULE: "cron", TriggerType.EVENT: "event", TriggerType.ONCE: "at"}[self.type]
        if not getattr(self, needs).strip():
            raise ValueError(f"a {self.type.value} trigger says its `{needs}`")
        if self.type is TriggerType.SCHEDULE and len(self.cron.split()) != 5:
            raise ValueError(f"cannot read the schedule {self.cron!r}: five fields, `0 8 * * *`")
        return self


# --- a decision's own -------------------------------------------------------------------


class CriterionKind(str, Enum):
    """How a criterion is assessed."""

    METRIC = "metric"
    NOUL = "noul"
    CHOICE = "choice"
    SCORE = "score"


class AppCriterion(_Strict):
    """What an alternative is judged on."""

    name: str = Field(..., description="Its name")
    kind: CriterionKind = Field(default=CriterionKind.METRIC, description="`metric`, `noul`, `choice`, `score`")
    weight: float = Field(default=1, ge=0, description="How much it counts")
    instructions: str = Field(default="", description="What a judgment model is asked, or how a metric is computed")
    options: List[str] = Field(default_factory=list, description="For a choice or a score: from the worst to the best")
    direction: str = Field(default="higher", pattern="^(higher|lower)$", description="Whether more counts for, or against")
    measure: str = Field(
        default="",
        pattern="^(|pass_rate|cost_per_task|seconds_per_task)$",
        description="For a metric: what a benchmark run fills it from",
    )

    @model_validator(mode="after")
    def _can_be_answered(self) -> "AppCriterion":
        if self.kind in (CriterionKind.CHOICE, CriterionKind.SCORE) and len(self.options) < 2:
            raise ValueError(f"give {self.name!r} at least two options, from the worst to the best")
        if self.kind is not CriterionKind.METRIC and not self.instructions.strip():
            raise ValueError(f"say what is judged for {self.name!r}")
        return self


class AppScenario(_Strict):
    """A named set of weights: one way of looking at the same findings."""

    name: str = Field(..., description="Its name")
    weights: Dict[str, float] = Field(default_factory=dict, description="By criterion name")


class AppDecision(_Strict):
    """What a decision application decides."""

    question: str = Field(..., description="The question it answers")
    alternatives: List[str] = Field(default_factory=list, description="What is chosen between")
    criteria: List[AppCriterion] = Field(default_factory=list, description="What each is judged on")
    min_confidence: float = Field(
        default=0,
        ge=0,
        le=1,
        description="A judgment less confident than this is put to the reader",
    )
    scenarios: List[AppScenario] = Field(default_factory=list, description="Named sets of weights")
    judgment_model: str = Field(default="", description="The model that answers the judgments")

    @model_validator(mode="after")
    def _can_rank(self) -> "AppDecision":
        if not self.question.strip():
            raise ValueError("say the question the application answers")
        names = [criterion.name.strip().lower() for criterion in self.criteria]
        if any(not name for name in names):
            raise ValueError("every criterion needs a name")
        if len(set(names)) != len(names):
            raise ValueError("two criteria have the same name")
        if self.criteria and all(criterion.weight == 0 for criterion in self.criteria):
            raise ValueError("at least one criterion needs a weight above zero")
        named = [name.strip().lower() for name in self.alternatives if name.strip()]
        if len(set(named)) != len(named):
            raise ValueError("two alternatives have the same name")
        return self


# --- the application ------------------------------------------------------------------


class AppSpec(_Strict):
    """Specification for an application."""

    schema_: str = Field(default=APP_SCHEMA, alias="schema", description="The version of the spec itself")
    id: str = Field(..., description="Unique application identifier")
    version: str = Field(default="0.0.1", description="Application version")
    name: str = Field(..., description="Display name")
    kind: AppKind = Field(..., description="`chat`, `widget`, `decision` or `worker`")
    description: str = Field(default="", description="What it does, in a sentence")
    owner: str = Field(default="", description="Who answers for it")

    agent: str = Field(default="", description="The agent or the Cog that does the work, `id` or `id:version`")
    team: str = Field(default="", description="Or a team of them, `id` or `id:version`")
    instructions: str = Field(default="", description="What this application tells its agent, on top of its own")
    model: str = Field(default="", description="The model, when it is not the organization's default")
    skills: List[str] = Field(default_factory=list, description="Skills it adds to its agent's")
    tools: List[str] = Field(default_factory=list, description="Tools of the catalogue it adds to its agent's")

    context: List[str] = Field(default_factory=list, description="The Frames it works under")
    contents: List[str] = Field(default_factory=list, description="The documents and datasets it answers from")
    connections: List[AppConnection] = Field(default_factory=list, description="What it reaches")
    rules: List[AppRule] = Field(default_factory=list, description="When it acts alone, and when it asks")
    permissions: AppPermissions = Field(
        default_factory=AppPermissions,
        description="What else it may reach: Spaces, its computer. Nothing, unless said",
    )

    interface: AppInterface = Field(default_factory=AppInterface, description="What the user sees")
    tests: AppTests = Field(default_factory=AppTests, description="How it is verified")
    record: AppRecord = Field(default_factory=AppRecord, description="What is kept of what it did")
    checks: AppChecks = Field(default_factory=AppChecks, description="Optional checks from the catalogue")
    deployment: AppDeployment = Field(default_factory=AppDeployment, description="Where it goes")

    goal: str = Field(default="", description="For a worker: what it works toward")
    triggers: List[AppTrigger] = Field(default_factory=list, description="For a worker: what starts its work")
    memory: str = Field(default="", description="A memory of the catalogue, when it remembers")
    notifications: List[str] = Field(default_factory=list, description="Where an approval reaches a person")

    decision: Optional[AppDecision] = Field(default=None, description="For a decision: what it decides")

    enabled: bool = Field(default=True, description="Whether it is offered today")
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="apps", description="Icon identifier")
    emoji: str = Field(
        default="\U0001f440",
        description="Its face: one emoji, shown wherever the application appears",
    )

    @field_validator("emoji")
    @classmethod
    def _is_a_face(cls, emoji: str) -> str:
        face = emoji.strip()
        if not face or len(face) > 16 or any(character.isalnum() or character.isspace() for character in face):
            raise ValueError("an application's `emoji` is one emoji, its face")
        return face

    @field_validator("schema_")
    @classmethod
    def _is_a_known_schema(cls, schema: str) -> str:
        if schema not in KNOWN_SCHEMAS:
            raise ValueError(
                f"this reads {', '.join(KNOWN_SCHEMAS)}; the application is written in {schema!r}"
            )
        return schema

    @field_validator("id")
    @classmethod
    def _is_an_id(cls, identity: str) -> str:
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", identity):
            raise ValueError(f"cannot use {identity!r} as an id: lower-case letters, digits and hyphens")
        return identity

    @model_validator(mode="after")
    def _holds_together(self) -> "AppSpec":
        if bool(self.agent) == bool(self.team):
            raise ValueError("an application names who does the work: an `agent`, or a `team`, and not both")
        if self.kind is AppKind.DECISION and self.decision is None:
            raise ValueError("a decision application says what it decides, under `decision`")
        if self.kind is not AppKind.DECISION and self.decision is not None:
            raise ValueError(f"a {self.kind.value} application decides nothing: remove `decision`, or make it a decision")
        if self.kind is AppKind.WORKER:
            if not self.goal.strip():
                raise ValueError("a worker says its `goal`")
            if not self.triggers:
                raise ValueError("a worker says what starts its work, under `triggers`")
        elif self.triggers:
            raise ValueError(f"a {self.kind.value} application starts when somebody opens it: `triggers` are a worker's")
        servers = [_id_of(connection.server) for connection in self.connections]
        if len(set(servers)) != len(servers):
            raise ValueError("the application connects to the same server twice")
        actions = [rule.action.lower() for rule in self.rules]
        if len(set(actions)) != len(actions):
            raise ValueError("two rules have the same action")
        seen: Dict[str, str] = {}
        for rule in self.rules:
            for target in (_normal(item) for item in rule.targets):
                if target in seen:
                    raise ValueError(
                        f"the rules {seen[target]!r} and {rule.action!r} both apply to {target!r}: keep one"
                    )
                seen[target] = rule.action
        return self

    @property
    def layout(self) -> Layout:
        """How it is laid out: what it says, or its kind's own."""
        return self.interface.layout or DEFAULT_LAYOUTS[self.kind]

    def connection(self, server: str) -> Optional[AppConnection]:
        """Its connection to a server, or None."""
        wanted = _id_of(server)
        for connection in self.connections:
            if _id_of(connection.server) == wanted:
                return connection
        return None


def _id_of(ref: str) -> str:
    """The id of a reference, `id` or `id:version`."""
    base, _, version = str(ref).rpartition(":")
    return base if base and "." in version else str(ref)


# --- what a rule decides ----------------------------------------------------------------

#: What an application does about a class of action no rule of its own covers.
#: Reading needs no rule. Anything that acts waits for a person: never `do_it`.
DEFAULT_BEHAVIOURS = {
    ActionClass.READ: Behaviour.DO_IT,
    ActionClass.WRITE: Behaviour.ASK_FIRST,
    ActionClass.SEND: Behaviour.ASK_FIRST,
    ActionClass.BUY: Behaviour.ASK_FIRST,
    ActionClass.DELETE: Behaviour.ASK_FIRST,
    ActionClass.PUBLISH: Behaviour.ASK_FIRST,
}


def _normal(target: str) -> str:
    """What a rule applies to, versions aside: `send`, `server.tool`, or a tool id."""
    if target in _CLASS_NAMES:
        return target
    server, name = split_ref(target)
    return f"{_id_of(server)}.{name}" if server is not None else name


def behaviour_for(
    app: AppSpec,
    tool: str,
    *,
    arguments: Optional[Mapping[str, Any]] = None,
    classes: Optional[Sequence[ActionClass]] = None,
) -> Behaviour:
    """What an application does when its agent calls a tool.

    ``tool`` is ``server.tool`` for a tool of an MCP server, or the id of a
    tool of the catalogue. Its classes are the catalogue's, unless given.
    What a tool does can depend on what it is asked: with the ``arguments``
    of the call, the decision is for that call; without them, for the worst
    the tool can do.

    In order:

    1. a tool of a server the application is not connected to, or that its
       connection leaves out (``only``), is left to the person: an
       application reaches nothing it does not name;
    2. a tool that can act, on a connection that only reads, is left to the person;
    3. a rule that names the tool decides what the tool does of its own — and
       what the arguments make it do *besides* is still decided by its class:
       *label a message: do it* does not become *trash it: do it*;
    4. a tool nobody classed is left to the person: unknown is the most restricted;
    5. otherwise each of its classes is decided by the rule on that class, or
       by :data:`DEFAULT_BEHAVIOURS`, and the most restricted wins.
    """
    server, name = split_ref(tool)
    if classes is not None:
        own, besides, possible = tuple(classes), (), tuple(classes)
    else:
        possible = classes_of(tool)
        own = classes_of(tool, {})
        now = possible if arguments is None else classes_of(tool, arguments)
        besides = tuple(item for item in now if item not in own)
    if server is not None:
        connection = app.connection(server)
        if connection is None or not connection.reaches(name):
            return Behaviour.LEAVE_TO_ME
        if connection.access is Access.READ and any(item is not ActionClass.READ for item in possible):
            return Behaviour.LEAVE_TO_ME
    by_class = {item: rule.behaviour for rule in app.rules for item in rule.classes}

    def decided(items: Sequence[ActionClass]) -> List[Behaviour]:
        return [by_class.get(item, DEFAULT_BEHAVIOURS[item]) for item in items]

    wanted = f"{_id_of(server)}.{name}" if server is not None else name
    for rule in app.rules:
        if any(_normal(named) == wanted for named in rule.tools):
            return strictest([rule.behaviour, *decided(besides)])
    if not own and not besides:
        return Behaviour.LEAVE_TO_ME
    return strictest(decided((*own, *besides)))


# --- the catalogues it draws from ---------------------------------------------------

_CATALOGUES: Dict[str, Dict[str, Dict[str, Any]]] = {}


def _catalogue(name: str) -> Dict[str, Dict[str, Any]]:
    """One of this package's catalogues, as plain data by id, read once."""
    if name not in _CATALOGUES:
        specs: Dict[str, Dict[str, Any]] = {}
        folder = _ROOT / name
        if folder.is_dir():
            for path in sorted(folder.rglob("*.yaml")):
                data = yaml.safe_load(path.read_text()) or {}
                if data.get("id"):
                    specs[str(data["id"])] = data
        _CATALOGUES[name] = specs
    return _CATALOGUES[name]


def _is_off(spec: Mapping[str, Any]) -> bool:
    """Whether a spec of the catalogue says it is not offered today."""
    return spec.get("enabled") is False or spec.get("available") is False


def _refs(app: AppSpec) -> List[Tuple[str, str, str]]:
    """Every reference an application makes: (what it is, the catalogue, the reference)."""
    refs: List[Tuple[str, str, str]] = []
    if app.team:
        refs.append(("team", "teams", app.team))
    refs += [("Frame", "frames", ref) for ref in app.context]
    refs += [("MCP server", "mcp-servers", connection.server) for connection in app.connections]
    refs += [("skill", "skills", ref) for ref in app.skills]
    refs += [("tool", "tools", ref) for ref in app.tools]
    refs += [("Guard", "guards", ref) for ref in app.checks.guards]
    refs += [("Gate", "gates", ref) for ref in app.checks.gates]
    if app.checks.track:
        refs.append(("Track", "tracks", app.checks.track))
    if app.memory:
        refs.append(("memory", "memory", app.memory))
    refs += [("notification", "notifications", ref) for ref in app.notifications]
    return refs


def _agent_of(app: AppSpec) -> Optional[Dict[str, Any]]:
    """The agent or the Cog an application names, as plain data, or None."""
    identity = _id_of(app.agent)
    return _catalogue("cogs").get(identity) or _catalogue("agents").get(identity)


def app_problems(app: AppSpec) -> List[str]:
    """What stops an application from being used, in sentences; empty when nothing does.

    Every reference resolves, every rule applies to something the application
    can reach, and what it asks of the catalogue's Gates is run by its Guards.
    """
    problems: List[str] = []
    if app.agent and _agent_of(app) is None:
        problems.append(f"There is no agent or Cog named {app.agent!r}.")
    for what, catalogue, ref in _refs(app):
        if _id_of(ref) not in _catalogue(catalogue):
            problems.append(f"There is no {what} named {ref!r}.")
    from ..models import get_model

    if app.model and get_model(app.model) is None:
        problems.append(f"There is no model named {app.model!r}.")
    if app.decision is not None and app.decision.judgment_model:
        judge = get_model(app.decision.judgment_model)
        if judge is None:
            problems.append(f"There is no model named {app.decision.judgment_model!r} to judge with.")
        elif "judgments" not in judge.capabilities:
            problems.append(f"The model {app.decision.judgment_model!r} does not answer typed judgments.")
    run = {_id_of(guard) for guard in app.checks.guards}
    for ref in app.checks.gates:
        gate = _catalogue("gates").get(_id_of(ref))
        for guard in (gate or {}).get("guards") or []:
            if _id_of(guard) not in run:
                problems.append(
                    f"The Gate {ref!r} reads the Guard {guard!r}, which the application does not run: "
                    "add it under `checks.guards`."
                )
    for rule in app.rules:
        for tool in rule.tools:
            server, name = split_ref(tool)
            if server is None:
                if _id_of(name) not in _catalogue("tools"):
                    problems.append(f"The rule {rule.action!r} names the tool {tool!r}, which the catalogue does not have.")
            elif app.connection(server) is None:
                problems.append(
                    f"The rule {rule.action!r} names {tool!r}, and the application is not connected to {server!r}."
                )
            elif not app.connection(server).reaches(name):  # type: ignore[union-attr]
                problems.append(
                    f"The rule {rule.action!r} names {tool!r}, which the connection to {server!r} leaves out (`only`)."
                )
    for connection in app.connections:
        if connection.access is Access.READ:
            continue
        spec = _catalogue("mcp-servers").get(_id_of(connection.server))
        if spec is not None and not (spec.get("actions") or {}).get("tools"):
            problems.append(
                f"The application may write through {connection.server!r}, whose tools nobody has classed: "
                "every one of them is left to the person until they are."
            )
    return problems


def app_setup(app: AppSpec) -> List[str]:
    """What an application names that is not offered today, in sentences.

    Not a mistake in the spec: something to set up before it runs — an agent
    or a server that is disabled, a notification that is not available.
    """
    setup: List[str] = []
    agent = _agent_of(app) if app.agent else None
    if agent is not None and _is_off(agent):
        setup.append(f"The agent {app.agent!r} is not enabled.")
    for what, catalogue, ref in _refs(app):
        spec = _catalogue(catalogue).get(_id_of(ref))
        if spec is not None and _is_off(spec):
            setup.append(f"The {what} {ref!r} is not enabled.")
    return setup


def tool_behaviours(app: AppSpec) -> Dict[str, Behaviour]:
    """What the application does about every classed tool of the servers it connects to.

    For each tool in its plain use — no argument that makes it do more; see
    :func:`tool_escalations` for those. A server that classes its tools by a
    pattern (``generate_*``) is reported by that pattern: the names it stands
    for are only known at run time, and each is decided then.
    """
    behaviours: Dict[str, Behaviour] = {}
    for connection in app.connections:
        identity = _id_of(connection.server)
        spec = _catalogue("mcp-servers").get(identity) or {}
        for name, value in ((spec.get("actions") or {}).get("tools") or {}).items():
            ref = f"{identity}.{name}"
            if is_pattern(name):
                found = classes_from(value.get("class") if isinstance(value, dict) else value)
                behaviours[ref] = (
                    Behaviour.LEAVE_TO_ME
                    if connection.access is Access.READ and any(item is not ActionClass.READ for item in found)
                    else _by_classes(app, found)
                )
            else:
                behaviours[ref] = behaviour_for(app, ref, arguments={})
    return behaviours


def _by_classes(app: AppSpec, found: Sequence[ActionClass]) -> Behaviour:
    """What the rules on classes decide for a tool of these classes."""
    if not found:
        return Behaviour.LEAVE_TO_ME
    by_class = {item: rule.behaviour for rule in app.rules for item in rule.classes}
    return strictest([by_class.get(item, DEFAULT_BEHAVIOURS[item]) for item in found])


def tool_escalations(app: AppSpec) -> Dict[str, List[Dict[str, Any]]]:
    """Where what a tool is asked changes what the application does about it.

    By tool: each condition that makes it do more than its plain use, and
    what the application does then — *labels a message: do it; when the label
    is TRASH: left to the person*. Only the conditions that change the
    decision are listed.
    """
    escalations: Dict[str, List[Dict[str, Any]]] = {}
    for connection in app.connections:
        identity = _id_of(connection.server)
        spec = _catalogue("mcp-servers").get(identity) or {}
        for name in (spec.get("actions") or {}).get("tools") or {}:
            if is_pattern(name):
                continue
            ref = f"{identity}.{name}"
            plain = behaviour_for(app, ref, arguments={})
            for condition in server_tool_conditions(spec, name):
                values = condition.includes or condition.equals
                arguments = {condition.argument: [values[0]] if condition.includes else values[0]}
                then = behaviour_for(app, ref, arguments=arguments)
                if then is not plain:
                    escalations.setdefault(ref, []).append({**condition.as_data(), "behaviour": then.value})
    return escalations


# --- reading, and the schema ------------------------------------------------------------


def parse_app(data: Mapping[str, Any]) -> AppSpec:
    """An application from plain data; what is wrong is said in sentences."""
    try:
        return AppSpec(**dict(data))
    except ValidationError as error:
        raise AppError(_sentences(error, str(data.get("id", "the application")))) from None
    except ActionError as error:
        raise AppError(str(error)) from None


def _sentences(error: ValidationError, identity: str) -> str:
    """A validation error as sentences a person can act on."""
    lines = []
    for issue in error.errors():
        where = ".".join(str(part) for part in issue["loc"]).replace("schema_", "schema").replace("acts_as", "as")
        message = issue["msg"].removeprefix("Value error, ")
        if issue["type"] == "extra_forbidden":
            message = "is not a field of the spec"
        elif issue["type"] == "missing":
            message = "is missing"
        lines.append(f"{where} {message}" if where and issue["type"] in ("extra_forbidden", "missing") else f"{where}: {message}" if where else message)
    return f"{identity}: " + "; ".join(lines)


def load_app(path: Path) -> AppSpec:
    """An application from a YAML file."""
    return parse_app(yaml.safe_load(Path(path).read_text()) or {})


def load_raw_apps(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every application YAML of a directory as plain data, by id; the file is named for the id."""
    raw: Dict[str, Dict[str, Any]] = {}
    for path in sorted((directory or Path(__file__).parent).glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("id") != path.stem:
            raise AppError(f"{path.name}: the file is named for id {path.stem!r}, the spec says {data.get('id')!r}")
        raw[path.stem] = data
    return raw


def load_apps(directory: Optional[Path] = None) -> Dict[str, AppSpec]:
    """Every application of a directory, validated, its references resolved."""
    apps: Dict[str, AppSpec] = {}
    for identity, data in load_raw_apps(directory).items():
        app = parse_app(data)
        problems = app_problems(app)
        if problems:
            raise AppError(f"{identity}: " + " ".join(problems))
        apps[identity] = app
    return apps


def dump_app(app: AppSpec) -> Dict[str, Any]:
    """An application as the plain data its file holds.

    The spec's own keys, in the order the spec declares them, `schema`
    first; nothing written that is at its default — the layout of its kind
    included, since it says nothing its kind does not. The same application
    always writes the same document.
    """
    data = json.loads(app.model_dump_json(by_alias=True, exclude_defaults=True))
    interface = data.get("interface") or {}
    if interface.get("layout") == DEFAULT_LAYOUTS[app.kind].value:
        del interface["layout"]
        if not interface:
            del data["interface"]
    return {"schema": app.schema_, **{key: value for key, value in data.items() if key != "schema"}}


def json_schema() -> Dict[str, Any]:
    """The JSON Schema of the Appspec, for editors and for validation outside Python."""
    schema = AppSpec.model_json_schema(by_alias=True)
    # A validator outside Python refuses another version, as `parse_app` does.
    schema["properties"]["schema"] = {
        "description": "The version of the spec itself",
        "title": "Schema",
        **({"const": APP_SCHEMA} if len(KNOWN_SCHEMAS) == 1 else {"enum": list(KNOWN_SCHEMAS)}),
        "default": APP_SCHEMA,
    }
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = f"https://agentspecs.datalayer.tech/schemas/{APP_SCHEMA}.json"
    schema["title"] = "Appspec"
    return schema


#: Where the published JSON Schema is kept, beside the specs.
SCHEMA_PATH = Path(__file__).parent / "appspec.schema.json"


def schema_text() -> str:
    """The JSON Schema as it is written to :data:`SCHEMA_PATH`."""
    return json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"


#: Every application of the catalogue, by id.
APP_CATALOGUE: Dict[str, AppSpec] = load_apps()


def get_app(app_id: str) -> Optional[AppSpec]:
    """An application, by `id` or `id:version`, or None."""
    return APP_CATALOGUE.get(_id_of(app_id))


def list_apps(kind: Optional[AppKind] = None) -> List[AppSpec]:
    """Every application, or those of a kind."""
    return [app for app in APP_CATALOGUE.values() if kind is None or app.kind is kind]


__all__ = [
    "APP_CATALOGUE",
    "APP_SCHEMA",
    "DEFAULT_BEHAVIOURS",
    "DEFAULT_LAYOUTS",
    "DEFAULT_READY_AT",
    "KNOWN_SCHEMAS",
    "SCHEMA_PATH",
    "Accent",
    "Access",
    "ActsAs",
    "AppChecks",
    "AppComputer",
    "AppConnection",
    "AppCriterion",
    "AppDecision",
    "AppDeployment",
    "AppError",
    "AppInterface",
    "AppKind",
    "AppPermissions",
    "AppRecord",
    "AppRule",
    "AppScenario",
    "AppSetting",
    "AppSpaceGrant",
    "AppSpec",
    "AppStarter",
    "AppSurface",
    "AppTestCase",
    "AppTests",
    "AppTrigger",
    "Behaviour",
    "CriterionKind",
    "EmbedMode",
    "EmbeddedDeployment",
    "HostedDeployment",
    "Layout",
    "RecordItem",
    "SettingType",
    "TriggerType",
    "Visibility",
    "app_problems",
    "app_setup",
    "behaviour_for",
    "dump_app",
    "get_app",
    "json_schema",
    "list_apps",
    "load_app",
    "load_apps",
    "load_raw_apps",
    "parse_app",
    "retention_days",
    "schema_text",
    "strictest",
    "tool_behaviours",
    "tool_escalations",
]
