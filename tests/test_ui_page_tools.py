# Copyright (c) 2025-2026 Datalayer, Inc.
# Distributed under the terms of the Modified BSD License.

"""Page UIs: a deck and a sheet an agent builds in the conversation with frontend tools.

The user, 18 November 2026: "add to the marketer the frontend tools to create slides; add to the
accountant the frontend tools to create spreadsheets". A page UI (``ui/page-deck.yaml``,
``ui/page-sheet.yaml``) is the plugin that hands the chat's agent the frontend tool set of its own
id (``frontend-tools/<id>.yaml``), bound to what it keeps in the page for the conversation, and
draws the calls. An agent names the two together, and so does its public demo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agentspecs import ui

ROOT = Path(ui.__file__).resolve().parent

#: Each page UI: the agent that has it, its public demo, and the tools of its set.
PAGE_UIS = {
    "page-deck": (
        "worker-marketer",
        "demo-marketer",
        [
            "deck_create",
            "deck_set_title",
            "deck_add_slide",
            "deck_add_slides",
            "deck_update_slide",
            "deck_move_slide",
            "deck_delete_slide",
            "deck_set_theme",
            "deck_read",
        ],
    ),
    "page-sheet": (
        "worker-accountant",
        "demo-accountant",
        [
            "sheet_create",
            "sheet_write_range",
            "sheet_read_range",
            "sheet_format_range",
            "sheet_freeze",
            "sheet_add_tab",
            "sheet_show_tab",
            "sheet_insert_chart",
        ],
    ),
    # The Functional Analyst's canvas and diagrams (the user, 19 November 2026): the tools of
    # @datalayer/reactor-excalidraw and @datalayer/reactor-mermaid, run in the page.
    "page-excalidraw": (
        "worker-functional-analyst",
        "demo-functional-analyst",
        [
            "datalayer_excalidrawInsertNode",
            "datalayer_excalidrawFromMermaid",
            "datalayer_excalidrawListDrawings",
            "datalayer_excalidrawReadScene",
            "datalayer_excalidrawAddElements",
            "datalayer_excalidrawUpdateElements",
            "datalayer_excalidrawConnectElements",
            "datalayer_excalidrawDeleteElements",
            "datalayer_excalidrawSetAppState",
            "datalayer_excalidrawResize",
            "datalayer_excalidrawClearScene",
        ],
    ),
    "page-mermaid": (
        "worker-functional-analyst",
        "demo-functional-analyst",
        [
            "datalayer_mermaidSetDiagram",
            "datalayer_mermaidReadDiagram",
            "datalayer_mermaidListDiagrams",
            "datalayer_mermaidValidate",
            "datalayer_mermaidRenderSvg",
            "datalayer_mermaidListDiagramTypes",
        ],
    ),
}


def raw(folder: str, name: str) -> dict:
    return yaml.safe_load((ROOT / folder / f"{name}.yaml").read_text(encoding="utf-8"))


def test_a_page_ui_is_a_ui_and_a_frontend_tool_set_of_one_id():
    # Besides the deck and the sheet, the side panels and the notices (tests/test_ui_side_panels.py).
    assert sorted(i for i in ui.UI_CATALOGUE if ui.hands_frontend_tools(i)) == sorted(
        [*PAGE_UIS, "notices", "side-panels"]
    )
    # A UI that draws a backend tool's card hands no tool; an id that is no id reads no file.
    assert not ui.hands_frontend_tools("trial-balance")
    assert not ui.hands_frontend_tools("books-header")
    assert not ui.hands_frontend_tools("../agents/worker-marketer")


@pytest.mark.parametrize("ui_id", sorted(PAGE_UIS))
def test_a_page_ui_goes_in_the_conversation_and_hands_its_tools_with_the_chats_extras(ui_id):
    spec = ui.UI_CATALOGUE[ui_id]
    assert spec.plugin == f"@datalayer/loop-plugin-{ui_id}"
    # In the conversation by default; in a side panel where an agent places it (18 November 2026).
    assert [p.value for p in spec.placements] == ["message", "right", "left"]
    assert spec.header is None
    assert sorted(spec.contributions.points) == ["loop.chat.extras", "reactor.ui.renderer", "reactor.ui.toolBinding"]


@pytest.mark.parametrize("ui_id", sorted(PAGE_UIS))
def test_a_page_tool_set_names_its_tools_and_nothing_else(ui_id):
    tools = raw("frontend-tools", ui_id)
    assert tools["id"] == ui_id and tools["enabled"] is True
    assert tools["toolset"] == PAGE_UIS[ui_id][2]
    assert "page" in tools["tags"] and "frontend" in tools["tags"]
    # The handlers are the page's: a set carries no code, no address and no schema of its own.
    assert set(tools) == {"id", "version", "name", "description", "tags", "enabled", "toolset", "icon", "emoji"}


@pytest.mark.parametrize("ui_id", sorted(PAGE_UIS))
def test_the_agent_names_the_set_and_the_ui_together_and_is_told_when_to_use_them(ui_id):
    agent_id, _demo, tools = PAGE_UIS[ui_id]
    agent = raw("agents", agent_id)
    assert f"{ui_id}:0.0.1" in agent["frontend_tools"]
    # Placed in the chat's right panel: drawn there, a line per call in the conversation.
    assert {"plugin": ui_id, "placement": "right"} in agent["ui"]
    prompt = " ".join(agent["system_prompt"].split())
    first = tools[0]
    assert first in prompt, f"{agent_id} is not told {first}"
    # When to make one, to say what it contains, and to ask before a long one.
    assert "Make one when the person asks" in prompt
    assert "say in two or three lines what the" in prompt
    assert "Ask before a" in prompt
    assert "run in the page" in prompt or "which run in the page" in prompt


def test_only_the_agents_that_name_a_page_ui_name_its_set():
    for path in sorted((ROOT / "agents").glob("*.yaml")):
        agent = yaml.safe_load(path.read_text(encoding="utf-8"))
        sets = {str(each).split(":")[0] for each in agent.get("frontend_tools") or []}
        plugins = {each["plugin"] for each in agent.get("ui") or [] if isinstance(each, dict)}
        for ui_id in PAGE_UIS:
            assert (ui_id in sets) == (ui_id in plugins), f"{path.stem}: {ui_id} is named on one side only"


@pytest.mark.parametrize("ui_id", sorted(PAGE_UIS))
def test_the_public_demo_has_it_and_builds_from_its_example_only(ui_id):
    agent_id, demo_id, tools = PAGE_UIS[ui_id]
    demo = raw("apps", demo_id)
    assert demo["agent"].split(":")[0] == agent_id
    assert {"plugin": ui_id, "placement": "right"} in demo["ui"]
    said = " ".join(demo["instructions"].split())
    for tool in tools:
        if tool != "deck_set_title":
            assert tool in said, f"{demo_id} does not name {tool}"
    assert "they run in the page" in said
    if demo_id == "demo-accountant":
        # It reads the demo Odoo books (0.0.8): the sheet holds what the books' tools returned.
        assert "make it from what the tools returned only" in said
    else:
        assert "example" in said and "only" in said
    assert not ui.ui_choices_problems(demo["ui"], to_ship=True)


def test_the_accountant_reads_before_it_writes_over_the_persons_cells():
    for spec in (raw("agents", "worker-accountant")["system_prompt"], raw("apps", "demo-accountant")["instructions"]):
        said = " ".join(spec.split())
        assert "sheet_read_range before" in said
        assert "=SUM(" in said


def test_the_marketer_lays_a_deck_out_in_one_or_two_calls():
    # One call a slide took a run a slide, and a message takes ten runs of page tools at most.
    agent = " ".join(raw("agents", "worker-marketer")["system_prompt"].split())
    demo = " ".join(raw("apps", "demo-marketer")["instructions"].split())
    assert "in one or two deck_add_slides calls" in agent
    assert "in one deck_add_slides call" in demo
    for said in (agent, demo):
        assert "never a call a slide" in said
        assert "eep deck_add_slide for a single slide" in said


#: Every agent and demo that builds a sheet, with the title bar's tool it sets beside it.
SHEET_BUILDERS = {
    ("agents", "worker-accountant"): "set_books_header",
    ("apps", "demo-accountant"): "set_books_header",
    ("agents", "jupyter-data-analyst"): "set_notebook_header",
    ("apps", "demo-jupyter-data-analyst"): "set_notebook_header",
    ("agents", "worker-steward-aws"): "set_aws_header",
    ("apps", "demo-aws-steward"): "set_aws_header",
}


def test_every_sheet_builder_is_listed():
    found = set()
    for folder in ("agents", "apps"):
        for path in sorted((ROOT / folder).glob("*.yaml")):
            spec = yaml.safe_load(path.read_text(encoding="utf-8"))
            plugins = {each["plugin"] for each in spec.get("ui") or [] if isinstance(each, dict)}
            if "page-sheet" in plugins:
                found.add((folder, path.stem))
    assert found == set(SHEET_BUILDERS)


@pytest.mark.parametrize("where", sorted(SHEET_BUILDERS), ids=lambda where: where[1])
def test_a_sheet_is_built_a_step_a_response(where):
    # The user, 19 November 2026: on the visitors' runtime the Accountant's demo made one page call
    # a response (the sheet, a range, a format, the panel, the header) and one sheet took more
    # rounds than a message has. A step's calls go together in one response; edits stay single.
    folder, name = where
    spec = raw(folder, name)
    said = " ".join((spec.get("system_prompt") or spec["instructions"]).split())
    header = SHEET_BUILDERS[where]
    assert "Build the sheet in as few responses as you can" in said, name
    assert "making all the calls of a step together in one response" in said, name
    assert "sheet_create and sheet_write_range in one response" in said, name
    assert f"then sheet_format_range, open_side_panel if the panel is closed, and {header} in the next" in said, name
    assert "Keep single calls for later edits" in said, name
