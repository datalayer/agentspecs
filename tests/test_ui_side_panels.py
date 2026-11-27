# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The chat's side panels and the agent's notices (the user, 18 November 2026).

"Left and right side panels are the main deliverable. They are real panels that receive controls
and visuals: an agent's UI plugins placed there ... A spec places a UI in `left` or `right`; the
agent can open, close and fill them through frontend tools." Then: "The N/E/S/W sliding panels are
only for notices ... triggered by the agent through one frontend tool."

- ``left`` and ``right`` are placements beside ``header``, ``toolbar``, ``footer``, ``banner`` and
  ``message``; ``panel``, which had no place in any chat, is gone.
- ``side-panels`` is a page UI: its set, ``sidePanelOpen`` and ``sidePanelClose``, opens and
  closes them; what fills one is the UI placed there.
- ``notices`` is a page UI: its one tool, ``noticeShow``, slides a notice in over the view.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from agentspecs import ui

ROOT = Path(ui.__file__).resolve().parent

SEVEN = {
    "worker-marketer": "marketer-tryout",
    "worker-shopper": "shopper-tryout",
    "worker-accountant": "accountant-tryout",
    "worker-traveller": "traveller-tryout",
    "worker-terra": "terra-tryout",
    "worker-steward-aws": "aws-steward-tryout",
    "worker-data-analyst": "data-analyst-tryout",
    "worker-functional-analyst": "functional-analyst-tryout",
}

#: The agents with something placed in a side panel, and what.
PLACED = {
    "worker-marketer": ("page-deck", "page-document"),
    "worker-accountant": ("page-sheet",),
    # The user, 18 November 2026: the Data Analyst's dataset profile and chart, the Steward's findings by service.
    # The user, 24 November 2026: the document and the person's Spaces for the four seed agents.
    "worker-data-analyst": ("page-notebook", "page-sheet", "page-document", "spaces"),
    "worker-steward-aws": ("page-sheet", "page-document", "spaces"),
    "worker-terra": ("page-document", "spaces"),
    # The user, 19 November 2026: the Analyst's canvas and diagrams, one above the other.
    "worker-functional-analyst": (
        "page-excalidraw",
        "page-mermaid",
        "page-react-flow",
        "page-document",
        "spaces",
    ),
}

#: The tab each placed UI takes in the right panel, when it names one.
TABS = {
    "worker-marketer": {"page-deck": "Deck", "page-document": "Document"},
    "worker-data-analyst": {
        "page-notebook": "Notebook",
        "page-sheet": "Spreadsheet",
        "page-document": "Document",
        "spaces": "Spaces",
    },
    "worker-steward-aws": {"page-document": "Document", "spaces": "Spaces"},
    "worker-terra": {"page-document": "Document", "spaces": "Spaces"},
    "worker-functional-analyst": {
        "page-excalidraw": "Excalidraw",
        "page-mermaid": "Mermaid",
        "page-react-flow": "React Flow",
        "page-document": "Document",
        "spaces": "Spaces",
    },
}

#: The four seed agents that carry the document and the person's Spaces (24 November 2026).
WITH_SPACES = (
    "worker-data-analyst",
    "worker-functional-analyst",
    "worker-terra",
    "worker-steward-aws",
)


def raw(folder: str, name: str) -> dict:
    return yaml.safe_load((ROOT / folder / f"{name}.yaml").read_text(encoding="utf-8"))


def test_the_side_panels_are_placements_and_panel_is_gone():
    assert ui.SIDE_PLACEMENTS == ("left", "right")
    assert {"left", "right"} <= set(ui.CHROME_PLACEMENTS)
    assert "panel" not in [p.value for p in ui.UiPlacement]
    with pytest.raises(ValidationError):
        ui.UiChoice.model_validate({"plugin": "page-deck", "placement": "panel"})


def test_what_may_go_in_a_side_panel_says_so():
    """The deck, the sheet and the header UIs; a card a backend tool draws stays in the conversation."""
    for ui_id in ("page-deck", "page-sheet"):
        assert [p.value for p in ui.UI_CATALOGUE[ui_id].placements] == ["message", "right", "left"]
    for ui_id, spec in ui.UI_CATALOGUE.items():
        if spec.header is not None:
            assert [p.value for p in spec.placements] == ["header", "right", "left"], ui_id
    assert (
        ui.ui_choices_problems([{"plugin": "page-deck", "placement": "right"}], to_ship=True) == []
    )
    assert (
        ui.ui_choices_problems([{"plugin": "shop-header", "placement": "left"}], to_ship=True) == []
    )
    refused = ui.ui_choices_problems(
        [{"plugin": "trial-balance", "placement": "right"}], to_ship=True
    )
    assert refused == [
        "The UI plugin Trial balance ('trial-balance') does not go in the chat's right: in its message only."
    ]
    assert ui.ui_choices_problems(
        [{"plugin": "page-deck", "placement": "right", "tab": "Slides"}], to_ship=True
    ) == []
    assert "names a `tab`" in ui.ui_choices_problems(
        [{"plugin": "chat", "tab": "Conversation"}], to_ship=True
    )[0]


@pytest.mark.parametrize(
    "ui_id,tools",
    [("side-panels", ["sidePanelOpen", "sidePanelClose"]), ("notices", ["noticeShow"])],
)
def test_the_side_panels_and_the_notices_are_page_uis(ui_id, tools):
    spec = ui.UI_CATALOGUE[ui_id]
    assert ui.hands_frontend_tools(ui_id)
    assert spec.plugin == f"@datalayer/agent-plugin-{ui_id}"
    assert [p.value for p in spec.placements] == ["message"]
    assert sorted(spec.contributions.points) == [
        "agent.chat.extras",
        "reactor.ui.renderer",
        "reactor.ui.toolBinding",
    ]
    assert spec.contributions.slots == (["agent.viewOverlay"] if ui_id == "notices" else [])
    toolset = raw("frontend-tools", ui_id)
    assert toolset["toolset"] == tools
    assert set(toolset) == {
        "id",
        "version",
        "name",
        "description",
        "tags",
        "enabled",
        "toolset",
        "icon",
        "emoji",
    }


@pytest.mark.parametrize("agent_id", sorted(SEVEN))
def test_each_seed_agent_has_notices_and_its_placed_ui_its_side_panels(agent_id):
    agent = raw("agents", agent_id)
    demo = raw("apps", SEVEN[agent_id])
    sets = {str(each).split(":")[0] for each in agent.get("frontend_tools") or []}
    plugins = {each["plugin"] for each in agent["ui"]}
    prompt = " ".join(agent["system_prompt"].split())
    said = " ".join(demo["instructions"].split())
    # The notice, for all seven: named on both sides, and when to use it.
    assert "notices" in sets and "notices" in plugins
    assert {"plugin": "notices"} in demo["ui"]
    for words in (prompt, said):
        assert "noticeShow" in words and "at most once in a turn" in words
    placed = PLACED.get(agent_id)
    # The side panels, for those with something placed there: opened by its first call.
    assert ("side-panels" in sets) == bool(placed) == ("side-panels" in plugins)
    for each in placed or ():
        expected = {"plugin": each, "placement": "right"}
        tab = TABS.get(agent_id, {}).get(each)
        if tab:
            expected["tab"] = tab
        assert expected in agent["ui"]
        assert expected in demo["ui"]
    if placed:
        assert {"plugin": "side-panels"} in demo["ui"]
        for words in (prompt, said):
            assert "sidePanelOpen" in words and "sidePanelClose" in words
            assert "right panel" in words
    assert ui.ui_choices_problems(agent["ui"], to_ship=False) == []
    assert ui.ui_choices_problems(demo["ui"], to_ship=True) == []


def test_the_analyst_and_the_steward_say_what_their_sheet_holds():
    analyst = " ".join(raw("agents", "worker-data-analyst")["system_prompt"].split())
    assert "a tab Profile with one row per column" in analyst and "sheetInsertChart" in analyst
    steward = " ".join(raw("agents", "worker-steward-aws")["system_prompt"].split())
    assert "Monthly saving" in steward and "=SUM(E2:E7)" in steward
    for demo in ("data-analyst-tryout", "aws-steward-tryout"):
        said = " ".join(raw("apps", demo)["instructions"].split())
        assert "sheetCreate" in said and "they too are tools you use here" in said
        assert "only" in said
    # The Analyst's demo now opens the live notebook and uses its cell tools.
    analyst_demo = raw("apps", "data-analyst-tryout")
    # Since e9fb357 the notebook is a tab of the right panel, beside the conversation.
    assert {"plugin": "page-notebook", "placement": "right", "tab": "Notebook"} in analyst_demo["ui"]
    assert analyst_demo["interface"]["layout"] == "chat"
    analyst_words = " ".join(analyst_demo["instructions"].split())
    assert "notebookReadAllCells" in analyst_words and "notebookInsertCell" in analyst_words
    assert "notebookRunCell" in analyst_words and "nothing ran here" not in analyst_words


def test_the_marketer_names_the_deck_tab_and_a_concrete_deck_deliverable():
    marketer = raw("agents", "worker-marketer")
    assert {"plugin": "page-deck", "placement": "right", "tab": "Deck"} in marketer["ui"]
    suggestions = " ".join(each["text"] for each in marketer["suggestions"])
    assert "six-slide launch deck" in suggestions
    assert "audience and problem" in suggestions and "speaker notes" in suggestions


def test_recent_workspace_plugins_all_have_ui_and_frontend_tool_specs():
    """The named work surfaces are catalogue entries, not implementation-only folders."""
    recent = {
        "page-deck": "Deck in the page",
        "page-sheet": "Sheet in the page",
        "page-mermaid": "Mermaid in the page",
        "page-excalidraw": "Excalidraw in the page",
        "page-react-flow": "React Flow in the page",
        "page-document": "Document in the page",
    }
    for ui_id, name in recent.items():
        assert ui.UI_CATALOGUE[ui_id].name == name
        tools = raw("frontend-tools", ui_id)
        assert tools["id"] == ui_id and tools["toolset"]
    for ui_id in ("notebook", "spreadsheet"):
        assert ui_id in ui.UI_CATALOGUE


def test_only_the_agents_that_name_a_set_name_its_ui():
    for path in sorted((ROOT / "agents").glob("*.yaml")):
        agent = yaml.safe_load(path.read_text(encoding="utf-8"))
        sets = {str(each).split(":")[0] for each in agent.get("frontend_tools") or []}
        plugins = {each["plugin"] for each in agent.get("ui") or [] if isinstance(each, dict)}
        for ui_id in ("side-panels", "notices"):
            assert (ui_id in sets) == (ui_id in plugins), (
                f"{path.stem}: {ui_id} is named on one side only"
            )


def test_spaces_is_a_page_ui_with_its_set():
    spec = ui.UI_CATALOGUE["spaces"]
    assert ui.hands_frontend_tools("spaces")
    assert spec.plugin == "@datalayer/agent-plugin-spaces"
    assert [p.value for p in spec.placements] == ["right", "left"]
    toolset = raw("frontend-tools", "spaces")
    assert toolset["toolset"] == [
        "spacesList",
        "spacesListItems",
        "spacesListItemsOfType",
        "spacesOpenItem",
        "spacesSaveItem",
    ]
    assert "page" in toolset["tags"] and "frontend" in toolset["tags"]


@pytest.mark.parametrize("agent_id", WITH_SPACES)
def test_the_four_seed_agents_carry_the_document_and_the_spaces(agent_id):
    agent = raw("agents", agent_id)
    demo = raw("apps", SEVEN[agent_id])
    sets = {str(each).split(":")[0] for each in agent.get("frontend_tools") or []}
    assert {"page-document", "spaces"} <= sets
    for choices in (agent["ui"], demo["ui"]):
        assert {"plugin": "page-document", "placement": "right", "tab": "Document"} in choices
        assert {"plugin": "spaces", "placement": "right", "tab": "Spaces"} in choices
    for words in (
        " ".join(agent["system_prompt"].split()),
        " ".join(demo["instructions"].split()),
    ):
        for tool in ("spacesList", "spacesListItems", "spacesListItemsOfType", "spacesOpenItem", "spacesSaveItem"):
            assert tool in words, f"{agent_id} is not told {tool}"
        assert "Document tab" in words


def test_only_the_agents_that_name_spaces_name_its_ui():
    for path in sorted((ROOT / "agents").glob("*.yaml")):
        agent = yaml.safe_load(path.read_text(encoding="utf-8"))
        sets = {str(each).split(":")[0] for each in agent.get("frontend_tools") or []}
        plugins = {each["plugin"] for each in agent.get("ui") or [] if isinstance(each, dict)}
        assert ("spaces" in sets) == ("spaces" in plugins), f"{path.stem}: spaces is named on one side only"
