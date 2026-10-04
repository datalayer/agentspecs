# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Every application's surface is valid A2UI v0.9 (LOOP R-01, C-04).

Each block of a catalogue application's surface that is one of A2UI's basic
components is validated against the shape A2UI v0.9 gives it — the basic
catalog and its common types, as `@a2ui/web_core` ships them, kept beside
this test — so that a ChoicePicker's options are `{label, value}`, a Slider
has its `max`, a Button its `action`. A block that writes under `/inputs`
writes one of the application's settings, the paths a page takes them at.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator
from typing import Any

import jsonschema
import pytest
from referencing import Registry, Resource

from agentspecs.apps import APP_CATALOGUE as APPS
from agentspecs.apps import AppSpec

SCHEMAS = pathlib.Path(__file__).resolve().parent / "a2ui_v0_9"

_COMMON = json.loads((SCHEMAS / "common_types.json").read_text())
_BASIC = json.loads((SCHEMAS / "basic_catalog.json").read_text())
_REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in (_COMMON, _BASIC)
)

_WITH_SURFACE = sorted(app_id for app_id, app in APPS.items() if app.interface.surface is not None)


def _validator(component: str) -> jsonschema.Draft202012Validator:
    schema = {"$ref": f"{_BASIC['$id']}#/components/{component}"}
    return jsonschema.Draft202012Validator(schema, registry=_REGISTRY)


def _paths(value: Any) -> Iterator[str]:
    """Every `{path}` a block binds, at any depth."""
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and set(value) <= {"path"}:
            yield value["path"]
        for item in value.values():
            yield from _paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from _paths(item)


def test_the_vendored_catalog_is_a2ui_v0_9():
    assert _BASIC["$id"].endswith("/v0_9/catalogs/basic/catalog.json")
    assert {"ChoicePicker", "Slider", "Button", "Text"} <= set(_BASIC["components"])


def test_some_application_has_a_surface():
    assert _WITH_SURFACE


@pytest.mark.parametrize("app_id", _WITH_SURFACE)
def test_a_surface_s_basic_components_are_valid_a2ui_v0_9(app_id: str):
    app: AppSpec = APPS[app_id]
    assert app.interface.surface is not None
    assert app.interface.surface.protocol == "a2ui/v0.9"
    problems = []
    for node in app.interface.surface.components:
        if node["component"] not in _BASIC["components"]:
            continue
        for error in _validator(node["component"]).iter_errors(node):
            problems.append(f"{node['id']} ({node['component']}): {error.message}")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("app_id", _WITH_SURFACE)
def test_a_surface_writes_its_inputs_where_its_settings_are(app_id: str):
    app = APPS[app_id]
    assert app.interface.surface is not None
    settings = {f"/inputs/{setting.id}" for setting in app.interface.settings}
    for node in app.interface.surface.components:
        for path in _paths(node):
            if path.startswith("/inputs"):
                assert path in settings, f"{node['id']} binds {path}, which is not a setting"


def test_plain_string_options_are_refused():
    """What the Quote Calculator once had: options as plain strings."""
    node = {
        "id": "plan",
        "component": "ChoicePicker",
        "value": {"path": "/inputs/plan"},
        "options": ["Team"],
    }
    assert list(_validator("ChoicePicker").iter_errors(node))
    node["options"] = [{"label": "Team", "value": "Team"}]
    assert not list(_validator("ChoicePicker").iter_errors(node))
