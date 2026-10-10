# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The catalog of visual components a UI plugin renders (LOOP C-13).

One catalog for the spec, the Canvas and Python, hosted by the UI plugins:
A2UI's standard components by the names A2UI gives them, and Datalayer's own,
each with its version and its properties as a JSON Schema a properties form
is drawn from (`@datalayer/primer-rjsf`, C-14): valid, an object, each
property titled and described; a standard one's as A2UI's, Datalayer's own
with an example valid against it.
"""

from __future__ import annotations

import json
import pathlib
import re

import jsonschema
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"

CATEGORIES = {"text", "input", "action", "data", "conversation", "media", "layout"}

#: The A2UI v0.9 basic catalog.
A2UI_BASIC = {
    "Text",
    "Image",
    "Icon",
    "Video",
    "AudioPlayer",
    "Row",
    "Column",
    "List",
    "Card",
    "Tabs",
    "Divider",
    "Modal",
    "Button",
    "TextField",
    "CheckBox",
    "ChoicePicker",
    "Slider",
    "DateTimeInput",
}


def _components() -> dict[str, dict]:
    plugin = yaml.safe_load((ROOT / "ui-plugins" / "a2ui.yaml").read_text())
    assert plugin["catalog"] == "a2ui/v0.9"
    return {component["id"]: component for component in plugin["components"]}


def test_a2ui_hosts_its_basic_catalog_and_datalayers_own():
    components = _components()
    assert {name for name, c in components.items() if c["standard"]} == A2UI_BASIC
    assert {"Table", "Chart", "Chat", "Evidence", "Form", "FileUpload", "Download"} <= set(components)


def test_a_component_says_what_it_is():
    for name, spec in _components().items():
        assert spec["name"] and spec["description"].strip() and spec["emoji"], name
        assert spec["category"] in CATEGORIES, name


def test_every_component_has_a_version_and_properties_a_form_is_drawn_from():
    for name, spec in _components().items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", str(spec["version"])), name
        schema = spec["properties"]
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema["type"] == "object", name
        for field_name, field in schema["properties"].items():
            assert field.get("title") and field.get("description"), f"{name}.{field_name}"
        assert set(schema.get("required", [])) <= set(schema["properties"]), name
        if spec["standard"]:
            continue
        assert set(spec["bindings"]) == {"shows", "sends"}, name
        assert isinstance(spec["events"], list), name
        jsonschema.validate(spec["example"], schema)


def _a2ui_properties(component: dict) -> tuple[dict, list]:
    properties: dict = {}
    required: list = []
    for part in component.get("allOf", [component]):
        properties.update(part.get("properties", {}))
        required += part.get("required", [])
    properties.pop("component", None)
    return properties, [name for name in required if name != "component"]


def _a2ui_choices(prop: dict) -> list | None:
    if "enum" in prop:
        return prop["enum"]
    for option in prop.get("oneOf", []):
        if "enum" in option:
            return option["enum"]
    return None


def test_a_standard_components_properties_are_a2uis():
    """The catalog's own schema of a standard component names what A2UI's does —
    every property, the required ones, each choice and default — so that the
    form, the spec and Python cannot offer what the renderer does not draw."""
    basic = json.loads(
        (pathlib.Path(__file__).parent / "a2ui_v0_9" / "basic_catalog.json").read_text()
    )["components"]
    for name, spec in _components().items():
        if not spec["standard"]:
            continue
        theirs, required = _a2ui_properties(basic[name])
        ours = spec["properties"]
        assert set(ours["properties"]) == set(theirs), name
        assert sorted(ours.get("required", [])) == sorted(required), name
        for field_name, field in ours["properties"].items():
            assert field.get("enum") == _a2ui_choices(theirs[field_name]), f"{name}.{field_name}"
            assert field.get("default") == theirs[field_name].get("default"), f"{name}.{field_name}"


def test_a_wrong_value_is_refused_by_the_schema():
    table = _components()["Table"]["properties"]
    for wrong in ({}, {"columns": []}, {"columns": ["a"], "page_size": 0}):
        try:
            jsonschema.validate(wrong, table)
        except jsonschema.ValidationError:
            continue
        raise AssertionError(f"{wrong} should be refused")


def test_the_catalogue_page_says_every_component_and_is_the_one_in_the_docs():
    """The documentation's page of components is generated from the plugins
    (LOOP G-05): it names every component, and for Datalayer's own every
    property, binding and event; the page in the docs is the generated one."""
    from agentspecs.ui_plugins import CATALOGUE_PATH, catalogue_markdown

    page = catalogue_markdown()
    for name, spec in _components().items():
        assert f"`{name}`" in page, name
        assert f"### `{name}`" in page, name
        assert f"version {spec['version']}" in page, name
        for field_name in spec["properties"]["properties"]:
            assert f"| `{field_name}`" in page, f"{name}.{field_name}"
        if spec["standard"]:
            continue
        for field_name in spec["properties"]["properties"]:
            assert f"| `{field_name}`" in page, f"{name}.{field_name}"
        for value in [*spec["bindings"]["shows"], *spec["bindings"]["sends"], *spec["events"]]:
            assert f"`{value}`" in page, f"{name}: {value}"
    if CATALOGUE_PATH.exists():
        assert CATALOGUE_PATH.read_text() == page, "run `python -m agentspecs.ui_plugins`"
