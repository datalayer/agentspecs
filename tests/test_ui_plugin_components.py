# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The catalog of visual components a UI plugin renders (LOOP C-13).

One catalog for the spec, the Canvas and Python, hosted by the UI plugins:
A2UI's standard components by the names A2UI gives them, and Datalayer's own,
whose properties are a JSON Schema a properties form is drawn from
(`@datalayer/primer-rjsf`, C-14): valid, an object, each property titled and
described, and its example valid against it.
"""

from __future__ import annotations

import pathlib

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
    assert {"Table", "Chart", "Chat", "Evidence", "Form", "FileUpload"} <= set(components)


def test_a_component_says_what_it_is():
    for name, spec in _components().items():
        assert spec["name"] and spec["description"].strip() and spec["emoji"], name
        assert spec["category"] in CATEGORIES, name


def test_datalayers_own_have_properties_a_form_is_drawn_from():
    for name, spec in _components().items():
        if spec["standard"]:
            # A2UI's own properties are A2UI's: not copied here.
            assert "properties" not in spec, name
            continue
        schema = spec["properties"]
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema["type"] == "object", name
        for field_name, field in schema["properties"].items():
            assert field.get("title") and field.get("description"), f"{name}.{field_name}"
        assert set(schema.get("required", [])) <= set(schema["properties"]), name
        assert set(spec["bindings"]) == {"shows", "sends"}, name
        assert isinstance(spec["events"], list), name
        jsonschema.validate(spec["example"], schema)


def test_a_wrong_value_is_refused_by_the_schema():
    table = _components()["Table"]["properties"]
    for wrong in ({}, {"columns": []}, {"columns": ["a"], "page_size": 0}):
        try:
            jsonschema.validate(wrong, table)
        except jsonschema.ValidationError:
            continue
        raise AssertionError(f"{wrong} should be refused")
