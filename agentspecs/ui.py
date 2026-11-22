# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The UI plugins, as specs (R8), and their components page.

The interface of an application is made of Reactor plugins: the chat, the
notebook and its toolbar, the page an application draws, its rules and
approvals… — those of agent-runtimes (``src/apps/plugins/``) the Agent editor
assembles. **A UI spec is one of them**, one YAML per plugin under ``ui/``,
named for the plugin's folder: the name the plugin registers under, its
Contributions (the Slots it fills, the Contribution Points it contributes to,
the Commands it adds), the Contribution Points it offers, the components it
renders, its settings, and the UI renderers (``ui-renderers/``,
:mod:`agentspecs.ui_renderers`) it may be exposed through.

A renderer is not a UI: a spec of the old shape — a renderer listed under
``ui`` — is refused, and so is a renderer a UI plugin names that the
``ui-renderers`` catalogue does not have.

An agent spec and an application name their UI plugins in ``ui``, each with
the renderer it is exposed through, when it is: :func:`ui_choices_problems`.

``python -m agentspecs.ui`` writes the components page: each plugin and the
components it renders, each with its version and its properties as a JSON
Schema — A2UI's standard ones as the catalog says what a builder sets of
them, Datalayer's own with their bindings, their events and an example.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .ui_renderers import UI_RENDERER_CATALOGUE

#: The UI specs of the catalogue.
PLUGINS_DIR = Path(__file__).resolve().parent / "ui"

#: Where the components page is kept in the documentation site, when the checkout has one.
CATALOGUE_PATH = Path(__file__).resolve().parents[1] / "docs" / "docs" / "agents" / "ui" / "components.md"

_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")


class UiInstances(str, Enum):
    """A plugin registered once per something, named ``<plugin>-<its id>``."""

    APPLICATION = "application"
    SOURCE = "source"
    UI = "ui"


class UiPlacement(str, Enum):
    """Where a UI goes in the chat (the user, 15 November 2026: "make sure ui can be used to be
    injected in the chat itself (toolbar, header...) or as chat message (a2ui)").

    The chat's own chrome — ``header`` (beside its title), ``toolbar`` (the input toolbar's
    controls), ``footer`` (under the prompt), ``banner`` (above the messages) — its two side
    panels, ``left`` and ``right`` (beside the conversation, closed until opened; the user,
    18 November 2026: "left and right side panels ... real panels that receive controls and
    visuals: an agent's UI plugins placed there") — or ``message``: a card in the conversation,
    drawn by a tool renderer or the A2UI renderer.
    """

    HEADER = "header"
    TOOLBAR = "toolbar"
    FOOTER = "footer"
    BANNER = "banner"
    LEFT = "left"
    RIGHT = "right"
    MESSAGE = "message"


#: The placements in the chat's own chrome, every one but `message`.
CHROME_PLACEMENTS = tuple(p.value for p in UiPlacement if p is not UiPlacement.MESSAGE)

#: The two side panels, beside the conversation.
SIDE_PLACEMENTS = (UiPlacement.LEFT.value, UiPlacement.RIGHT.value)


class UiContributions(BaseModel):
    """What a UI plugin contributes, as agent-runtimes registers it."""

    model_config = ConfigDict(extra="forbid")

    slots: List[str] = Field(default_factory=list, description="The Slots it fills")
    points: List[str] = Field(default_factory=list, description="The Contribution Points it contributes to")
    commands: List[str] = Field(
        default_factory=list,
        description="The Commands it adds: Reactor Commands by id, the composer's `/` commands by name",
    )


class UiImplementationKind(str, Enum):
    """What a UI spec's export is: the plugin, its instances, or what makes it."""

    #: A Reactor plugin.
    PLUGIN = "plugin"
    #: A list of Reactor plugins, one per instance (``per: source``, ``per: ui``).
    PLUGINS = "plugins"
    #: A function returning the plugin: called with the application for a plugin
    #: ``per: application``, with its placement for one whose first placement is in
    #: the chat's chrome or a side panel, and with nothing otherwise.
    FACTORY = "factory"


#: An npm package name: ``name`` or ``@scope/name``.
_NPM_PACKAGE = re.compile(r"^(@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*$")

#: A JavaScript export name.
_JS_EXPORT = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")

#: A Python entry point's object reference: ``module.path:attribute``.
#: Each side is dotted identifiers, none empty (``a..b`` and ``a.`` are refused).
_PY_DOTTED = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
_PY_ENTRY_POINT = re.compile(rf"^{_PY_DOTTED}:{_PY_DOTTED}$")


class UiBackendImplementation(BaseModel):
    """The backend (Python) Reactor plugin of a UI, when it has a server side."""

    model_config = ConfigDict(extra="forbid")

    package: str = Field(min_length=1, description="The PyPI distribution that ships it, e.g. `agent-runtimes`")
    entry_point: str = Field(
        description="Its entry point, as `module.path:attribute`, the object the reactor registers"
    )

    @field_validator("entry_point")
    @classmethod
    def _an_entry_point(cls, value: str) -> str:
        if not _PY_ENTRY_POINT.fullmatch(value):
            raise ValueError(f"{value!r} is not an entry point: `module.path:attribute`")
        return value


class UiImplementation(BaseModel):
    """Where a UI spec's Reactor plugin is: the package, the module and the export that are it.

    ``import { <export> } from '<package>/<module>'`` gives the plugin (``kind: plugin``), its
    instances (``plugins``) or what makes it (``factory``), whose manifest says what the spec
    says.
    """

    model_config = ConfigDict(extra="forbid")

    package: str = Field(description="The npm package that ships the plugin, e.g. `@datalayer/agent-runtimes`")
    module: str = Field(
        min_length=1,
        description="The module of the package that exports it, from the package's root (`lib/apps/plugins/chat`)",
    )
    export: str = Field(description="The name it is exported under, e.g. `ChatPlugin`")
    kind: UiImplementationKind = Field(
        default=UiImplementationKind.PLUGIN,
        description="What the export is: a plugin, a list of plugins, or a factory",
    )
    backend: Optional[UiBackendImplementation] = Field(
        default=None, description="Its backend (Python) Reactor plugin, when it has a server side"
    )

    @field_validator("package")
    @classmethod
    def _an_npm_package(cls, value: str) -> str:
        if not _NPM_PACKAGE.fullmatch(value):
            raise ValueError(f"{value!r} is not an npm package name")
        return value

    @field_validator("module")
    @classmethod
    def _a_module(cls, value: str) -> str:
        if value.startswith(("/", ".")) or value.endswith((".ts", ".tsx", ".js")) or "\\" in value:
            raise ValueError(f"{value!r} is not a module path from the package's root, without extension")
        return value

    @field_validator("export")
    @classmethod
    def _an_export(cls, value: str) -> str:
        if not _JS_EXPORT.fullmatch(value):
            raise ValueError(f"{value!r} is not a JavaScript export name")
        return value


#: How a header item is named: what its frontend tool's argument is called.
_ITEM_ID = re.compile(r"^[a-z][a-z0-9_]{0,30}$")

#: The items a header UI holds at most: the chat's title bar stays calm.
HEADER_ITEMS_AT_MOST = 3

#: The options a drop-down holds at most.
HEADER_OPTIONS_AT_MOST = 8


class UiHeaderItemKind(str, Enum):
    """What a header item is (the user, 18 November 2026: "a drop-down choice, or visual indicators").

    ``action``: a button that says something to the agent. ``choice``: a drop-down the person
    picks one option of, told to the agent with the next turn. ``indicator``: something the agent
    shows the person — a label, a counter, a status or a meter — set by the plugin's frontend tool.
    """

    ACTION = "action"
    CHOICE = "choice"
    INDICATOR = "indicator"


class UiHeaderDisplay(str, Enum):
    """How an indicator is drawn: words, a number with its words, a dot with its words, or a bar."""

    LABEL = "label"
    COUNTER = "counter"
    STATUS = "status"
    METER = "meter"


class UiHeaderTone(str, Enum):
    """What an indicator's colour says, in the theme's own tokens."""

    NEUTRAL = "neutral"
    ACCENT = "accent"
    SUCCESS = "success"
    ATTENTION = "attention"
    DANGER = "danger"


class UiHeaderOption(BaseModel):
    """One option of a header drop-down."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="What the page sends when it is chosen")
    label: str = Field(min_length=1, max_length=32, description="What the person reads")
    says: Optional[str] = Field(
        default=None,
        max_length=240,
        description="What the agent is told while it is chosen, in place of the item's `says`; empty for nothing",
    )

    @field_validator("id")
    @classmethod
    def _an_option_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,30}", value):
            raise ValueError(f"{value!r} is not an option id: letters, digits, `_`, `.` and `-`")
        return value


class UiHeaderItem(BaseModel):
    """One item of a header UI: a button, a drop-down or an indicator."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Its name: the argument of the plugin's frontend tool that sets it")
    kind: UiHeaderItemKind
    label: str = Field(min_length=1, max_length=32, description="Its name, as the person reads and hears it")
    description: str = Field(
        min_length=1, max_length=240, description="What it means: the person's tooltip, and what the model reads"
    )
    octicon: Optional[str] = Field(default=None, description="Its Octicon")
    # An action.
    message: Optional[str] = Field(
        default=None, max_length=400, description="An action's: what pressing it says to the agent, as the person"
    )
    # A choice.
    options: List[UiHeaderOption] = Field(default_factory=list, description="A choice's options, in order")
    default: Optional[str] = Field(default=None, description="A choice's option to start with; its first unsaid")
    says: Optional[str] = Field(
        default=None,
        max_length=240,
        description="A choice's: what the agent is told with every turn, `{label}` the option chosen",
    )
    # An indicator.
    display: Optional[UiHeaderDisplay] = Field(default=None, description="An indicator's: how it is drawn")
    unit: Optional[str] = Field(default=None, max_length=8, description="A meter's unit, after its value: `%`")
    max: Optional[float] = Field(default=None, gt=0, description="A meter's full value; 100 unsaid")

    @field_validator("id")
    @classmethod
    def _an_item_id(cls, value: str) -> str:
        if not _ITEM_ID.fullmatch(value):
            raise ValueError(f"{value!r} is not a header item id: lower-case letters, digits and `_`")
        return value

    @model_validator(mode="after")
    def _is_whole(self) -> "UiHeaderItem":
        kind = self.kind
        own = {
            UiHeaderItemKind.ACTION: {"message"},
            UiHeaderItemKind.CHOICE: {"options", "default", "says"},
            UiHeaderItemKind.INDICATOR: {"display", "unit", "max"},
        }
        for other, fields in own.items():
            if other is kind:
                continue
            for name in sorted(fields):
                if getattr(self, name):
                    raise ValueError(f"the {kind.value} {self.id!r} takes no `{name}`: it is {_a(other.value)}'s")
        if kind is UiHeaderItemKind.ACTION and not (self.message or "").strip():
            raise ValueError(f"the action {self.id!r} says nothing: give it a `message`")
        if kind is UiHeaderItemKind.CHOICE:
            if len(self.options) < 2:
                raise ValueError(f"the choice {self.id!r} needs two options at least")
            if len(self.options) > HEADER_OPTIONS_AT_MOST:
                raise ValueError(f"the choice {self.id!r} has more than {HEADER_OPTIONS_AT_MOST} options")
            ids = [option.id for option in self.options]
            if len(set(ids)) != len(ids):
                raise ValueError(f"the choice {self.id!r} lists an option twice")
            if self.default is not None and self.default not in ids:
                raise ValueError(f"the choice {self.id!r} starts with {self.default!r}, which is not one of its options")
            if self.says is None and any(option.says is None for option in self.options):
                raise ValueError(
                    f"the choice {self.id!r} tells the agent nothing: give it `says`, or each option its own"
                )
        if kind is UiHeaderItemKind.INDICATOR:
            if self.display is None:
                raise ValueError(f"the indicator {self.id!r} does not say how it is drawn: give it a `display`")
            if self.display is not UiHeaderDisplay.METER and (self.unit or self.max):
                raise ValueError(f"the indicator {self.id!r} is no meter: it takes no `unit` and no `max`")
        return self


def _a(kind: str) -> str:
    return f"an {kind}" if kind[0] in "aeiou" else f"a {kind}"


class UiHeader(BaseModel):
    """What a UI puts in the chat's title bar, and the frontend tool its agent sets it with."""

    model_config = ConfigDict(extra="forbid")

    tool: Optional[str] = Field(
        default=None,
        description=(
            "The frontend tool the agent sets its indicators and its drop-downs with, run in the page: "
            "`set_<the plugin's id>`; required as soon as it has an indicator"
        ),
    )
    when: Optional[str] = Field(
        default=None, max_length=400, description="When the agent calls the tool, as the model reads it"
    )
    items: List[UiHeaderItem] = Field(min_length=1, max_length=HEADER_ITEMS_AT_MOST)

    @model_validator(mode="after")
    def _is_whole(self) -> "UiHeader":
        ids = [item.id for item in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("a header item is listed twice")
        indicators = [item for item in self.items if item.kind is UiHeaderItemKind.INDICATOR]
        if indicators and not self.tool:
            raise ValueError("a header with an indicator names the frontend tool that sets it: `tool`")
        if self.tool and not self.settable():
            raise ValueError("a header of buttons alone takes no `tool`: nothing of it is set")
        if self.when and not self.tool:
            raise ValueError("`when` says when the tool is called: there is no `tool`")
        return self

    def settable(self) -> List[UiHeaderItem]:
        """The items the tool sets: the indicators and the drop-downs."""
        return [item for item in self.items if item.kind is not UiHeaderItemKind.ACTION]


def header_tool_name(ui_id: str) -> str:
    """The frontend tool of a header UI: ``set_<its id>``, hyphens as underscores."""
    return "set_" + ui_id.replace("-", "_")


def header_tool_parameters(header: UiHeader) -> Dict[str, Any]:
    """The arguments of a header's frontend tool, as a JSON Schema: one per item it sets.

    An indicator takes an object — ``label`` (its words), ``tone``, ``visible``, and ``value``
    for a counter or a meter (``max`` too for a meter); a drop-down takes one of its option ids.
    Only the items named change: the others stay as they are. Agent-runtimes builds the same
    schema in the page (``headerToolParameters``), held to this one by its tests.
    """
    properties: Dict[str, Any] = {}
    for item in header.settable():
        if item.kind is UiHeaderItemKind.CHOICE:
            properties[item.id] = {
                "type": "string",
                "enum": [option.id for option in item.options],
                "description": f"{item.label}: {item.description} Set it only when the person says so in the conversation.",
            }
            continue
        fields: Dict[str, Any] = {}
        if item.display in (UiHeaderDisplay.COUNTER, UiHeaderDisplay.METER):
            fields["value"] = {"type": "number", "description": "The number shown."}
        if item.display is UiHeaderDisplay.METER:
            fields["max"] = {"type": "number", "description": f"The full value; {_number(item.max or 100)} unsaid."}
        fields["label"] = {"type": "string", "maxLength": 48, "description": "Its words, a few."}
        fields["tone"] = {
            "type": "string",
            "enum": [tone.value for tone in UiHeaderTone],
            "description": "What its colour says; neutral unsaid.",
        }
        fields["visible"] = {"type": "boolean", "description": "false takes it off the title bar."}
        properties[item.id] = {
            "type": "object",
            "description": f"{item.label}: {item.description}",
            "properties": fields,
            "additionalProperties": False,
        }
    return {"type": "object", "properties": properties, "additionalProperties": False}


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def header_says(header: UiHeader, chosen: Mapping[str, Any]) -> List[str]:
    """What the agent is told of the options chosen in a header's drop-downs, a sentence each.

    ``chosen`` is what the page sends with a turn, an option id by item id. An option's own
    ``says`` wins over its item's, whose ``{label}`` is the option's; an empty one says nothing.

    Raises
    ------
    ValueError
        When an item is not a drop-down of this header, or an option is not one of its own.
    """
    choices = {item.id: item for item in header.items if item.kind is UiHeaderItemKind.CHOICE}
    said: List[str] = []
    for item_id, option_id in chosen.items():
        item = choices.get(str(item_id))
        if item is None:
            raise ValueError(f"The header has no drop-down {item_id!r}.")
        option = next((each for each in item.options if each.id == option_id), None)
        if option is None:
            raise ValueError(f"{item.label} has no option {option_id!r}.")
        words = option.says if option.says is not None else (item.says or "").replace("{label}", option.label)
        if words.strip():
            said.append(words.strip())
    return said


class UiSpec(BaseModel):
    """One UI plugin: a Reactor plugin of agent-runtimes a Maker composes an interface with."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Its id, the file's name and the plugin's folder in agent-runtimes")
    version: str = Field(description="The version of this spec")
    name: str = Field(min_length=1, description="Its name, as a Maker reads it")
    description: str = Field(min_length=1, description="What it is, in a Maker's words")
    emoji: str = Field(min_length=1, description="Its face")
    octicon: Optional[str] = Field(default=None, description="Its Octicon")
    plugin: str = Field(description="The name the Reactor plugin registers under")
    folder: str = Field(min_length=1, description="The plugin's folder in agent-runtimes, under `src/apps/plugins/`")
    implementation: UiImplementation = Field(
        description="Where its plugin is: the npm package, the module and the export, and its backend part if any"
    )
    per: Optional[UiInstances] = Field(
        default=None,
        description="Registered once per application, per source or per UI spec, as `<plugin>-<its id>`",
    )
    contributions: UiContributions = Field(default_factory=UiContributions)
    contribution_points: List[str] = Field(default_factory=list, description="The Contribution Points it offers")
    catalog: Optional[str] = Field(default=None, description="The catalog its components are written in")
    components: List[Dict[str, Any]] = Field(default_factory=list, description="The visual components it renders")
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Its settings, as the JSON Schema of an object; its defaults the plugin's"
    )
    renderers: List[str] = Field(
        default_factory=list, description="The UI renderers it may be exposed through, ids of `ui-renderers`"
    )
    placements: List[UiPlacement] = Field(
        default_factory=list,
        description=(
            "Where in the chat it may go, its default first (0.0.197): `header`, `toolbar`, "
            "`footer`, `banner`, the side panels `left` and `right`, or `message`; none for a part of the workspace itself"
        ),
    )
    header: Optional[UiHeader] = Field(
        default=None,
        description=(
            "What it puts in the chat's title bar — buttons, drop-downs and indicators — and the "
            "frontend tool its agent sets them with; for a UI whose first placement is `header`"
        ),
    )
    supersedes: List[str] = Field(
        default_factory=list,
        description="The UI plugins it stands in for: a chat that has it leaves them out",
    )

    @model_validator(mode="before")
    @classmethod
    def _not_a_renderer(cls, data: Any) -> Any:
        """The old shape — a renderer listed as a UI — is refused, not read."""
        if isinstance(data, Mapping) and "plugin" not in data and ("docs_url" in data or "enabled" in data):
            raise ValueError(
                f"{data.get('id')!r} is a UI renderer, not a UI: a UI spec is a Reactor plugin, "
                "and renderers are specs of `ui-renderers`"
            )
        return data

    @field_validator("id")
    @classmethod
    def _an_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError(f"{value!r} is not a UI id: lower-case letters, digits and hyphens")
        if value in UI_RENDERER_CATALOGUE:
            raise ValueError(f"{value!r} is a UI renderer, not a UI: it is a spec of `ui-renderers`")
        return value

    @field_validator("plugin")
    @classmethod
    def _a_plugin_name(cls, value: str) -> str:
        if not re.fullmatch(r"@[a-z0-9-]+/[a-z0-9-]+", value):
            raise ValueError(f"{value!r} is not the name of a Reactor plugin: `@scope/name`")
        return value

    @field_validator("renderers")
    @classmethod
    def _renderers_exist(cls, values: List[str]) -> List[str]:
        for renderer in values:
            if renderer not in UI_RENDERER_CATALOGUE:
                raise ValueError(
                    f"there is no UI renderer {renderer!r}: one of {', '.join(sorted(UI_RENDERER_CATALOGUE))}"
                )
        if len(set(values)) != len(values):
            raise ValueError("a UI renderer is listed twice")
        return values

    @field_validator("settings")
    @classmethod
    def _settings_are_an_object(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if value and (value.get("type") != "object" or not isinstance(value.get("properties"), Mapping)):
            raise ValueError("its settings are the JSON Schema of an object, with properties")
        return value

    @model_validator(mode="after")
    def _a_header_goes_in_the_header(self) -> "UiSpec":
        if self.header is not None:
            if not self.placements or self.placements[0] is not UiPlacement.HEADER:
                raise ValueError(f"{self.id!r} declares a `header`: its first placement is `header`")
            expected = header_tool_name(self.id)
            if self.header.tool is not None and self.header.tool != expected:
                raise ValueError(f"the frontend tool of {self.id!r} is named {expected!r}, not {self.header.tool!r}")
        if self.id in self.supersedes:
            raise ValueError(f"{self.id!r} supersedes itself")
        if len(set(self.supersedes)) != len(self.supersedes):
            raise ValueError(f"{self.id!r} supersedes a UI twice")
        return self

    @model_validator(mode="after")
    def _a_factory_for_instances(self) -> "UiSpec":
        kind = self.implementation.kind
        if self.per is UiInstances.APPLICATION and kind is not UiImplementationKind.FACTORY:
            raise ValueError(f"{self.id!r} is registered per application: its export is a factory")
        if self.per in (UiInstances.SOURCE, UiInstances.UI) and kind is not UiImplementationKind.PLUGINS:
            raise ValueError(f"{self.id!r} is registered per {self.per.value}: its export is a list of plugins")
        return self

    @model_validator(mode="after")
    def _components_have_a_catalog(self) -> "UiSpec":
        if self.components and not self.catalog:
            raise ValueError(f"{self.id!r} renders components: say the catalog they are written in")
        return self


class UiChoice(BaseModel):
    """A UI plugin an agent or an application names, and the renderer it is exposed through, when it is."""

    model_config = ConfigDict(extra="forbid")

    plugin: str = Field(min_length=1, description="A UI plugin of `agentspecs/ui`, by id")
    renderer: Optional[str] = Field(
        default=None, description="The UI renderer of `agentspecs/ui-renderers` it is exposed through, by id"
    )
    placement: Optional[UiPlacement] = Field(
        default=None, description="Where in the chat it goes, one of its spec's `placements`; its default unsaid"
    )

    @model_validator(mode="before")
    @classmethod
    def _not_a_bare_id(cls, data: Any) -> Any:
        """The old shape — a renderer's id under `ui` — is refused, not read."""
        if isinstance(data, str):
            hint = (
                " it is a UI renderer: name the plugin it renders, and say it as its `renderer`"
                if data in UI_RENDERER_CATALOGUE
                else ""
            )
            raise ValueError(f"`ui` lists UI plugins, each as `{{plugin, renderer}}`, not {data!r}:{hint or ' a bare id'}")
        return data


#: Where the frontend tool sets are (agentspecs/frontend-tools).
FRONTEND_TOOLS_DIR = Path(__file__).resolve().parent / "frontend-tools"


def hands_frontend_tools(ui_id: str) -> bool:
    """Whether a UI hands the chat's agent a set of frontend tools: the set of its own id.

    A page UI (``page-deck``, ``page-sheet``) is the plugin that binds a frontend tool set
    (``frontend-tools/<id>.yaml``) to what it keeps in the page for the conversation, and draws
    its calls. An agent names the two together: the set under ``frontend_tools``, the UI under ``ui``.
    """
    return bool(_ID.match(ui_id)) and (FRONTEND_TOOLS_DIR / f"{ui_id}.yaml").is_file()


def load_ui(directory: Path = PLUGINS_DIR) -> Dict[str, UiSpec]:
    """Every UI spec of a directory, validated, by id; each file named for its id, each plugin once."""
    found: Dict[str, UiSpec] = {}
    plugins: Dict[str, str] = {}
    for path in sorted(directory.glob("*.yaml")):
        spec = UiSpec.model_validate(yaml.safe_load(path.read_text()) or {})
        if spec.id != path.stem:
            raise ValueError(f"{path.name}: the file is named for {path.stem!r}, the spec says {spec.id!r}")
        if spec.plugin in plugins:
            raise ValueError(f"{path.name}: the plugin {spec.plugin!r} is already {plugins[spec.plugin]!r}'s")
        plugins[spec.plugin] = spec.id
        found[spec.id] = spec
    tools: Dict[str, str] = {}
    for spec in found.values():
        for other in spec.supersedes:
            if other not in found:
                raise ValueError(f"{spec.id}.yaml: it supersedes {other!r}, which is no UI spec")
        if spec.header is not None and spec.header.tool:
            if spec.header.tool in tools:
                raise ValueError(f"{spec.id}.yaml: the tool {spec.header.tool!r} is already {tools[spec.header.tool]!r}'s")
            tools[spec.header.tool] = spec.id
    return found


#: Every UI spec of the catalogue, by id.
UI_CATALOGUE: Dict[str, UiSpec] = load_ui()


def get_ui(ui_id: str) -> Optional[UiSpec]:
    """A UI spec by id, or None."""
    return UI_CATALOGUE.get(ui_id)


def ui_choices_problems(choices: Sequence[Any], *, to_ship: bool) -> List[str]:
    """What is wrong with the UI plugins an agent or an application names, in sentences.

    Each choice is ``{plugin, renderer}``: a UI plugin of the catalogue, once,
    and the renderer it is exposed through when it is one — one of those the
    plugin may be exposed through, and an enabled one for an application that
    is offered. A bare id (the old shape, a renderer named as a UI) is refused.
    """
    problems: List[str] = []
    seen: List[str] = []
    for choice in choices:
        if not isinstance(choice, Mapping):
            problems.append(
                f"`ui` lists UI plugins, each as `{{plugin, renderer}}`: {choice!r} is not one"
                + (
                    f" ({choice!r} is a UI renderer: name the plugin it renders, and say it as its `renderer`)."
                    if isinstance(choice, str) and choice in UI_RENDERER_CATALOGUE
                    else "."
                )
            )
            continue
        plugin_id = str(choice.get("plugin") or "")
        renderer_id = choice.get("renderer")
        if plugin_id in seen:
            problems.append(f"It lists the UI plugin {plugin_id!r} twice.")
            continue
        seen.append(plugin_id)
        spec = get_ui(plugin_id)
        if spec is None:
            problems.append(
                f"There is no UI plugin named {plugin_id!r}: one of {', '.join(sorted(UI_CATALOGUE))}."
                + (
                    f" {plugin_id!r} is a UI renderer: say it as a plugin's `renderer`."
                    if plugin_id in UI_RENDERER_CATALOGUE
                    else ""
                )
            )
            continue
        placement = choice.get("placement")
        # A parsed choice holds the enum: its value is the placement's name.
        if isinstance(placement, Enum):
            placement = placement.value
        if placement is not None:
            allowed = [p.value for p in spec.placements]
            if not allowed:
                problems.append(f"The UI plugin {spec.name} ({plugin_id!r}) has no place in the chat: it takes no `placement`.")
            elif str(placement) not in allowed:
                problems.append(
                    f"The UI plugin {spec.name} ({plugin_id!r}) does not go in the chat's {placement}: "
                    f"in its {', '.join(allowed)} only."
                )
        if renderer_id is None:
            continue
        renderer = UI_RENDERER_CATALOGUE.get(str(renderer_id))
        if renderer is None:
            problems.append(
                f"There is no UI renderer named {renderer_id!r}: one of {', '.join(sorted(UI_RENDERER_CATALOGUE))}."
            )
        elif renderer.id not in spec.renderers:
            problems.append(
                f"The UI plugin {spec.name} ({plugin_id!r}) is not exposed through {renderer.name}: "
                + (f"through {', '.join(spec.renderers)} only." if spec.renderers else "through no renderer.")
            )
        elif to_ship and not renderer.enabled:
            problems.append(
                f"The UI renderer {renderer.name} ({renderer.id!r}) is not enabled: an application cannot be exposed through it yet."
            )
    return problems


def brought_ui_problems(spec: Mapping[str, Any], what: str) -> List[str]:
    """What is wrong with the UI plugins an MCP server, a skill or a backend tool brings, in sentences.

    Such a spec says ``ui`` as an agent does (agentspecs 0.0.196): a list of
    ``{plugin, renderer}``, each a UI plugin of ``ui/``, each once, the renderer
    one it may be exposed through. The chat that uses it injects them after the
    agent's own. No ``ui``, nothing wrong.
    """
    choices = spec.get("ui")
    if choices is None:
        return []
    name = f"{what} {spec.get('id', '?')!r}"
    if not isinstance(choices, list):
        return [f"{name}: `ui` is a list of UI plugins, each as `{{plugin, renderer}}`."]
    return [f"{name}: {problem}" for problem in ui_choices_problems(choices, to_ship=False)]


def plugins() -> List[Dict[str, Any]]:
    """The UI specs, as their files say, by id."""
    found = [yaml.safe_load(path.read_text()) or {} for path in sorted(PLUGINS_DIR.glob("*.yaml"))]
    return sorted(found, key=lambda plugin: str(plugin.get("id")))


def _cell(text: Any) -> str:
    """Text for a table cell, safe in MDX."""
    words = " ".join(str(text if text is not None else "").split())
    return words.replace("|", "\\|").replace("<", "&lt;").replace("{", "\\{").replace("}", "\\}")


def _type(prop: Mapping[str, Any]) -> str:
    if "enum" in prop:
        return " | ".join(f"`{value}`" for value in prop["enum"])
    kind = prop.get("type", "any")
    words = {"string": "text", "integer": "integer", "number": "number", "boolean": "true or false", "object": "mapping"}
    text = f"list of {_type(prop.get('items') or {})}" if kind == "array" else words.get(str(kind), str(kind))
    bounds = [f"{key} {prop[key]}" for key in ("minimum", "maximum", "minItems", "maxItems") if key in prop]
    return f"{text} ({', '.join(bounds)})" if bounds else text


def _default(prop: Mapping[str, Any]) -> str:
    if "default" not in prop:
        return "—"
    return f"`{json.dumps(prop['default'], ensure_ascii=False)}`"


def _names(values: List[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "nothing"


def _component(component: Mapping[str, Any]) -> List[str]:
    schema: Mapping[str, Any] = component.get("properties") or {}
    required = list(schema.get("required") or [])
    bindings: Mapping[str, Any] = component.get("bindings") or {}
    lines = [
        f"### `{component['id']}`",
        "",
        f"{component.get('emoji', '')} **{_cell(component['name'])}** · {_cell(component['category'])} · "
        f"version {_cell(component['version'])} — {_cell(component['description'])}",
        "",
        "| Property | Type | Meaning | Default |",
        "| --- | --- | --- | --- |",
    ]
    for name, prop in (schema.get("properties") or {}).items():
        field = f"`{name}`" + (" (required)" if name in required else "")
        title = prop.get("title", "")
        meaning = f"**{_cell(title)}**. {_cell(prop.get('description', ''))}" if title else _cell(prop.get("description"))
        lines.append(f"| {field} | {_cell(_type(prop))} | {meaning} | {_cell(_default(prop))} |")
    lines.append("")
    if not component.get("standard"):
        lines += [
            f"- **Shows**: {_names(list(bindings.get('shows') or []))}.",
            f"- **Sends**: {_names(list(bindings.get('sends') or []))}.",
            f"- **Events**: {_names(list(component.get('events') or []))}.",
            "",
        ]
    lines += [
        "Its properties, as a JSON Schema:",
        "",
        "```json",
        json.dumps(schema, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    if component.get("example") is not None:
        lines += [
            "An example, valid against it:",
            "",
            "```yaml",
            yaml.safe_dump(component["example"], sort_keys=False, allow_unicode=True).rstrip(),
            "```",
            "",
        ]
    return lines


def catalogue_markdown() -> str:
    """The page of the catalog of visual components, as Markdown."""
    every = plugins()
    lines: List[str] = [
        "---",
        "sidebar_position: 2",
        "title: Components",
        "---",
        "",
        "<!-- Generated by `python -m agentspecs.ui` from ui/*.yaml. Do not edit. -->",
        "",
        "# The catalog of visual components",
        "",
        "Every UI plugin, and the visual components each renders, by the name a surface gives them. "
        "A component no UI plugin renders is not in the catalog: an Appspec that names one is refused "
        "(see [UI](./index.mdx)).",
        "",
        "| UI plugin | Registered as | Renderers | Catalog | Components |",
        "| --- | --- | --- | --- | --- |",
    ]
    for plugin in every:
        count = len(plugin.get("components") or [])
        per = f" (one per {plugin['per']})" if plugin.get("per") else ""
        renderers = ", ".join(f"`{each}`" for each in plugin.get("renderers") or []) or "—"
        lines.append(
            f"| `{plugin['id']}` ({_cell(plugin['name'])}) | `{plugin['plugin']}`{per} | {renderers} | "
            f"{_cell(plugin.get('catalog') or '—')} | {count or 'none of its own'} |"
        )
    lines.append("")
    for plugin in every:
        components = list(plugin.get("components") or [])
        if not components:
            continue
        standard = [c for c in components if c.get("standard")]
        own = [c for c in components if not c.get("standard")]
        lines += [
            f"## {_cell(plugin['name'])} (`{plugin['id']}`)",
            "",
            _cell(plugin.get("description")),
            "",
            f"Catalog `{plugin.get('catalog')}`: {len(standard)} standard components, named and drawn as the "
            f"protocol says ([A2UI](https://a2ui.org/)), and {len(own)} of Datalayer's own. "
            "Every one has a version and its properties as a JSON Schema of the catalog's: what a builder sets, "
            "the Canvas draws a properties form from, and Python calls typed.",
            "",
            "| Id | Name | Category | Version | Standard | What it is for |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for component in components:
            anchor = f"[`{component['id']}`](#{component['id'].lower()})"
            lines.append(
                f"| {anchor} | {component.get('emoji', '')} {_cell(component['name'])} | {_cell(component['category'])} | "
                f"{_cell(component['version'])} | {'yes' if component.get('standard') else 'no'} | "
                f"{_cell(component['description'])} |"
            )
        lines.append("")
        for title, group in (("standard components", standard), ("Datalayer's own components", own)):
            if group:
                lines += [f"## {_cell(plugin['name'])}: {title}", ""]
                for component in group:
                    lines += _component(component)
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    if CATALOGUE_PATH.parent.is_dir():
        CATALOGUE_PATH.write_text(catalogue_markdown())
        print(f"wrote {CATALOGUE_PATH}")
