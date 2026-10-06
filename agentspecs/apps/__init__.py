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
  wherever it appears; optionally an ``avatar`` and a ``banner``, drawings
  chosen by name as a person chooses theirs on their profile;
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

#: How an avatar or a banner is named: as its drawing is, ``AstronautIcon``.
DRAWING_NAME = r"[A-Z][A-Za-z0-9]{0,63}"

#: What a validator outside Python checks an avatar or a banner against:
#: nothing, or a drawing's name, around the spaces Python lets go.
_DRAWING_SCHEMA = {"pattern": rf"^\s*({DRAWING_NAME})?\s*$"}

#: How the character of a floating assistant is named (LOOP T-24): by the id
#: a UI plugin contributes it under, ``paperclip`` or ``acme-owl``. Which ids
#: exist is known only where the plugins are, the runtime and the page.
ASSISTANT_CHARACTER_ID = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"

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
    category: str = Field(
        default="",
        description=(
            "The heading it is offered under: the starters of one category are shown together, "
            "those without one first (LOOP P-20)"
        ),
    )


#: What follows the slash: lower-case letters, digits and hyphens, a letter first.
COMMAND_NAME = r"[a-z](?:[a-z0-9-]{0,30}[a-z0-9])?"

#: Where a command's prompt takes the words typed after it.
COMMAND_INPUT = "{input}"

#: The id of a mode or of one of its options.
MODE_ID = r"[a-z][a-z0-9_-]{0,39}"


class AppCommand(_Strict):
    """A slash command the user picks in the composer (LOOP P-19).

    Typing `/` lists the application's commands; picking one sends its
    `prompt`, `{input}` replaced by the words typed after the command.
    """

    name: str = Field(
        ...,
        pattern=rf"^{COMMAND_NAME}$",
        description="What follows the slash: lower-case letters, digits and hyphens, a letter first (`summarise`)",
    )
    description: str = Field(..., min_length=1, description="What the composer's menu says it does")
    prompt: str = Field(
        ...,
        min_length=1,
        description=(
            "What is sent when it is picked: `{input}` stands for the words typed after it; "
            "without `{input}`, those words follow the prompt. An application's code answers "
            "`/<name> {input}` itself (`@app.command`)"
        ),
    )

    @field_validator("prompt")
    @classmethod
    def _takes_input_only(cls, prompt: str) -> str:
        for placeholder in re.findall(r"\{[^{}]*\}", prompt):
            if placeholder != COMMAND_INPUT:
                raise ValueError(
                    f"a command's prompt takes the words typed after it as `{COMMAND_INPUT}`, not {placeholder}"
                )
        return prompt


def command_prompt(command: AppCommand, words: str = "") -> str:
    """What a command sends: its prompt, the words typed after it in place of `{input}`."""
    words = words.strip()
    if COMMAND_INPUT in command.prompt:
        return command.prompt.replace(COMMAND_INPUT, words).strip()
    return f"{command.prompt}\n\n{words}" if words else command.prompt


class AppModeOption(_Strict):
    """One position of a mode switch (LOOP P-19): what the agent is told, the model it runs on."""

    id: str = Field(..., pattern=rf"^{MODE_ID}$", description="Its id, what a run says it is in")
    label: str = Field(..., min_length=1, description="What the switch says")
    description: str = Field(default="", description="What it changes, in a sentence")
    instructions: str = Field(
        default="", description="What the agent is told besides its instructions, in every run in this mode"
    )
    model: Optional[str] = Field(
        default=None, description="The model a run in this mode runs on, in place of the application's"
    )


class AppMode(_Strict):
    """A mode switch in the composer (LOOP P-19): the person picks one of its options."""

    id: str = Field(..., pattern=rf"^{MODE_ID}$", description="Its id, the key a run says its option under")
    label: str = Field(..., min_length=1, description="What the switch is called")
    options: List[AppModeOption] = Field(..., min_length=2, description="Its positions, two at least")
    default: Optional[str] = Field(default=None, description="The option it starts on; the first when unsaid")

    @model_validator(mode="after")
    def _options_are_distinct(self) -> "AppMode":
        ids = [option.id for option in self.options]
        if len(set(ids)) != len(ids):
            raise ValueError(f"two options of the mode {self.id!r} have the same id")
        if self.default is not None and self.default not in ids:
            raise ValueError(f"the mode {self.id!r} starts on {self.default!r}, which is not one of its options")
        return self

    def option(self, option_id: Optional[str] = None) -> AppModeOption:
        """An option by id, or the one it starts on."""
        wanted = option_id or self.default or self.options[0].id
        for option in self.options:
            if option.id == wanted:
                return option
        raise KeyError(f"The mode {self.id!r} has no option {wanted!r}.")


class AppProfile(_Strict):
    """One of several assistants in one application (LOOP P-20): a variant of its agent.

    The person picks a profile before the conversation starts, and keeps it to
    the end: its instructions are told to the agent on top of the
    application's in every run, its model run in place of the application's
    (a mode's model wins over it), and its starters offered in place of the
    application's.
    """

    id: str = Field(..., pattern=rf"^{MODE_ID}$", description="Its id, what a conversation says it is with")
    label: str = Field(..., min_length=1, description="What the person picks it by")
    description: str = Field(default="", description="What it is for, in a sentence, beside its label")
    instructions: str = Field(
        default="", description="What the agent is told besides its instructions, in every run with this profile"
    )
    model: Optional[str] = Field(
        default=None, description="The model it runs on, in place of the application's; a mode's model wins over it"
    )
    starters: List[AppStarter] = Field(
        default_factory=list,
        description="The first messages it offers, in place of the application's; the application's when empty",
    )


#: The inputs a setting is drawn with (LOOP P-20), each a JSON Schema field and
#: the widget its form's ``ui`` names for it (``ui:widget``; the schema's own
#: when unsaid): what the page draws with ``@datalayer/primer-rjsf``.
SETTING_INPUTS: Dict[str, Tuple[str, str]] = {
    "Select": ("a field with an `enum`", "select (its own)"),
    "Slider": ("a `number` or an `integer` with a `minimum` and a `maximum`", "range"),
    "Switch": ("a `boolean`", "switch"),
    "TextInput": ("a `string`", "text (its own), or textarea"),
    "Checkbox": ("a `boolean`", "checkbox (its own)"),
    "DatePicker": ("a `string` of `format: date`", "date (its own)"),
    "MultiSelect": ("an `array` of `uniqueItems` whose `items` have an `enum`", "select (its own), or checkboxes"),
    "RadioGroup": ("a field with an `enum`", "radio"),
    "Tags": ("an `array` of `string` items without an `enum`", "tags"),
}

#: The widgets a form's ``ui`` may name (``ui:widget``), and the fields each draws.
FORM_WIDGETS = (
    "select",
    "radio",
    "range",
    "updown",
    "switch",
    "checkbox",
    "text",
    "textarea",
    "date",
    "checkboxes",
    "tags",
)


def _widget_refusal(widget: str, field: Mapping[str, Any]) -> Optional[str]:
    """Why a widget cannot draw a field, in words; None when it can."""
    kind = field.get("type")
    items = field.get("items") if isinstance(field.get("items"), Mapping) else {}
    if widget in ("select", "radio"):
        if "enum" in field or (widget == "radio" and kind == "boolean"):
            return None
        if widget == "select" and kind == "array" and "enum" in items:
            return None
        return "draws a choice: the field has an `enum`"
    if widget == "range":
        if kind in ("number", "integer") and "minimum" in field and "maximum" in field:
            return None
        return "is a slider: a `number` or an `integer` with a `minimum` and a `maximum`"
    if widget == "updown":
        return None if kind in ("number", "integer") else "draws a `number` or an `integer`"
    if widget in ("switch", "checkbox"):
        return None if kind == "boolean" else "draws a `boolean`"
    if widget in ("text", "textarea"):
        return None if kind == "string" else "draws a `string`"
    if widget == "date":
        return None if kind == "string" else "draws a `string` of `format: date`"
    if widget == "checkboxes":
        return None if kind == "array" and "enum" in items else "draws an `array` whose `items` have an `enum`"
    if widget == "tags":
        if kind == "array" and items.get("type") == "string" and "enum" not in items:
            return None
        return "draws an `array` of `string` items without an `enum`"
    return f"is no widget: {', '.join(FORM_WIDGETS)}"


def form_ui_problems(said: str, schema: Mapping[str, Any], ui: Any) -> List[str]:
    """What is wrong with how a form's fields are drawn (LOOP P-20), in sentences.

    ``ui`` is the form's uiSchema as ``@datalayer/primer-rjsf`` reads it: by
    field name, the ``ui:`` options of each — ``ui:widget`` one of
    :data:`FORM_WIDGETS` that draws the field — and ``ui:order`` at its top.
    """
    if not isinstance(ui, Mapping):
        return [f"{said} is drawn by field name: its `ui` is a mapping."]
    fields = schema.get("properties") if isinstance(schema.get("properties"), Mapping) else {}
    problems: List[str] = []
    for name, options in ui.items():
        if name == "ui:order":
            unknown = [item for item in options or [] if item != "*" and item not in fields]
            if not isinstance(options, list) or unknown:
                problems.append(f"{said} orders fields it does not ask: {', '.join(map(repr, unknown)) or options!r}.")
            continue
        if str(name).startswith("ui:"):
            continue
        if name not in fields:
            problems.append(f"{said} says how to draw {name!r}, which it does not ask.")
            continue
        if not isinstance(options, Mapping):
            problems.append(f"{said}'s field {name!r} is drawn with `ui:` options, a mapping.")
            continue
        wrong = [key for key in options if not str(key).startswith("ui:") and key != "items"]
        if wrong:
            problems.append(f"{said}'s field {name!r} is drawn with `ui:` options, not {', '.join(map(repr, wrong))}.")
        widget = options.get("ui:widget")
        if widget is None:
            continue
        refusal = _widget_refusal(str(widget), fields[name]) if isinstance(fields[name], Mapping) else None
        if refusal:
            problems.append(f"{said}'s field {name!r} is drawn with {widget!r}, which {refusal}.")
    return problems


#: A language, as BCP 47 tags it (LOOP P-26): a language of two or three
#: letters, then optionally its script, its region and its variants — ``fr``,
#: ``pt-BR``, ``zh-Hant-TW``.
LANGUAGE_TAG = re.compile(
    r"^[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?(?:-(?:[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}))*$"
)


def pick_language(available: Sequence[str], preferred: Sequence[str]) -> Optional[str]:
    """The first language a person prefers that is available (LOOP P-26), or None.

    Tags are compared without case; a preferred tag also matches an available
    one of its language alone or of the same language (``fr-CA`` takes ``fr``,
    then ``fr-FR``), the exact one first.
    """
    by_tag = {tag.lower(): tag for tag in available}
    for wanted in preferred:
        tag = str(wanted).strip().lower()
        if not tag:
            continue
        if tag in by_tag:
            return by_tag[tag]
        language = tag.split("-")[0]
        if language in by_tag:
            return by_tag[language]
        for candidate, original in by_tag.items():
            if candidate.split("-")[0] == language:
                return original
    return None


class AppStarterTranslation(_Strict):
    """A starter in another language."""

    label: str = Field(default="", description="What the button says")
    message: str = Field(default="", description="What is sent when it is chosen")


class AppFieldTranslation(_Strict):
    """A field of the settings in another language."""

    title: str = Field(default="", description="Its title")
    description: str = Field(default="", description="What it is for")
    options: Dict[str, str] = Field(
        default_factory=dict,
        description="What each value of its `enum` (or of its items') reads as, by the value; the value is sent",
    )


class AppOptionTranslation(_Strict):
    """An option of a mode in another language."""

    label: str = Field(default="", description="What the switch says")
    description: str = Field(default="", description="What it changes")


class AppModeTranslation(_Strict):
    """A mode in another language."""

    label: str = Field(default="", description="What the switch is called")
    options: Dict[str, AppOptionTranslation] = Field(default_factory=dict, description="Its options, by id")


class AppProfileTranslation(_Strict):
    """A profile in another language."""

    label: str = Field(default="", description="What the person picks it by")
    description: str = Field(default="", description="What it is for")


class AppTranslation(_Strict):
    """What a person reads of an application, in another language (LOOP P-26).

    Each part is keyed by what names it in the spec: a starter by its label,
    a category by its words, a setting by its field, a command by its name,
    a mode and a profile by their ids. What is not translated is shown in
    the spec's own words; what is translated is shown, never sent, but a
    starter's message — the agent is written to in the person's language.
    """

    name: str = Field(default="", description="Its display name")
    description: str = Field(default="", description="What it does")
    welcome: str = Field(default="", description="What it says first")
    starters: Dict[str, AppStarterTranslation] = Field(
        default_factory=dict, description="Its starters and its profiles', by their label"
    )
    categories: Dict[str, str] = Field(default_factory=dict, description="The starters' categories, by their words")
    settings: Dict[str, AppFieldTranslation] = Field(
        default_factory=dict, description="The fields of its settings, by name"
    )
    commands: Dict[str, str] = Field(default_factory=dict, description="Its commands' descriptions, by name")
    modes: Dict[str, AppModeTranslation] = Field(default_factory=dict, description="Its modes, by id")
    profiles: Dict[str, AppProfileTranslation] = Field(default_factory=dict, description="Its profiles, by id")


class AppSurface(_Strict):
    """The component tree the user meets, over the approved catalog (A2UI)."""

    protocol: str = Field(default="a2ui/v0.9", description="The protocol the tree is written in")
    components: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="The components, as the protocol's `updateComponents` carries them",
    )
    composed_by: str = Field(
        default="",
        description="Who composed it: a model's id, `canvas` (a person on the Canvas), `developer`, `template`",
    )
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


class ThemeVariant(str, Enum):
    """A theme of Datalayer's, as Appearance names it (LOOP T-30)."""

    DATALAYER = "datalayer"
    SPATIAL = "spatial"
    LOVELY = "lovely"
    MATRIX = "matrix"
    EARTH = "earth"
    SAND = "sand"
    IVORY = "ivory"
    SUN = "sun"
    LOOP = "loop"


class ThemeMode(str, Enum):
    """The colour mode a theme is worn in: `auto` follows the device."""

    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


class AppTheme(_Strict):
    """The theme an application runs in by default (LOOP T-30)."""

    variant: ThemeVariant = Field(
        description=(
            "The theme: `datalayer`, `spatial`, `lovely`, `matrix`, `earth`, `sand`, `ivory`, `sun` or `loop`"
        ),
    )
    mode: Optional[ThemeMode] = Field(
        default=None,
        description="`light`, `dark` or `auto` (the device's); the person's own when unsaid",
    )


class BalloonDisplay(str, Enum):
    """How a floating assistant's balloon shows the conversation (LOOP T-23)."""

    HISTORY = "history"
    """Every message, scrolled, the composer last."""

    CURRENT = "current"
    """Only what it says or does now: the answer being written, or the tool it calls."""


class VoiceInput(str, Enum):
    """How a person talks to the application (VOICE.md VO-10, VO-12)."""

    OFF = "off"
    PUSH_TO_TALK = "push_to_talk"
    HANDS_FREE = "hands_free"


class VoiceOutput(str, Enum):
    """When its answers are heard (VO-21)."""

    OFF = "off"
    ON_REQUEST = "on_request"
    ALWAYS = "always"


class VoiceWhere(str, Enum):
    """Where its speech runs: in the person's browser, on Datalayer's servers, or the better of the two (§5)."""

    AUTO = "auto"
    DEVICE = "device"
    SERVER = "server"


#: A language as BCP 47 writes it, as far as voices need: `en`, `en-US`, `fr-FR`.
VOICE_LANGUAGE = r"[a-z]{2,3}(?:-[A-Z]{2})?"


class AppVoice(_Strict):
    """Its voice (VOICE.md VO-41): whether it listens, whether it speaks, with which voice, in which language.

    Off unless said. What is said becomes a message, and what is heard is the
    answer the conversation shows: the text stays the truth.
    """

    enabled: bool = Field(default=False, description="Whether it has a voice at all; off unless said")
    input: VoiceInput = Field(
        default=VoiceInput.PUSH_TO_TALK,
        description="`off`, `push_to_talk` (hold a key or the microphone, speak, let go) or `hands_free`",
    )
    output: VoiceOutput = Field(
        default=VoiceOutput.ON_REQUEST,
        description="When its answers are heard: `off`, `on_request` (a Read aloud on each answer) or `always`",
    )
    voice: str = Field(
        default="",
        description=(
            "The voice it speaks with, an id of the voice catalogue (`kokoro-af-heart`); "
            "the language's first when unsaid"
        ),
    )
    language: str = Field(
        default="",
        pattern=rf"^(?:{VOICE_LANGUAGE})?$",
        description="The language it listens and speaks in, BCP 47 (`en-US`, `fr-FR`); the person's when unsaid",
    )
    where: VoiceWhere = Field(
        default=VoiceWhere.AUTO,
        description="Where its speech runs: `auto`, `device` (the person's browser) or `server` (Datalayer's)",
    )


#: A media type as an output names it: `type/subtype`, lowercase, no parameters.
MEDIA_TYPE = re.compile(r"[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*")

#: The outputs an answer in words comes in; an application's first output is one.
TEXT_OUTPUTS = ("text/plain", "text/markdown")

#: The largest file a person may send an application, in megabytes: what a runtime takes.
MAX_UPLOAD_MB = 25

#: A kind of file a person may send: a media type (`application/pdf`), a family of
#: them (`image/*`), or an extension (`.csv`).
UPLOAD_KIND = re.compile(r"(?:[a-z0-9][a-z0-9.+-]*/(?:\*|[a-z0-9][a-z0-9.+-]*)|\.[a-z0-9][a-z0-9_+-]*)")


def upload_kind_takes(kind: str, name: str, media_type: str) -> bool:
    """Whether a kind of file takes a file: an extension by its name, a media type or a family by its type."""
    if kind.startswith("."):
        return name.lower().endswith(kind)
    wanted = (media_type or "").split(";", 1)[0].strip().lower()
    if kind.endswith("/*"):
        return wanted.startswith(kind[:-1])
    return wanted == kind


class AppUploadKind(_Strict):
    """A kind of file a person may send, and how large (LOOP P-21)."""

    type: str = Field(
        ...,
        pattern=rf"^{UPLOAD_KIND.pattern}$",
        description=(
            "A media type (`application/pdf`), a family of them (`image/*`, `audio/*`) or an "
            "extension (`.csv`), lowercase"
        ),
    )
    max_mb: float = Field(
        default=10,
        gt=0,
        le=MAX_UPLOAD_MB,
        description=f"The largest file of this kind, in megabytes; {MAX_UPLOAD_MB} at most",
    )


class AppUploads(_Strict):
    """What a person may send in the composer without being asked (LOOP P-21): images, files, audio.

    A file of a kind it does not name, larger than its kind takes, or one too
    many is refused, in a sentence — by the page before it is sent, and by the
    runtime when it is sent all the same.
    """

    kinds: List[AppUploadKind] = Field(
        ..., min_length=1, description="The kinds of file it takes, each with its largest size"
    )
    max_files: int = Field(default=5, ge=1, le=20, description="The most files sent with one message")

    @model_validator(mode="after")
    def _kinds_are_distinct(self) -> "AppUploads":
        types = [kind.type for kind in self.kinds]
        if len(set(types)) != len(types):
            raise ValueError("two kinds of upload have the same type")
        return self

    def kind_of(self, name: str, media_type: str) -> Optional[AppUploadKind]:
        """The first of its kinds that takes a file, or None."""
        return next((kind for kind in self.kinds if upload_kind_takes(kind.type, name, media_type)), None)

    def refusal(self, app_name: str, name: str, media_type: str, size: int) -> Optional[str]:
        """Why a file is refused, in a sentence; None when it is taken."""
        kind = self.kind_of(name, media_type)
        if kind is None:
            taken = ", ".join(kind.type for kind in self.kinds)
            return f"{name} is not a kind of file {app_name} takes: it takes {taken}."
        if size > kind.max_mb * 1024 * 1024:
            return (
                f"{name} is {size / (1024 * 1024):.1f} MB: {app_name} takes {kind.type} "
                f"of at most {kind.max_mb:g} MB."
            )
        return None

    def too_many(self, app_name: str, count: int) -> Optional[str]:
        """Why so many files are refused at once, in a sentence; None when they are not."""
        if count > self.max_files:
            return f"{count} files were sent at once: {app_name} takes at most {self.max_files}."
        return None


class AppInterface(_Strict):
    """What the user sees."""

    layout: Optional[Layout] = Field(default=None, description="`chat`, `page` or `split`; the kind's own when unsaid")
    accent: Accent = Field(default=Accent.GREEN, description="The application's one colour")
    theme: Optional[AppTheme] = Field(
        default=None,
        description=(
            "The theme it runs in by default, at its address, embedded, in the Studio's Preview and as an "
            "example: a `variant` and, optionally, a colour `mode`. The person's own when unsaid. Its "
            "`accent` colours the `loop` theme only"
        ),
    )
    welcome: str = Field(default="", description="What the application says first")
    starters: List[AppStarter] = Field(default_factory=list, description="First messages offered to the user")
    commands: List[AppCommand] = Field(
        default_factory=list,
        description="Slash commands the user picks in the composer: typing `/` lists them (LOOP P-19)",
    )
    modes: List[AppMode] = Field(
        default_factory=list,
        description=(
            "Mode switches in the composer: the option picked goes with every run, its instructions "
            "told to the agent and its model run on (LOOP P-19)"
        ),
    )
    profiles: List[AppProfile] = Field(
        default_factory=list,
        description=(
            "Several assistants in one application, two at least: the person picks one before the "
            "conversation starts — the first unless they do — and keeps it to the end; its "
            "instructions, model and starters go with every run (LOOP P-20). None when unsaid"
        ),
    )
    settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "What the user may set: the JSON Schema of a form, an object of named fields, each with "
            "its `title` and its `default` (LOOP C-16). Drawn with `@datalayer/primer-rjsf` beside "
            "the conversation and on a deployment's Ship card, its values go with every run and are "
            "checked by the runtime against the same schema. None when unsaid"
        ),
    )
    settings_ui: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "How the settings' fields are drawn, as `@datalayer/primer-rjsf` reads a uiSchema: by "
            "field name, its `ui:` options — `ui:widget` one of `select`, `radio`, `range`, "
            "`updown`, `switch`, `checkbox`, `text`, `textarea`, `date`, `checkboxes`, `tags` — and "
            "`ui:order` (LOOP P-20). Each field's own widget when unsaid"
        ),
    )
    language: str = Field(
        default="en",
        description="The language its own words are in, as BCP 47 tags it (`en`, `fr`, `pt-BR`) (LOOP P-26)",
    )
    translations: Dict[str, AppTranslation] = Field(
        default_factory=dict,
        description=(
            "What a person reads of it in other languages, by BCP 47 tag: its name, welcome, "
            "starters and their categories, settings, commands, modes and profiles. The page shows "
            "the person's language when it has it, else its own words (LOOP P-26)"
        ),
    )
    uploads: Optional[AppUploads] = Field(
        default=None,
        description=(
            "What a person may send in the composer without being asked — images, files, audio — "
            "by kind, each with its largest size, and how many at once (LOOP P-21). None when "
            "unsaid: the composer offers no attachment, and a file sent with a message is refused"
        ),
    )
    components: List[str] = Field(
        default_factory=list,
        description="The components of the catalog the surface may use; the kind's own when empty",
    )
    surface: Optional[AppSurface] = Field(default=None, description="The component tree, when there is one")
    assistant: Optional[str] = Field(
        default=None,
        max_length=64,
        pattern=rf"^{ASSISTANT_CHARACTER_ID}$",
        description=(
            "The character its floating assistant shows, by the id a plugin contributes it under "
            "(lowercase letters and digits, words joined by a hyphen): Datalayer's are `paperclip`, "
            "`wizard`, `cat` and `eyes`. The paper clip when unsaid; an id no enabled plugin "
            "contributes is refused where the plugins are known, the runtime and the page. Said "
            "here, it wins over a person's own choice in their settings"
        ),
    )
    balloon: Optional[BalloonDisplay] = Field(
        default=None,
        description=(
            "How its floating assistant's balloon shows the conversation: `history` (every "
            "message, scrolled, the composer last) or `current` (only what it says or does now, "
            "the answer being written or the tool it calls, in one balloon). The page's own "
            "when unsaid: `history` for the floating chat"
        ),
    )
    voice: AppVoice = Field(
        default_factory=lambda: AppVoice(),
        description="Its voice: whether it listens and speaks, with which voice, in which language (off unless said)",
    )
    outputs: List[str] = Field(
        default_factory=list,
        json_schema_extra={
            "items": {"type": "string", "pattern": f"^{MEDIA_TYPE.pattern}$"},
            "uniqueItems": True,
        },
        description=(
            "The formats its answers come in, by media type, words first: `text/markdown`, "
            "then `application/x-ipynb+json` for a Jupyter notebook. Over A2A, its agent "
            "card's output modes; a caller asks for some of them (`acceptedOutputModes`). "
            "Plain text alone when unsaid"
        ),
    )

    @field_validator("settings", mode="before")
    @classmethod
    def _settings_are_a_form(cls, value: Any) -> Any:
        if isinstance(value, list):
            raise ValueError(
                "interface.settings is the JSON Schema of a form, an object of named fields "
                "(LOOP C-16), not a list of settings: say each one as a property, its title "
                "and its default"
            )
        return value

    @model_validator(mode="after")
    def _names_are_distinct(self) -> "AppInterface":
        if self.settings is not None:
            problems = form_problems({"id": "settings", "schema": self.settings})
            if problems:
                raise ValueError(" ".join(problems))
        names = [command.name for command in self.commands]
        if len(set(names)) != len(names):
            raise ValueError("two commands have the same name")
        modes = [mode.id for mode in self.modes]
        if len(set(modes)) != len(modes):
            raise ValueError("two modes have the same id")
        choosing = [mode.id for mode in self.modes if any(option.model for option in mode.options)]
        if len(choosing) > 1:
            raise ValueError(f"only one mode chooses the model a run runs on, not {', '.join(choosing)}")
        if self.settings_ui is not None:
            if self.settings is None:
                raise ValueError("`settings_ui` draws the settings' fields: say `settings` first")
            problems = form_ui_problems("The form 'settings'", self.settings, self.settings_ui)
            if problems:
                raise ValueError(" ".join(problems))
        profiles = [profile.id for profile in self.profiles]
        if len(set(profiles)) != len(profiles):
            raise ValueError("two profiles have the same id")
        if len(profiles) == 1:
            raise ValueError(
                "one profile is the application itself: say two at least, or put its "
                "instructions, model and starters on the application"
            )
        self._translations_hold()
        return self

    def _translations_hold(self) -> None:
        """Every translation is of a language, and of something the application says."""
        if not LANGUAGE_TAG.match(self.language):
            raise ValueError(f"{self.language!r} is no language as BCP 47 tags it: `en`, `fr`, `pt-BR`")
        seen: Dict[str, str] = {}
        starters = {starter.label for starter in self.starters}
        starters |= {starter.label for profile in self.profiles for starter in profile.starters}
        categories = {starter.category for starter in self.starters if starter.category}
        categories |= {starter.category for profile in self.profiles for starter in profile.starters if starter.category}
        fields = dict((self.settings or {}).get("properties") or {})
        modes = {mode.id: mode for mode in self.modes}
        for tag, translation in self.translations.items():
            if not LANGUAGE_TAG.match(tag):
                raise ValueError(f"the translation {tag!r} is of no language as BCP 47 tags it: `fr`, `pt-BR`")
            if tag.lower() == self.language.lower():
                raise ValueError(f"its own words are in {self.language!r}: no translation into it")
            if tag.lower() in seen:
                raise ValueError(f"{seen[tag.lower()]!r} and {tag!r} are the same language")
            seen[tag.lower()] = tag
            said = f"The translation {tag!r}"
            unknown = [
                *(f"the starter {label!r}" for label in translation.starters if label not in starters),
                *(f"the category {name!r}" for name in translation.categories if name not in categories),
                *(f"the setting {name!r}" for name in translation.settings if name not in fields),
                *(f"the command {name!r}" for name in translation.commands if self.command(name) is None),
                *(f"the mode {name!r}" for name in translation.modes if name not in modes),
                *(f"the profile {name!r}" for name in translation.profiles if self.profile(name) is None),
            ]
            for mode_id, mode in translation.modes.items():
                if mode_id in modes:
                    ids = {option.id for option in modes[mode_id].options}
                    unknown += [f"the option {option!r} of {mode_id!r}" for option in mode.options if option not in ids]
            for name, field in translation.settings.items():
                values = _enum_values(fields.get(name))
                unknown += [f"the value {value!r} of {name!r}" for value in field.options if value not in values]
            if unknown:
                raise ValueError(f"{said} translates what the application does not say: {', '.join(unknown)}")

    def profile(self, profile_id: str) -> Optional[AppProfile]:
        """A profile by id (LOOP P-20), or None."""
        return next((profile for profile in self.profiles if profile.id == profile_id), None)

    def profile_choice(self, chosen: Optional[str] = None) -> Optional[AppProfile]:
        """The profile a conversation is with: the one chosen, else the first; None without profiles.

        Raises
        ------
        ValueError
            When the profile chosen is not the application's, or one is chosen and it has none.
        """
        if chosen:
            profile = self.profile(chosen)
            if profile is None:
                raise ValueError(f"There is no profile {chosen!r}.")
            return profile
        return self.profiles[0] if self.profiles else None

    def starters_for(self, profile_id: Optional[str] = None) -> List[AppStarter]:
        """The starters offered: the profile's, else the application's (LOOP P-20)."""
        profile = self.profile_choice(profile_id)
        return list(profile.starters) if profile is not None and profile.starters else list(self.starters)

    def translated(self, preferred: Sequence[str]) -> "AppInterface":
        """What a person who prefers these languages reads (LOOP P-26): its words in
        the first of them it has a translation into, else its own.
        """
        tag = pick_language([self.language, *self.translations], preferred)
        if tag is None or tag not in self.translations:
            return self
        words = self.translations[tag]

        def starter(item: AppStarter) -> AppStarter:
            said = words.starters.get(item.label)
            return item.model_copy(
                update={
                    "label": (said and said.label) or item.label,
                    "message": (said and said.message) or item.message,
                    "category": words.categories.get(item.category, item.category),
                }
            )

        settings = None
        if self.settings is not None:
            settings = json.loads(json.dumps(self.settings))
            for name, field in words.settings.items():
                target = settings["properties"][name]
                if field.title:
                    target["title"] = field.title
                if field.description:
                    target["description"] = field.description
        modes = [_mode_in(mode, words.modes.get(mode.id)) for mode in self.modes]
        return self.model_copy(
            update={
                "welcome": words.welcome or self.welcome,
                "starters": [starter(item) for item in self.starters],
                "commands": [
                    command.model_copy(update={"description": words.commands.get(command.name) or command.description})
                    for command in self.commands
                ],
                "modes": modes,
                "profiles": [
                    profile.model_copy(
                        update={
                            "label": (words.profiles.get(profile.id) and words.profiles[profile.id].label)
                            or profile.label,
                            "description": (words.profiles.get(profile.id) and words.profiles[profile.id].description)
                            or profile.description,
                            "starters": [starter(item) for item in profile.starters],
                        }
                    )
                    for profile in self.profiles
                ],
                "settings": settings,
                "settings_ui": _with_option_names(self.settings_ui, words, settings),
                "language": tag,
                "translations": {},
            }
        )

    def command(self, name: str) -> Optional[AppCommand]:
        """A command by its name, without the slash."""
        return next((command for command in self.commands if command.name == name), None)

    def mode_choice(self, chosen: Optional[Mapping[str, Any]] = None) -> Dict[str, str]:
        """The option of every mode a run is in: what was chosen, else where each starts.

        Raises
        ------
        ValueError
            When a mode or an option chosen is not the application's.
        """
        chosen = dict(chosen or {})
        known = {mode.id: mode for mode in self.modes}
        for mode_id, option_id in chosen.items():
            mode = known.get(mode_id)
            if mode is None:
                raise ValueError(f"There is no mode {mode_id!r}.")
            if not isinstance(option_id, str) or option_id not in {option.id for option in mode.options}:
                raise ValueError(f"The mode {mode_id!r} has no option {option_id!r}.")
        return {mode.id: mode.option(chosen.get(mode.id)).id for mode in self.modes}

    def mode_effect(self, chosen: Optional[Mapping[str, Any]] = None) -> Tuple[str, Optional[str]]:
        """What a run in the modes chosen is told, and the model it runs on (None: the application's)."""
        choice = self.mode_choice(chosen)
        options = [mode.option(choice[mode.id]) for mode in self.modes]
        instructions = "\n\n".join(option.instructions.strip() for option in options if option.instructions.strip())
        model = next((option.model for option in options if option.model), None)
        return instructions, model

    @field_validator("outputs")
    @classmethod
    def _outputs_are_media_types(cls, outputs: List[str]) -> List[str]:
        for output in outputs:
            if not MEDIA_TYPE.fullmatch(output):
                raise ValueError(
                    f"{output!r} is not a media type, `type/subtype` in lowercase: `text/markdown`"
                )
        if len(set(outputs)) != len(outputs):
            raise ValueError("an output is named twice")
        if outputs and outputs[0] not in TEXT_OUTPUTS:
            raise ValueError(
                "its answers come in words first: "
                "the first output is `text/plain` or `text/markdown`"
            )
        return outputs


def _enum_values(field: Any) -> List[str]:
    """The values a field takes, or its items take, as words: what a translation names them by."""
    if not isinstance(field, Mapping):
        return []
    items = field.get("items") if isinstance(field.get("items"), Mapping) else {}
    return [str(value) for value in (field.get("enum") or items.get("enum") or [])]


def _mode_in(mode: AppMode, words: Optional[AppModeTranslation]) -> AppMode:
    """A mode in another language: what is translated of it, else its own words."""
    if words is None:
        return mode
    options = []
    for option in mode.options:
        said = words.options.get(option.id)
        options.append(
            option.model_copy(
                update={
                    "label": (said and said.label) or option.label,
                    "description": (said and said.description) or option.description,
                }
            )
        )
    return mode.model_copy(update={"label": words.label or mode.label, "options": options})


def _with_option_names(
    ui: Optional[Dict[str, Any]], words: AppTranslation, settings: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """The settings' uiSchema, a translated field's values named in the language (``ui:enumNames``)."""
    named = {name: field for name, field in words.settings.items() if field.options}
    if not named or settings is None:
        return ui
    drawn = json.loads(json.dumps(ui or {}))
    for name, field in named.items():
        values = _enum_values(settings["properties"].get(name))
        drawn.setdefault(name, {})["ui:enumNames"] = [field.options.get(value, value) for value in values]
    return drawn


# --- how it is verified, and what is kept -------------------------------------------


#: The name of a function of an application's code: what `code` and a code
#: check name, and what an application's own tool is called (LOOP P-06).
CODE_NAME = r"[A-Za-z_][A-Za-z0-9_]*"


class AppTestCase(_Strict):
    """An example of what the application should do, in plain words.

    When plain words are not enough, its code decides it (LOOP P-06): `code`
    names the function of the application's `app.py` that is given the
    conversation and says whether it passed — `@app.test` writes it. `expect`
    still says it in words: without its file, the case is judged by them.
    """

    ask: str = Field(..., description="What it is asked")
    expect: str = Field(..., description="What it should do")
    code: str = Field(
        default="",
        pattern=rf"^(?:{CODE_NAME})?$",
        description=(
            "The function of its code that decides the case, by name, when words are not enough; "
            "`expect` says it in words"
        ),
    )


class AppVerified(_Strict):
    """What was verified, and how, each in a sentence a person reads (LOOP E-14).

    An example says it on its card and on its page: what was tried live,
    what runs on recorded data instead, and what is not verified yet. Said
    by whoever tried it; nothing here is computed.
    """

    live: List[str] = Field(default_factory=list, description="What was tried live, where and when")
    recorded: List[str] = Field(
        default_factory=list, description="What runs on recorded data, not on live calls"
    )
    unverified: List[str] = Field(default_factory=list, description="What is not verified yet")


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
    verified: AppVerified = Field(
        default_factory=lambda: AppVerified(),
        description="What was verified live, what runs on recorded data, and what is not verified yet",
    )


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
    AUDIO = "audio"
    """What was said aloud, as sound: off unless named, never for a public deployment (VOICE.md VO-42)."""


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
    suggest_tests: bool = Field(
        default=False,
        description=(
            "Whether its conversations may be used to suggest tests: a few, sampled from "
            "those kept while it is on, proposed to its builder; off unless said"
        ),
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


#: What each item a Track includes keeps of an application's record, in the
#: words of `record.include` (LOOP R-07). A Track's other items — the Op, the
#: Frames, the model versions, who read it — are not entries of an
#: application's record: its session already says the application, its
#: version and who opened it.
TRACK_KEEPS: Dict[str, Tuple[str, ...]] = {
    "input_data": ("conversations",),
    "actions_taken": ("actions",),
    "gate_decisions": ("checks", "decisions"),
    "guard_results": ("checks",),
    "human_approvals": ("approvals",),
    "source_documents": ("sources",),
    "final_output": ("outputs",),
}


class KeptRecord(BaseModel):
    """What an application's record keeps, and for how long, as it is applied."""

    model_config = ConfigDict(frozen=True)

    days: int = Field(..., description="How many days each entry is kept")
    include: Tuple[str, ...] = Field(
        ..., description="What is kept, in the words of `record.include`"
    )
    track: str = Field(default="", description="The Track that decided it, when one did")


def kept_record(keep_for: str, include: Sequence[Any], track: str = "") -> KeptRecord:
    """What an application's record keeps, and for how long (LOOP R-07).

    As its `record` says — or, when it names a Track under `checks`, as the
    Track says: the Track's retention in place of `keep_for`, and what its
    items keep (`TRACK_KEEPS`) besides what `include` names. A Track is an
    evidence policy: it never keeps less than the application asked for.

    Raises `AppError` for a Track the catalogue does not have.
    """
    kept = [str(getattr(item, "value", item)) for item in include]
    if not track.strip():
        return KeptRecord(days=retention_days(keep_for), include=tuple(dict.fromkeys(kept)))
    from ..tracks import get_track

    found = get_track(track.strip())
    if found is None:
        raise AppError(f"There is no Track named {track.strip()!r}.")
    for item in found.include:
        kept += TRACK_KEEPS.get(item.value, ())
    return KeptRecord(days=found.retention_days, include=tuple(dict.fromkeys(kept)), track=found.id)


class CheckStage(str, Enum):
    """Where a check of its code runs (LOOP P-06), as the built-in checks do (R-06)."""

    ANSWER = "answer"
    """On every answer, before it is given: one it refuses is asked again."""

    TOOL_CALL = "tool_call"
    """On every tool call the rules let through: one it refuses is stopped."""


class AppCodeCheck(_Strict):
    """A check written in the application's code (LOOP P-06): `@app.check`.

    Run at its stage beside the built-in checks and the catalogue's Guards;
    what it refuses is said in its own sentence. Without its file nothing
    runs it, and validation says so.
    """

    name: str = Field(..., pattern=rf"^{CODE_NAME}$", description="The function of its code that checks, by name")
    on: CheckStage = Field(..., description="`answer` or `tool_call`: where it runs")
    description: str = Field(..., min_length=1, description="What it checks, in a sentence a person reads")


class AppChecks(_Strict):
    """Optional: checks from the catalogue, for a builder who wants them — and its code's own."""

    guards: List[str] = Field(default_factory=list, description="Guards, `id` or `id:version`")
    gates: List[str] = Field(default_factory=list, description="Gates, `id` or `id:version`")
    track: str = Field(default="", description="A Track, `id` or `id:version`")
    code: List[AppCodeCheck] = Field(
        default_factory=list,
        description="Checks written in its code (`@app.check`), each run at its stage (LOOP P-06)",
    )


class AppTool(_Strict):
    """A tool of the application's own, written in its code (LOOP P-06): `@app.tool`.

    Its agent calls it as any tool; the rules decide each call by what it
    `does` — a rule may name it, by its name alone — and the Canvas lists it.
    Without its file the agent is not given it.
    """

    name: str = Field(
        ..., pattern=rf"^{CODE_NAME}$", description="Its name: what the agent calls, and a rule names"
    )
    description: str = Field(..., min_length=1, description="What it does, for the agent: when to call it")
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="The JSON Schema of its arguments, an object; none when unsaid",
    )
    does: List[ActionClass] = Field(
        ...,
        min_length=1,
        description="What it does, by class of action (`read`, `write`, `send`…): what the rules decide",
    )

    @field_validator("parameters")
    @classmethod
    def _is_an_object(cls, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if parameters.get("type") != "object" or not isinstance(parameters.get("properties", {}), dict):
            raise ValueError("a tool's `parameters` are the JSON Schema of an object, its arguments its properties")
        return parameters

    @field_validator("does")
    @classmethod
    def _each_once(cls, does: List[ActionClass]) -> List[ActionClass]:
        if len(set(does)) != len(does):
            raise ValueError("a tool says each thing it does once")
        return does


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
    """The application in the page."""

    BUBBLE = "bubble"
    """A floating button that opens it: the copilot pattern."""

    PANEL = "panel"
    """A side panel."""

    ASSISTANT = "assistant"
    """A character on the page that speaks in a balloon (LOOP §6.9)."""


class HostedDeployment(_Strict):
    """The application at an address of its own."""

    visibility: Visibility = Field(default=Visibility.PRIVATE, description="Who can open it")
    slug: str = Field(default="", description="The readable part of its address")
    character_alone: bool = Field(
        default=False,
        description=(
            "At its address, only its character: the conversation opens in its balloon, "
            "as when it is shipped as `assistant`"
        ),
    )

    @field_validator("slug")
    @classmethod
    def _is_a_slug(cls, slug: str) -> str:
        if slug and not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", slug):
            raise ValueError(f"cannot use {slug!r} in an address: lower-case letters, digits and hyphens")
        return slug


_ORIGIN = re.compile(r"^https://[A-Za-z0-9.-]+(?::\d+)?$|^http://(?:localhost|127\.0\.0\.1)(?::\d+)?$")


_HOST_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")

#: The tool its agent reads what the host page passes it with (LOOP D-10).
HOST_CONTEXT_TOOL = "host_context"


def host_tool(function: str) -> str:
    """The tool its agent calls a host function with: ``host_`` and its name."""
    return f"host_{function}"


class HostFunction(_Strict):
    """A function of the host page the application's agent may call (LOOP D-10)."""

    name: str = Field(..., description="Its name, lower-case words joined by `_`: `open_ticket`")
    description: str = Field(..., description="What it does, for the agent: when to call it")
    parameters: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="Its arguments, as a JSON Schema object",
    )

    @field_validator("name")
    @classmethod
    def _is_a_name(cls, name: str) -> str:
        if not _HOST_NAME.match(name):
            raise ValueError(f"cannot use {name!r} as a host function: lower-case letters, digits and `_`")
        return name

    @field_validator("description")
    @classmethod
    def _says_what(cls, description: str) -> str:
        if not description.strip():
            raise ValueError("a host function says what it does")
        return description.strip()

    @field_validator("parameters")
    @classmethod
    def _is_an_object(cls, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if parameters.get("type") != "object":
            raise ValueError("a host function's parameters are a JSON Schema of `type: object`")
        return parameters


class HostBridge(_Strict):
    """What the host page and the application say to each other (LOOP D-10).

    The values of the host it reads (`context`: `user`, `page`, or a name of
    the host's own), through the tool `host_context`; the functions of the
    host it may call, each through `host_<name>`. Every one of these tools is
    decided by a rule that names it, as any tool is: one no rule names is
    left to the person.
    """

    context: List[str] = Field(
        default_factory=list, description="The host's values it reads: `user`, `page`, or names of the host's own"
    )
    functions: List[HostFunction] = Field(default_factory=list, description="The host's functions it may call")

    @field_validator("context")
    @classmethod
    def _are_names(cls, context: List[str]) -> List[str]:
        for name in context:
            if not _HOST_NAME.match(name):
                raise ValueError(f"cannot use {name!r} as a value of the host: lower-case letters, digits and `_`")
        if len(set(context)) != len(context):
            raise ValueError("the host's values are named once each")
        return context

    @model_validator(mode="after")
    def _functions_named_once(self) -> "HostBridge":
        names = [function.name for function in self.functions]
        if len(set(names)) != len(names):
            raise ValueError("the host's functions are named once each")
        return self

    @property
    def tools(self) -> List[str]:
        """The tools its agent is given for the host."""
        return ([HOST_CONTEXT_TOOL] if self.context else []) + [host_tool(f.name) for f in self.functions]


class EmbeddedDeployment(_Strict):
    """The application inside another product's page."""

    mode: EmbedMode = Field(default=EmbedMode.INLINE, description="`inline`, `bubble`, `panel` or `assistant`")
    origins: List[str] = Field(default_factory=list, description="The origins allowed to embed it")
    host: Optional[HostBridge] = Field(
        default=None, description="What the host page passes it and the functions of the host it may call"
    )

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
    """What an alternative is weighed on."""

    name: str = Field(..., description="Its name")
    kind: CriterionKind = Field(default=CriterionKind.METRIC, description="`metric`, `noul`, `choice`, `score`")
    weight: float = Field(default=1, ge=0, description="How much it counts")
    instructions: str = Field(default="", description="What a decision model is asked, or how a metric is computed")
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
            raise ValueError(f"say what is asked for {self.name!r}")
        return self


class AppScenario(_Strict):
    """A named set of weights: one way of looking at the same findings."""

    name: str = Field(..., description="Its name")
    weights: Dict[str, float] = Field(default_factory=dict, description="By criterion name")


class AppDecision(_Strict):
    """What a decision application decides."""

    question: str = Field(..., description="The question it answers")
    alternatives: List[str] = Field(default_factory=list, description="What is chosen between")
    criteria: List[AppCriterion] = Field(default_factory=list, description="What each is weighed on")
    min_confidence: float = Field(
        default=0,
        ge=0,
        le=1,
        description="An answer less confident than this is put to the reader",
    )
    scenarios: List[AppScenario] = Field(default_factory=list, description="Named sets of weights")
    decision_model: str = Field(default="", description="The model that answers the decision's typed questions")

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
    backend_tools: List[str] = Field(
        default_factory=list, description="Backend tools of the catalogue it adds to its agent's"
    )

    tools: List[AppTool] = Field(
        default_factory=list,
        description="Tools of its own, written in its code (`@app.tool`): the agent calls them, rules decide them",
    )
    context: List[str] = Field(
        default_factory=list,
        description="The Frames it works under: the catalogue's, or its organization's own (`org-…`)",
    )
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
    unavailable_because: str = Field(
        default="",
        description=(
            "Why it is not offered today, in a sentence its page shows: "
            "said when `enabled` is false, and only then"
        ),
    )
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="apps", description="Icon identifier")
    emoji: str = Field(
        default="\U0001f440",
        description="Its face: one emoji, shown wherever the application appears",
    )
    avatar: str = Field(
        default="",
        description=(
            "Its avatar, by name: a drawing of the set people choose theirs from on their profile. "
            "Its emoji stands for it when unsaid, and where only text goes"
        ),
        json_schema_extra=_DRAWING_SCHEMA,
    )
    banner: str = Field(
        default="",
        description=(
            "Its banner, by name, from the set people choose theirs from on their profile. "
            "The one its id seeds when unsaid"
        ),
        json_schema_extra=_DRAWING_SCHEMA,
    )

    @field_validator("emoji")
    @classmethod
    def _is_a_face(cls, emoji: str) -> str:
        face = emoji.strip()
        if not face or len(face) > 16 or any(character.isalnum() or character.isspace() for character in face):
            raise ValueError("an application's `emoji` is one emoji, its face")
        return face

    @field_validator("avatar", "banner")
    @classmethod
    def _is_a_drawing(cls, name: str) -> str:
        # The sets are the interface's (core's PRINCIPAL_AVATAR_ICONS and
        # PRINCIPAL_BANNERS): this says a name is one, the interface whether
        # it is in them — and draws the emoji, or the seeded banner, if not.
        name = name.strip()
        if name and not re.fullmatch(DRAWING_NAME, name):
            raise ValueError("an avatar or a banner is named as its drawing is, `AstronautIcon`")
        return name

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
        if not self.enabled and not self.unavailable_because.strip():
            raise ValueError("an application that is not offered says why, under `unavailable_because`")
        if self.enabled and self.unavailable_because.strip():
            raise ValueError(
                "an application offered today is available: remove `unavailable_because`, or set `enabled: false`"
            )
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
        if RecordItem.AUDIO in self.record.include:
            hosted = self.deployment.hosted
            if hosted is not None and hosted.visibility is Visibility.PUBLIC:
                raise ValueError(
                    "a public application keeps no audio: remove `audio` from `record.include`, "
                    "or open it to fewer people"
                )
            if not self.interface.voice.enabled or self.interface.voice.input is VoiceInput.OFF:
                raise ValueError("an application keeps audio only when it listens: turn `interface.voice` on")
        servers = [_id_of(connection.server) for connection in self.connections]
        if len(set(servers)) != len(servers):
            raise ValueError("the application connects to the same server twice")
        actions = [rule.action.lower() for rule in self.rules]
        if len(set(actions)) != len(actions):
            raise ValueError("two rules have the same action")
        # What its code declares is known by name (LOOP P-06): each name once.
        tools = [tool.name for tool in self.tools]
        if len(set(tools)) != len(tools):
            raise ValueError("two of its tools have the same name")
        catalogued = sorted(set(tools) & {_id_of(ref) for ref in self.backend_tools})
        if catalogued:
            raise ValueError(
                f"its tool {catalogued[0]!r} has the name of a backend tool it names: call one of them otherwise"
            )
        checks = [check.name for check in self.checks.code]
        if len(set(checks)) != len(checks):
            raise ValueError("two checks of its code have the same name")
        decided = [case.code for case in self.tests.cases if case.code]
        if len(set(decided)) != len(decided):
            raise ValueError("two tests are decided by the same function of its code")
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

    def translated(self, preferred: Sequence[str]) -> "AppSpec":
        """The application as a person who prefers these languages reads it (LOOP P-26):
        its name, description and interface in the first of them it is translated
        into, else in its own words. What it does — its agent, rules, ids — is the same.
        """
        interface = self.interface.translated(preferred)
        if interface is self.interface:
            return self
        words = self.interface.translations[interface.language]
        return self.model_copy(
            update={
                "name": words.name or self.name,
                "description": words.description or self.description,
                "interface": interface,
            }
        )

    def tool(self, name: str) -> Optional[AppTool]:
        """Its own tool of that name (LOOP P-06), or None."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

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

    ``tool`` is ``server.tool`` for a tool of an MCP server, the id of a
    tool of the catalogue, or the name of one of its own tools (LOOP P-06).
    Its classes are the catalogue's — or, for its own, what it says it
    ``does`` — unless given.
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
    # Its own tool does what it says it does (LOOP P-06).
    own_tool = app.tool(name) if server is None and classes is None else None
    if own_tool is not None:
        classes = own_tool.does
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


def output_media_types() -> List[str]:
    """Every media type the outputs catalogue gives (its `mime_types`), each once.

    What an application's `interface.outputs` may name.
    """
    found: List[str] = []
    for spec in _catalogue("outputs").values():
        for media_type in spec.get("mime_types") or []:
            if media_type not in found:
                found.append(str(media_type))
    return found


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
    refs += [("backend tool", "backend-tools", ref) for ref in app.backend_tools]
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


def component_named(name: str) -> Optional[Dict[str, Any]]:
    """The component a layout names (LOOP C-13), from the catalogs of the UI
    plugins an application may use (`ui-plugins/*.yaml`, `components`), by the
    name a surface gives it. None when no enabled plugin renders it."""
    for plugin in _catalogue("ui-plugins").values():
        if not plugin.get("enabled"):
            continue
        for component in plugin.get("components") or []:
            if component["id"] == name:
                return component
    return None


def form_problems(node: Mapping[str, Any]) -> List[str]:
    """What stops a Form block from asking (LOOP C-16), in sentences.

    A form is what an application asks of a person — a quote's parameters, an
    approval's reason — as the JSON Schema of its fields: an object whose
    fields are named, each required one among them, so that the page draws it
    and the runtime checks what it receives against the same schema. An
    application's settings are one such form (``interface.settings``, checked
    as the form ``'settings'``): what a run is given, and a deployment set.
    """
    said = f"The form {node['id']!r}"
    schema = node.get("schema")
    if not isinstance(schema, Mapping):
        return [f"{said} has no fields: its schema is the JSON Schema of what it asks."]
    if schema.get("type") != "object" or not isinstance(schema.get("properties"), Mapping) or not schema["properties"]:
        return [f"{said} asks for no named field: its schema is an object with properties."]
    problems = []
    for name, field in schema["properties"].items():
        if not isinstance(field, Mapping):
            problems.append(f"{said}'s field {name!r} is not a schema.")
    missing = [name for name in schema.get("required") or [] if name not in schema["properties"]]
    if missing:
        problems.append(f"{said} requires {', '.join(repr(name) for name in missing)}, which it does not ask.")
    if node.get("ui") is not None:
        problems += form_ui_problems(said, schema, node["ui"])
    return problems


def app_problems(app: AppSpec, organization_frames: Optional[Sequence[str]] = None) -> List[str]:
    """What stops an application from being used, in sentences; empty when nothing does.

    Every reference resolves, every rule applies to something the application
    can reach, and what it asks of the catalogue's Gates is run by its Guards.

    A context of an organization's own (``org-…``, LOOP U-32) is not the
    catalogue's: it resolves among ``organization_frames``, the ids of the
    organization the application belongs to, and is refused when they are not
    known — no organization was said.
    """
    from ..frames import is_organization_frame

    problems: List[str] = []
    if app.agent and _agent_of(app) is None:
        problems.append(f"There is no agent or Cog named {app.agent!r}.")
    for what, catalogue, ref in _refs(app):
        if catalogue == "frames" and is_organization_frame(ref):
            if organization_frames is None:
                problems.append(
                    f"{ref!r} is a context of an organization's own: "
                    "it is checked with the organization the application belongs to, which was not said."
                )
            elif _id_of(ref) not in organization_frames:
                problems.append(f"Its organization has no context named {ref!r}.")
        elif _id_of(ref) not in _catalogue(catalogue):
            problems.append(f"There is no {what} named {ref!r}.")
    from ..models import get_model

    if app.model and get_model(app.model) is None:
        problems.append(f"There is no model named {app.model!r}.")
    # The model a mode runs on is the catalogue's (LOOP P-19).
    for mode in app.interface.modes:
        for option in mode.options:
            if option.model and get_model(option.model) is None:
                problems.append(f"The mode {mode.id!r} runs {option.id!r} on {option.model!r}, which is no model.")
    for profile in app.interface.profiles:
        if profile.model and get_model(profile.model) is None:
            problems.append(f"The profile {profile.id!r} runs on {profile.model!r}, which is no model.")
    if app.decision is not None and app.decision.decision_model:
        decider = get_model(app.decision.decision_model)
        if decider is None:
            problems.append(f"There is no model named {app.decision.decision_model!r} to decide with.")
        elif "decisions" not in decider.capabilities:
            problems.append(f"The model {app.decision.decision_model!r} does not answer typed decisions.")
    # Its voice is one of the catalogue's, and speaks its language (VOICE.md VO-41).
    voice = app.interface.voice
    if voice.enabled and voice.output is not VoiceOutput.OFF and voice.voice:
        from ..speech import voice_problems

        problems.extend(voice_problems(voice.voice, voice.language))
    # Its outputs are formats the outputs catalogue gives.
    known = output_media_types()
    for output in app.interface.outputs:
        if output not in known:
            problems.append(
                f"Its output {output!r} is no format of the outputs catalogue: "
                f"{', '.join(sorted(known))}."
            )
    # The components it may use, and the ones its surface uses, are the catalog's (C-13).
    for name in app.interface.components:
        if component_named(name) is None:
            problems.append(f"There is no component named {name!r} in the catalog.")
    if app.interface.surface is not None:
        for node in app.interface.surface.components:
            if component_named(str(node["component"])) is None:
                problems.append(
                    f"The surface's {node['id']!r} is a {node['component']!r}, which the catalog does not have."
                )
            elif node["component"] == "Form":
                problems += form_problems(node)
        # A `chat` layout is the conversation alone: a page composed for it is not drawn.
        if (
            app.agent
            and app.kind is not AppKind.DECISION
            and app.layout is Layout.CHAT
            and app.interface.surface.components
        ):
            problems.append(
                "Its page is composed but its layout is chat, the conversation alone: "
                "choose page or split to show it."
            )
    run = {_id_of(guard) for guard in app.checks.guards}
    for ref in app.checks.gates:
        gate = _catalogue("gates").get(_id_of(ref))
        for guard in (gate or {}).get("guards") or []:
            if _id_of(guard) not in run:
                problems.append(
                    f"The Gate {ref!r} reads the Guard {guard!r}, which the application does not run: "
                    "add it under `checks.guards`."
                )
    host = app.deployment.embedded.host if app.deployment.embedded else None
    host_tools = host.tools if host else []
    for rule in app.rules:
        for tool in rule.tools:
            server, name = split_ref(tool)
            if server is None:
                if tool in host_tools or app.tool(tool) is not None:
                    continue
                if _id_of(name) not in _catalogue("backend-tools"):
                    problems.append(f"The rule {rule.action!r} names the tool {tool!r}, which the catalogue does not have.")
            elif app.connection(server) is None:
                problems.append(
                    f"The rule {rule.action!r} names {tool!r}, and the application is not connected to {server!r}."
                )
            elif not app.connection(server).reaches(name):  # type: ignore[union-attr]
                problems.append(
                    f"The rule {rule.action!r} names {tool!r}, which the connection to {server!r} leaves out (`only`)."
                )
    # What the host page offers is decided by a rule that names it (D-10).
    named = {tool for rule in app.rules for tool in rule.tools}
    for tool in host_tools:
        if tool not in named:
            problems.append(
                f"No rule names {tool!r}, which the host page offers it: "
                "it is left to the person until a rule decides it."
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
    included, since it says nothing its kind does not. Where the spec does
    not declare the keys — a scenario's weights, a component of a surface —
    they are written in alphabetical order, a component's `id` and what it
    is first. The same application always writes the same document, whatever
    order it was read in.
    """
    data = json.loads(app.model_dump_json(by_alias=True, exclude_defaults=True))
    # One target is written alone when it is a class of action, as a person would.
    for rule in data.get("rules") or []:
        targets = rule["applies_to"]
        if isinstance(targets, list) and len(targets) == 1 and targets[0] in _CLASS_NAMES:
            rule["applies_to"] = targets[0]
    interface = data.get("interface") or {}
    if interface.get("layout") == DEFAULT_LAYOUTS[app.kind].value:
        del interface["layout"]
        if not interface:
            del data["interface"]
    # What the spec does not declare the keys of is written in one order too.
    surface = interface.get("surface") or {}
    if "components" in surface:
        surface["components"] = [_component(component) for component in surface["components"]]
    for scenario in (data.get("decision") or {}).get("scenarios") or []:
        if "weights" in scenario:
            scenario["weights"] = _sorted(scenario["weights"])
    return {"schema": app.schema_, **{key: value for key, value in data.items() if key != "schema"}}


def _sorted(value: Any) -> Any:
    """A value with the keys of every mapping in it in alphabetical order."""
    if isinstance(value, dict):
        return {key: _sorted(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sorted(item) for item in value]
    return value


def _component(component: Mapping[str, Any]) -> Dict[str, Any]:
    """A component of a surface as it is written: its `id`, what it is, then the rest in alphabetical order."""
    rest = {key: value for key, value in component.items() if key not in ("id", "component")}
    return {"id": component.get("id"), "component": component.get("component"), **_sorted(rest)}


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
    "ASSISTANT_CHARACTER_ID",
    "DEFAULT_BEHAVIOURS",
    "DEFAULT_LAYOUTS",
    "DEFAULT_READY_AT",
    "KNOWN_SCHEMAS",
    "KeptRecord",
    "MAX_UPLOAD_MB",
    "MEDIA_TYPE",
    "SCHEMA_PATH",
    "TEXT_OUTPUTS",
    "TRACK_KEEPS",
    "UPLOAD_KIND",
    "Accent",
    "Access",
    "ActsAs",
    "AppChecks",
    "AppCodeCheck",
    "AppComputer",
    "AppConnection",
    "AppCriterion",
    "AppDecision",
    "AppDeployment",
    "AppError",
    "AppInterface",
    "AppKind",
    "AppCommand",
    "AppMode",
    "AppModeOption",
    "AppFieldTranslation",
    "AppModeTranslation",
    "AppOptionTranslation",
    "AppPermissions",
    "AppProfile",
    "AppProfileTranslation",
    "AppRecord",
    "AppRule",
    "AppScenario",
    "AppSpaceGrant",
    "AppSpec",
    "AppStarter",
    "AppStarterTranslation",
    "AppSurface",
    "AppTestCase",
    "AppTests",
    "AppTool",
    "AppTranslation",
    "AppTrigger",
    "AppVoice",
    "Behaviour",
    "CODE_NAME",
    "CheckStage",
    "CriterionKind",
    "AppTheme",
    "AppUploadKind",
    "AppUploads",
    "BalloonDisplay",
    "EmbedMode",
    "FORM_WIDGETS",
    "LANGUAGE_TAG",
    "SETTING_INPUTS",
    "EmbeddedDeployment",
    "HostedDeployment",
    "Layout",
    "RecordItem",
    "ThemeMode",
    "ThemeVariant",
    "TriggerType",
    "Visibility",
    "VoiceInput",
    "VoiceOutput",
    "VoiceWhere",
    "app_problems",
    "app_setup",
    "behaviour_for",
    "command_prompt",
    "dump_app",
    "form_problems",
    "form_ui_problems",
    "get_app",
    "kept_record",
    "json_schema",
    "list_apps",
    "load_app",
    "load_apps",
    "load_raw_apps",
    "output_media_types",
    "parse_app",
    "pick_language",
    "retention_days",
    "schema_text",
    "strictest",
    "tool_behaviours",
    "tool_escalations",
    "upload_kind_takes",
]
