# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Visual components (LOOP C-13): one catalog for the spec, the Canvas and Python.

Every component says what it is, and its properties are a JSON Schema that a
properties form is generated from (`@datalayer/primer-rjsf`, C-14): valid, an
object, each property titled and described, and its example valid against it.
"""

from __future__ import annotations

import pathlib

import jsonschema
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"

CATEGORIES = {"text", "input", "action", "data", "conversation", "media", "layout"}

#: The A2UI (v0.9) standard catalog's components a catalog component may render as.
A2UI_STANDARD = {
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
    "CheckBox",
    "TextField",
    "DateTimeInput",
    "ChoicePicker",
    "Slider",
}


def _components() -> dict[str, dict]:
    return {
        path.stem: yaml.safe_load(path.read_text())
        for path in sorted((ROOT / "components").glob("*.yaml"))
    }


def test_the_catalog_holds_the_palette():
    assert {
        "text",
        "input",
        "select",
        "slider",
        "button",
        "table",
        "chart",
        "file-upload",
        "chat",
        "evidence",
        "form",
    } <= set(_components())


def test_a_component_says_what_it_is():
    for stem, spec in _components().items():
        assert spec["id"] == stem
        assert str(spec["version"]).count(".") == 2
        assert spec["name"] and spec["description"].strip() and spec["emoji"]
        assert spec["category"] in CATEGORIES, stem
        assert set(spec["bindings"]) == {"shows", "sends"}, stem
        assert isinstance(spec["events"], list), stem
        # Rendered by A2UI's standard catalog, or by a contributed plugin (C-12).
        assert spec.get("a2ui") is None or spec["a2ui"] in A2UI_STANDARD, stem


def test_its_properties_are_a_schema_a_form_is_drawn_from():
    for stem, spec in _components().items():
        schema = spec["properties"]
        jsonschema.Draft202012Validator.check_schema(schema)
        assert schema["type"] == "object", stem
        for name, field in schema["properties"].items():
            assert field.get("title") and field.get("description"), (
                f"{stem}.{name}: a form shows its title and description"
            )
        assert set(schema.get("required", [])) <= set(schema["properties"]), stem
        jsonschema.validate(spec["example"], schema)


def test_a_wrong_value_is_refused_by_the_schema():
    table = _components()["table"]["properties"]
    for wrong in ({}, {"columns": []}, {"columns": ["a"], "page_size": 0}):
        try:
            jsonschema.validate(wrong, table)
        except jsonschema.ValidationError:
            continue
        raise AssertionError(f"{wrong} should be refused")
