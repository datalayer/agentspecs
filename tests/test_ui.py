# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""UI specs are Reactor plugins, UI renderers their own specs (R8).

Every UI spec is one plugin of agent-runtimes, well formed, and names only
renderers of the ``ui-renderers`` catalogue; every renderer is well formed;
the old shape — a renderer listed as a UI — is refused wherever it is said,
with no compatibility reading. That each UI spec is its plugin's registration,
and each plugin of the Agent editor has one, is agent-runtimes' test
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
    """The renderers moved to `ui-renderers`: none is left under `ui`, under its id or its shape."""
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
        assert spec.plugin.startswith("@datalayer/agent-plugin-"), spec.id
        assert spec.name and spec.description.strip() and spec.emoji, spec.id


def test_a_ui_spec_says_where_its_plugin_is():
    """Each spec names its implementation: the package, a module under the plugin's folder, the export.

    A plugin registered per instance is exported as what makes it: a factory per
    application, a list per source or UI spec.
    """
    for spec in ui.UI_CATALOGUE.values():
        implementation = spec.implementation
        assert implementation.package == "@datalayer/agent-runtimes", spec.id
        assert implementation.module == f"lib/apps/plugins/{spec.folder}", spec.id
        assert implementation.export, spec.id
        assert implementation.backend is None, spec.id
    assert ui.UI_CATALOGUE["chat"].implementation.export == "ChatPlugin"
    assert ui.UI_CATALOGUE["app-page"].implementation.kind is ui.UiImplementationKind.FACTORY
    assert ui.UI_CATALOGUE["canvas-parts"].implementation.kind is ui.UiImplementationKind.PLUGINS


def test_a_ui_spec_may_name_its_backend_plugin():
    good = _yaml("ui", "a2ui-surface")
    spec = ui.UiSpec.model_validate(
        {
            **good,
            "implementation": {
                **good["implementation"],
                "backend": {"package": "agent-runtimes", "entry_point": "agent_runtimes.reactor_extension:plugin"},
            },
        }
    )
    assert spec.implementation.backend.entry_point == "agent_runtimes.reactor_extension:plugin"


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
        ({"implementation": {"package": "Not A Package", "module": "lib/x", "export": "X"}}, "not an npm package"),
        ({"implementation": {"package": "@a/b", "module": "./lib/x", "export": "X"}}, "not a module path"),
        ({"implementation": {"package": "@a/b", "module": "lib/x.ts", "export": "X"}}, "not a module path"),
        ({"implementation": {"package": "@a/b", "module": "lib/x", "export": "not-a-name"}}, "not a JavaScript export"),
        (
            {
                "implementation": {
                    "package": "@a/b",
                    "module": "lib/x",
                    "export": "X",
                    "backend": {"package": "b", "entry_point": "no colon"},
                }
            },
            "not an entry point",
        ),
        (
            {
                "implementation": {
                    "package": "@a/b",
                    "module": "lib/x",
                    "export": "X",
                    "backend": {"package": "b", "entry_point": "agent_runtimes..reactor_extension:plugin"},
                }
            },
            "not an entry point",
        ),
        (
            {
                "implementation": {
                    "package": "@a/b",
                    "module": "lib/x",
                    "export": "X",
                    "backend": {"package": "b", "entry_point": "agent_runtimes.reactor_extension:plugin."},
                }
            },
            "not an entry point",
        ),
        (
            {
                "implementation": {
                    "package": "@a/b",
                    "module": "lib/x",
                    "export": "X",
                    "backend": {"package": "b", "entry_point": ".a:b"},
                }
            },
            "not an entry point",
        ),
        (
            {
                "implementation": {
                    "package": "@a/b",
                    "module": "lib/x",
                    "export": "X",
                    "backend": {"package": "b", "entry_point": "a:.b"},
                }
            },
            "not an entry point",
        ),
        ({"per": "application"}, "its export is a factory"),
        ({"per": "source"}, "its export is a list of plugins"),
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
    """`ui-plugins` is `ui`: no spec says the old field, no folder keeps the old name."""
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


def test_every_application_of_the_catalogue_names_ui_plugins_its_renderers_allow():
    """Each catalogue application lists its UI plugins (R8): each a plugin of `ui`, each renderer one it allows.

    The loader refuses any other (`AppSpec`'s check runs `ui_choices_problems`); this reads the files as written.
    """
    for path in sorted((ROOT / "apps").glob("*.yaml")):
        spec = yaml.safe_load(path.read_text()) or {}
        assert spec.get("ui"), f"{path.name} lists no UI plugin"
        assert ui.ui_choices_problems(spec["ui"], to_ship=spec.get("enabled", True)) == [], path.name
        for choice in spec["ui"]:
            plugin = ui.get_ui(choice["plugin"])
            assert plugin is not None, path.name
            if "renderer" in choice:
                assert choice["renderer"] in plugin.renderers, path.name


def test_an_application_of_the_catalogue_lists_the_ui_plugins_it_is_drawn_with():
    """What each catalogue application lists in `ui` is what its kind, layout, outputs, PAP and components mount.

    The mapping is `ui_of` (`ui_for` on the spec's facts): agent-runtimes' `uiFor` is held to the same
    cases (`agent_runtimes/tests/fixtures/app_ui.json`), and seeds a new blank application with it.
    """
    from agentspecs.apps import load_apps, ui_of

    apps = load_apps()
    assert apps
    for identity, app in apps.items():
        # A header UI is the application's own addition (its agent's title bar), not its kind's;
        # so is a page UI, which hands its agent a set of frontend tools (a deck, a sheet in the page),
        # and the Composer's button, which a demo adds to show how it is built (21 November 2026).
        drawn = [
            c.model_dump(exclude_none=True)
            for c in app.ui
            if ui.UI_CATALOGUE[c.plugin].header is None
            and not ui.hands_frontend_tools(c.plugin)
            and c.plugin != "composer-portal"
        ]
        assert drawn == ui_of(app), identity


@pytest.mark.parametrize("folder,what", [("mcp-servers", "MCP server"), ("skills", "Skill"), ("backend-tools", "Backend tool")])
def test_a_server_a_skill_and_a_tool_bring_ui_plugins_of_the_catalogue(folder, what):
    """An MCP server, a skill and a backend tool say `ui` as an agent does (0.0.196): each a UI plugin of `ui/`, once."""
    for path in sorted((ROOT / folder).glob("*.yaml")):
        spec = yaml.safe_load(path.read_text()) or {}
        assert ui.brought_ui_problems(spec, what) == [], path.name


def test_the_seed_agents_capabilities_bring_their_ui():
    """The UI belongs to the capability: Shopify brings the basket, Odoo the reconciliation, Stripe its checkout."""
    def brought(folder, spec_id):
        spec = _yaml(folder, spec_id)
        return [choice["plugin"] for choice in spec.get("ui", [])]

    assert brought("mcp-servers", "shopify") == ["product-comparison", "shopping-basket"]
    assert "bank-reconciliation" in brought("mcp-servers", "odoo-accounting")
    assert brought("mcp-servers", "earthdata") == ["earth-scenes", "earth-index", "earth-area"]
    assert brought("mcp-servers", "linkedin") == ["browser-session"]
    assert "trip-options" in brought("skills", "fare-and-stay-comparison")
    assert brought("backend-tools", "list-recommendations") == ["aws-savings", "aws-savings-badge"]
    assert brought("backend-tools", "social-post-x") == ["x-post-preview"]
    assert _yaml("mcp-servers", "stripe")["ui"] == [{"plugin": "stripe-checkout", "renderer": "a2ui"}]


@pytest.mark.parametrize(
    "choices,why",
    [
        ([{"plugin": "nope"}], "There is no UI plugin named 'nope'"),
        (["stripe-checkout"], "each as `{plugin, renderer}`"),
        ([{"plugin": "trip-options"}, {"plugin": "trip-options"}], "twice"),
        ([{"plugin": "trial-balance", "renderer": "a2ui"}], "not exposed through A2UI"),
        ({"plugin": "trip-options"}, "is a list"),
    ],
)
def test_a_brought_ui_is_refused_when_wrong(choices, why):
    problems = ui.brought_ui_problems({"id": "x", "ui": choices}, "MCP server")
    assert problems and why in problems[0], problems
    with pytest.raises(ValueError, match="MCP server 'x'"):
        from agentspecs.mcp_servers import check_mcp_servers

        tmp = ROOT.parent / ".pytest-brought-ui"
        tmp.mkdir(exist_ok=True)
        try:
            (tmp / "x.yaml").write_text(yaml.safe_dump({"id": "x", "version": "0.0.1", "ui": choices}))
            check_mcp_servers(tmp)
        finally:
            for leftover in tmp.glob("*"):
                leftover.unlink()
            tmp.rmdir()


def test_a_ui_says_where_it_goes_in_the_chat():
    """A placement (0.0.197): the chat's chrome or a message; a choice picks one its spec allows."""
    assert ui.UI_CATALOGUE["x-budget"].placements[0].value == "header"
    assert ui.UI_CATALOGUE["linkedin-link"].placements[0].value == "banner"
    assert ui.UI_CATALOGUE["browser-session"].placements[0].value == "header"
    assert ui.UI_CATALOGUE["shopping-basket"].placements[0].value == "message"
    assert ui.ui_choices_problems([{"plugin": "x-budget", "placement": "footer"}], to_ship=False) == []
    assert "in its header, footer only" in ui.ui_choices_problems(
        [{"plugin": "x-budget", "placement": "message"}], to_ship=False
    )[0]
    assert "takes no `placement`" in ui.ui_choices_problems([{"plugin": "chat", "placement": "header"}], to_ship=False)[0]
    with pytest.raises(ValidationError):
        ui.UiChoice.model_validate({"plugin": "x-budget", "placement": "sidebar"})


#: The seed agents that bring cards to the chat. The seventh, the Data Analyst
#: (18 November 2026), brings none yet: what it does lands in the notebook's cells.
SEED_AGENTS = ["worker-marketer", "worker-shopper", "worker-accountant", "worker-traveller", "worker-terra", "worker-steward-aws"]


def _brought(agent_id):
    """The UI an agent's chat collects: its own, its servers', its skills', its tools' (as agent-runtimes does)."""
    agent = _yaml("agents", agent_id)
    choices = list(agent.get("ui") or [])
    for folder, key in (("mcp-servers", "mcp_servers"), ("skills", "skills"), ("backend-tools", "backend_tools")):
        for ref in agent.get(key) or []:
            path = ROOT / folder / f"{str(ref).split(':')[0]}.yaml"
            if path.is_file():
                choices += yaml.safe_load(path.read_text()).get("ui") or []
    return choices


@pytest.mark.parametrize("agent_id", SEED_AGENTS)
def test_each_seed_agent_has_ui_in_the_chat_and_an_a2ui_message(agent_id):
    """Asked 15 November 2026 ("for the 6 agents, have such ui: for the chat itself, for the chat message (a2ui)")."""
    chrome, a2ui_messages = [], []
    for choice in _brought(agent_id):
        spec = ui.UI_CATALOGUE[choice["plugin"]]
        placement = choice.get("placement") or (spec.placements[0].value if spec.placements else None)
        if placement in ui.CHROME_PLACEMENTS:
            chrome.append(choice["plugin"])
        if placement == "message" and choice.get("renderer") == "a2ui":
            a2ui_messages.append(choice["plugin"])
    assert chrome, agent_id
    assert a2ui_messages, agent_id


SEED_AGENTS_WITH_COMPOSER = {
    "worker-marketer": "demo-marketer",
    "worker-shopper": "demo-shopper",
    "worker-accountant": "demo-accountant",
    "worker-traveller": "demo-traveller",
    "worker-terra": "demo-terra",
    "worker-steward-aws": "demo-aws-steward",
    "worker-data-analyst": "demo-data-analyst",
    "worker-functional-analyst": "demo-functional-analyst",
}


@pytest.mark.parametrize("agent,demo", sorted(SEED_AGENTS_WITH_COMPOSER.items()))
def test_each_seed_agent_and_its_demo_bring_the_composer(agent, demo):
    """The seed agents and their public demos bring the Composer's button (the user, 21 November 2026):
    it opens how the application is built — its Canvas, its spec and its Python — full screen, from the toolbar."""
    from agentspecs.apps import load_apps

    spec = yaml.safe_load((ROOT / "agents" / f"{agent}.yaml").read_text())
    assert "composer-portal" in [choice["plugin"] for choice in spec["ui"]], agent
    app = load_apps()[demo]
    assert "composer-portal" in [choice.plugin for choice in app.ui], demo
    composer = ui.UI_CATALOGUE["composer-portal"]
    assert composer.plugin == "@datalayer/agent-plugin-composer-portal"
    assert [p.value for p in composer.placements][0] == "toolbar"


def test_every_application_has_the_composer_unless_it_leaves_it_out():
    """Every application's chat has the Composer button, listed in `ui` or not (the user, 21 November 2026),
    unless its spec leaves it out with `interface.composer_portal_disabled`; never both said."""
    from agentspecs.apps import COMPOSER_PORTAL, load_apps

    assert COMPOSER_PORTAL == "composer-portal" and COMPOSER_PORTAL in ui.UI_CATALOGUE
    base = {"id": "notes", "name": "Notes", "kind": "chat", "agent": "a"}
    assert AppSpec.model_validate(base).interface.composer_portal_disabled is False
    left_out = AppSpec.model_validate({**base, "interface": {"composer_portal_disabled": True}})
    assert left_out.interface.composer_portal_disabled is True
    assert COMPOSER_PORTAL not in [choice.plugin for choice in left_out.ui]
    with pytest.raises(ValidationError, match="leaves it out"):
        AppSpec.model_validate(
            {
                **base,
                "ui": [{"plugin": "chat"}, {"plugin": COMPOSER_PORTAL}],
                "interface": {"composer_portal_disabled": True},
            }
        )
    with pytest.raises(ValidationError):
        AppSpec.model_validate({**base, "interface": {"composer_portal_disabled": "maybe"}})
    # The catalogue's applications all have it today: none leaves it out.
    assert not [app.id for app in load_apps().values() if app.interface.composer_portal_disabled]


def test_every_application_has_the_plugins_manager_unless_it_leaves_it_out():
    """Every application has the plugins manager's button in its chat's footer, listed in `ui` or not (the user,
    21 November 2026: "all our apps should render with that plugin"), unless its spec leaves it out with
    `interface.plugin_manager_disabled`; never both said."""
    from agentspecs.apps import PLUGIN_MANAGER, load_apps

    assert PLUGIN_MANAGER == "plugin-manager" and PLUGIN_MANAGER in ui.UI_CATALOGUE
    manager = ui.UI_CATALOGUE[PLUGIN_MANAGER]
    assert manager.plugin == "@datalayer/agent-plugin-plugin-manager"
    assert [p.value for p in manager.placements][0] == "footer"
    # The one Slot it fills is the one its description puts it in (the chat's footer row under the prompt
    # since 22 November 2026), read from the spec rather than pinned here.
    (slot,) = manager.contributions.slots
    assert slot.startswith("agent.") and f"(`{slot}`" in manager.description, slot
    assert manager.implementation.model_dump(exclude_none=True) == {
        "package": "@datalayer/agent-runtimes",
        "module": "lib/apps/plugins/plugin-manager",
        "export": "pluginManagerPlugin",
        "kind": "factory",
    }
    base = {"id": "notes", "name": "Notes", "kind": "chat", "agent": "a"}
    assert AppSpec.model_validate(base).interface.plugin_manager_disabled is False
    left_out = AppSpec.model_validate({**base, "interface": {"plugin_manager_disabled": True}})
    assert left_out.interface.plugin_manager_disabled is True
    with pytest.raises(ValidationError, match="leaves it out"):
        AppSpec.model_validate(
            {
                **base,
                "ui": [{"plugin": "chat"}, {"plugin": PLUGIN_MANAGER}],
                "interface": {"plugin_manager_disabled": True},
            }
        )
    with pytest.raises(ValidationError):
        AppSpec.model_validate({**base, "interface": {"plugin_manager_disabled": "maybe"}})
    # None of the catalogue's applications lists it or leaves it out today: each has it by default.
    for app in load_apps().values():
        assert not app.interface.plugin_manager_disabled, app.id
        assert PLUGIN_MANAGER not in [choice.plugin for choice in app.ui], app.id
