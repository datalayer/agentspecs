# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The UI plugins, as specs (AGENTIC_UI R8, F-02), and their components page.

The interface of an application is made of Reactor plugins: the chat, the
notebook and its toolbar, the page an application draws, its rules and
approvals… — those of agent-runtimes (``src/apps/plugins/``) the Loop editor
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


class UiContributions(BaseModel):
    """What a UI plugin contributes, as agent-runtimes registers it."""

    model_config = ConfigDict(extra="forbid")

    slots: List[str] = Field(default_factory=list, description="The Slots it fills")
    points: List[str] = Field(default_factory=list, description="The Contribution Points it contributes to")
    commands: List[str] = Field(
        default_factory=list,
        description="The Commands it adds: Reactor Commands by id, the composer's `/` commands by name",
    )


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
