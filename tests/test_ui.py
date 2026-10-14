# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""UI specs are Reactor plugins, UI renderers their own specs (AGENTIC_UI R8, F-01, F-02).

Every UI spec is one plugin of agent-runtimes, well formed, and names only
renderers of the ``ui-renderers`` catalogue; every renderer is well formed;
the old shape — a renderer listed as a UI — is refused wherever it is said,
with no compatibility reading. That each UI spec is its plugin's registration,
and each plugin of the Loop editor has one, is agent-runtimes' test
(``src/apps/__tests__/ui-specs.test.ts``): the registrations are there.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from pydantic import ValidationError

from agentspecs import ui, ui_renderers
from agentspecs.apps import AppSpec

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"


def _yaml(folder: str, name: str) -> dict:
    return yaml.safe_load((ROOT / folder / f"{name}.yaml").read_text())


def test_the_renderers_are_a2ui_mcp_apps_and_mcp_ui_and_nothing_else():
    catalogue = ui_renderers.UI_RENDERER_CATALOGUE
    assert set(catalogue) == {"a2ui", "mcp-apps", "mcp-ui"}
    assert {r for r, spec in catalogue.items() if spec.enabled} == {"a2ui"}
    for spec in catalogue.values():
        assert spec.name and spec.description.strip() and spec.docs_url.startswith("https://")


def test_a_renderer_is_not_a_ui():
    """The renderers moved to `ui-renderers` (F-01): none is left under `ui`, under its id or its shape."""
    for renderer in ui_renderers.UI_RENDERER_CATALOGUE:
        assert not (ROOT / "ui" / f"{renderer}.yaml").exists()
    for path in sorted((ROOT / "ui").glob("*.yaml")):
        assert "docs_url" not in (yaml.safe_load(path.read_text()) or {}), path.name


def test_a_ui_spec_is_a_reactor_plugin_named_for_its_file():
    catalogue = ui.UI_CATALOGUE
    assert {"chat", "notebook", "document", "a2ui-surface", "app-page", "app-rules", "pap-sign-in", "page-layout"} <= set(
        catalogue
    )
    folders = [spec.folder for spec in catalogue.values()]
    assert len(set(folders)) == len(folders)
    for spec in catalogue.values():
        assert spec.plugin.startswith("@datalayer/loop-plugin-"), spec.id
        assert spec.name and spec.description.strip() and spec.emoji, spec.id


def test_only_a2ui_surface_renders_the_catalog_of_components():
    with_components = {spec.id for spec in ui.UI_CATALOGUE.values() if spec.components}
    assert with_components == {"a2ui-surface"}
    assert ui.UI_CATALOGUE["a2ui-surface"].catalog == "a2ui/v0.9"


def test_the_schema_and_the_reference_are_the_specs():
    assert ui_renderers.SCHEMA_PATH.read_text() == ui_renderers.schema_text()
    if ui_renderers.REFERENCE_PATH.is_file():
        assert ui_renderers.REFERENCE_PATH.read_text() == ui_renderers.reference_text()


@pytest.mark.parametrize(
    "change,why",
    [
        ({"renderers": ["nope"]}, "no UI renderer 'nope'"),
        ({"renderers": ["a2ui", "a2ui"]}, "listed twice"),
        ({"id": "a2ui"}, "is a UI renderer, not a UI"),
        ({"plugin": "chat"}, "not the name of a Reactor plugin"),
        ({"settings": {"type": "string"}}, "JSON Schema of an object"),
        ({"enabled": True}, "Extra inputs"),
    ],
)
def test_a_ui_spec_refuses(change, why):
    good = _yaml("ui", "a2ui-surface")
    with pytest.raises(ValidationError, match=why):
        ui.UiSpec.model_validate({**good, **change})


def test_the_old_shape_of_a_ui_spec_is_refused():
    """A renderer written as a UI spec, as `ui/a2ui.yaml` was, is not read."""
    old = _yaml("ui-renderers", "a2ui")
    with pytest.raises(ValidationError, match="is a UI renderer, not a UI"):
        ui.UiSpec.model_validate(old)


@pytest.mark.parametrize(
    "change,why",
    [
        ({"id": "Not An Id"}, "not a UI renderer id"),
        ({"docs_url": "http://x.example"}, "https"),
        ({"components": []}, "Extra inputs"),
    ],
)
def test_a_renderer_refuses(change, why):
    good = _yaml("ui-renderers", "a2ui")
    with pytest.raises(ValidationError, match=why):
        ui_renderers.UiRendererSpec.model_validate({**good, **change})


def test_an_agent_names_ui_plugins_with_their_renderer():
    named = 0
    for path in sorted((ROOT / "agents").rglob("*.yaml")):
        spec = yaml.safe_load(path.read_text()) or {}
        if "ui" not in spec:
            continue
        named += 1
        assert ui.ui_choices_problems(spec["ui"], to_ship=False) == [], path.name
    assert named > 0


def test_the_old_names_are_gone():
    """`ui-plugins` is `ui` (AGENT_PROTOCOLS PS-03): no spec says the old field, no folder keeps the old name."""
    assert not (ROOT / "ui-plugins").exists()
    for path in sorted([*(ROOT / "agents").rglob("*.yaml"), *(ROOT / "cogs").rglob("*.yaml")]):
        spec = yaml.safe_load(path.read_text()) or {}
        assert "ui_plugin" not in spec, f"{path.name}: `ui_plugin` is now `ui`"


def test_an_application_names_its_ui_plugins_and_a_renderer_for_each():
    """The Appspec's `ui` (R8): UI plugins, each once, each with a renderer it may be exposed through."""
    base = {"id": "shop", "name": "Shop", "kind": "chat", "agent": "a"}
    chosen = [{"plugin": "a2ui-surface", "renderer": "a2ui"}, {"plugin": "chat"}]
    assert [c.model_dump(exclude_none=True) for c in AppSpec.model_validate({**base, "ui": chosen}).ui] == chosen
    for choices, why in (
        (["a2ui"], "it is a UI renderer"),
        ([{"plugin": "a2ui"}], "There is no UI plugin named 'a2ui'"),
        ([{"plugin": "nope"}], "There is no UI plugin named 'nope'"),
        ([{"plugin": "chat"}, {"plugin": "chat"}], "twice"),
        ([{"plugin": "chat", "renderer": "a2ui"}], "is not exposed through A2UI"),
        ([{"plugin": "a2ui-surface", "renderer": "nope"}], "There is no UI renderer named 'nope'"),
        ([{"plugin": "app-page", "renderer": "mcp-apps"}], "not enabled"),
    ):
        with pytest.raises(ValidationError, match=why):
            AppSpec.model_validate({**base, "ui": choices})
    off = {**base, "ui": [{"plugin": "app-page", "renderer": "mcp-apps"}], "enabled": False, "unavailable_because": "Later."}
    assert AppSpec.model_validate(off).ui[0].renderer == "mcp-apps"
