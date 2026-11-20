# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""A header UI: buttons, drop-downs and indicators in the chat's title bar (the user, 18 November 2026).

A UI spec whose first placement is ``header`` may declare what it puts there under ``header``:
at most three items — an ``action`` (a button that says its message), a ``choice`` (a drop-down
told to the agent with every turn) or an ``indicator`` (a label, a counter, a status or a meter
the agent sets) — and the frontend tool, ``set_<its id>``, the agent sets them with. Each of the
seven seed agents and its public demo names one.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from pydantic import ValidationError

from agentspecs import ui

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"

#: Each seed agent, its public demo, and its header UI.
HEADERS = {
    "worker-marketer": ("demo-marketer", "social-header"),
    "worker-shopper": ("demo-shopper", "shop-header"),
    "worker-accountant": ("demo-accountant", "books-header"),
    "worker-traveller": ("demo-traveller", "trip-header"),
    "worker-terra": ("demo-terra", "earth-header"),
    "worker-steward-aws": ("demo-aws-steward", "aws-header"),
    "jupyter-data-analyst": ("demo-jupyter-data-analyst", "notebook-header"),
    "worker-functional-analyst": ("demo-functional-analyst", "analysis-header"),
}


def _yaml(folder: str, name: str) -> dict:
    return yaml.safe_load((ROOT / folder / f"{name}.yaml").read_text())


def _good() -> dict:
    return _yaml("ui", "shop-header")


def _with_item(change: dict, index: int = 0) -> dict:
    spec = _good()
    spec["header"]["items"][index] = {**spec["header"]["items"][index], **change}
    return spec


@pytest.mark.parametrize("plugin", sorted(header for _, header in HEADERS.values()))
def test_a_header_ui_is_calm_named_and_set_by_its_own_tool(plugin):
    spec = ui.UI_CATALOGUE[plugin]
    header = spec.header
    assert header is not None
    assert spec.placements[0] is ui.UiPlacement.HEADER
    assert 2 <= len(header.items) <= ui.HEADER_ITEMS_AT_MOST
    assert header.tool == ui.header_tool_name(plugin) == "set_" + plugin.replace("-", "_")
    assert header.when and header.when.startswith("Call it")
    for item in header.items:
        assert item.label and item.description.endswith("."), item.id
        assert item.octicon, item.id
    # What it registers: its items in the title bar, its tool with the chat's extras, and its
    # drop-downs with every run.
    assert spec.contributions.slots == ["loop.chatHeader"]
    choices = [item for item in header.items if item.kind is ui.UiHeaderItemKind.CHOICE]
    assert spec.contributions.points == ["loop.chat.extras", *(["loop.runProps"] if choices else [])]


def test_the_three_kinds_and_the_four_displays_are_all_shown_by_a_seed_agent():
    items = [item for _, header in HEADERS.values() for item in ui.UI_CATALOGUE[header].header.items]
    assert {item.kind for item in items} == set(ui.UiHeaderItemKind)
    assert {item.display for item in items if item.display} == set(ui.UiHeaderDisplay)


@pytest.mark.parametrize("agent_id", sorted(HEADERS))
def test_each_seed_agent_and_its_demo_name_their_header_and_say_when_to_set_it(agent_id):
    demo_id, plugin = HEADERS[agent_id]
    tool = ui.UI_CATALOGUE[plugin].header.tool
    agent, demo = _yaml("agents", agent_id), _yaml("apps", demo_id)
    assert {"plugin": plugin} in agent["ui"], agent_id
    assert {"plugin": plugin} in demo["ui"], demo_id
    assert ui.ui_choices_problems(agent["ui"], to_ship=False) == []
    assert ui.ui_choices_problems(demo["ui"], to_ship=True) == []
    # The model is told the tool by name, in the agent's instructions and in the demo's.
    assert tool in agent["system_prompt"], agent_id
    assert tool in demo["instructions"], demo_id
    # Every item the tool is said to set is one of the header's.
    settable = {item.id for item in ui.UI_CATALOGUE[plugin].header.settable()}
    assert any(item in demo["instructions"] for item in settable), demo_id


def test_a_header_stands_in_for_the_chip_it_replaces():
    assert ui.UI_CATALOGUE["shop-header"].supersedes == ["basket-total"]
    assert ui.UI_CATALOGUE["trip-header"].supersedes == ["trip-summary"]
    assert ui.UI_CATALOGUE["aws-header"].supersedes == ["aws-savings-badge"]
    with pytest.raises(ValidationError, match="supersedes itself"):
        ui.UiSpec.model_validate({**_good(), "supersedes": ["shop-header"]})


def test_the_tool_takes_one_argument_per_item_it_sets():
    """An indicator is an object (label, tone, visible; value for a counter or a meter), a drop-down one of its options."""
    parameters = ui.header_tool_parameters(ui.UI_CATALOGUE["shop-header"].header)
    assert parameters["additionalProperties"] is False
    assert list(parameters["properties"]) == ["basket", "budget", "approval"]
    basket = parameters["properties"]["basket"]
    assert list(basket["properties"]) == ["value", "label", "tone", "visible"]
    assert basket["properties"]["tone"]["enum"] == ["neutral", "accent", "success", "attention", "danger"]
    assert list(parameters["properties"]["approval"]["properties"]) == ["label", "tone", "visible"]
    assert parameters["properties"]["budget"]["enum"] == ["none", "50", "100", "250"]
    meter = ui.header_tool_parameters(ui.UI_CATALOGUE["earth-header"].header)["properties"]["cloud"]
    assert list(meter["properties"]) == ["value", "max", "label", "tone", "visible"]
    # A button is set by nobody.
    assert "profile" not in ui.header_tool_parameters(ui.UI_CATALOGUE["notebook-header"].header)["properties"]


def test_a_choice_is_told_to_the_agent_in_a_sentence():
    header = ui.UI_CATALOGUE["shop-header"].header
    assert ui.header_says(header, {"budget": "100"}) == [
        "The person's budget for the whole basket, chosen in the chat's header: Under $100. "
        "Keep the basket within it, and say so when something does not fit."
    ]
    # An option that says nothing: no limit is no instruction.
    assert ui.header_says(header, {"budget": "none"}) == []
    assert ui.header_says(header, {}) == []
    with pytest.raises(ValueError, match="no option '75'"):
        ui.header_says(header, {"budget": "75"})
    with pytest.raises(ValueError, match="no drop-down 'basket'"):
        ui.header_says(header, {"basket": "3"})


@pytest.mark.parametrize(
    "spec,why",
    [
        ({**_good(), "placements": ["footer", "header"]}, "its first placement is `header`"),
        ({**_good(), "header": {**_good()["header"], "tool": "set_basket"}}, "is named 'set_shop_header'"),
        ({**_good(), "header": {**_good()["header"], "tool": None, "when": None}}, "names the frontend tool"),
        ({**_good(), "header": {**_good()["header"], "items": _good()["header"]["items"] * 2}}, "at most 3"),
        (_with_item({"id": "Basket"}), "not a header item id"),
        (_with_item({"display": None}), "does not say how it is drawn"),
        (_with_item({"unit": "%"}), "is no meter"),
        (_with_item({"message": "Hello"}), "takes no `message`"),
        (_with_item({"default": "75"}, 1), "not one of its options"),
        (_with_item({"options": [{"id": "a", "label": "A"}]}, 1), "two options at least"),
        (_with_item({"says": None, "default": None, "options": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}]}, 1), "tells the agent nothing"),
        (_with_item({"kind": "action"}, 2), "takes no `display`"),
        (_with_item({"kind": "action", "display": None}, 2), "says nothing"),
        (_with_item({"colour": "red"}), "Extra inputs"),
    ],
)
def test_a_header_refuses(spec, why):
    with pytest.raises(ValidationError, match=why):
        ui.UiSpec.model_validate(spec)


def test_a_header_of_buttons_alone_takes_no_tool():
    button = {"id": "go", "kind": "action", "label": "Go", "description": "Asks to go.", "message": "Go."}
    alone = {**_good(), "supersedes": [], "header": {"items": [button]}}
    assert ui.UiSpec.model_validate(alone).header.tool is None
    with pytest.raises(ValidationError, match="takes no `tool`"):
        ui.UiSpec.model_validate({**alone, "header": {"tool": "set_shop_header", "items": [button]}})
