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
- ``side-panels`` is a page UI: its set, ``open_side_panel`` and ``close_side_panel``, opens and
  closes them; what fills one is the UI placed there.
- ``notices`` is a page UI: its one tool, ``show_notice``, slides a notice in over the view.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from agentspecs import ui

ROOT = Path(ui.__file__).resolve().parent

SEVEN = {
    "worker-marketer": "demo-marketer",
    "worker-shopper": "demo-shopper",
    "worker-accountant": "demo-accountant",
    "worker-traveller": "demo-traveller",
    "worker-terra": "demo-terra",
    "worker-steward-aws": "demo-aws-steward",
    "jupyter-data-analyst": "demo-jupyter-data-analyst",
    "worker-analyst": "demo-analyst",
}

#: The agents with something placed in a side panel, and what.
PLACED = {
    "worker-marketer": ("page-deck",),
    "worker-accountant": ("page-sheet",),
    # The user, 18 November 2026: the Jupyter Data Analyst's dataset profile and chart, the Steward's findings by service.
    "jupyter-data-analyst": ("page-sheet",),
    "worker-steward-aws": ("page-sheet",),
    # The user, 19 November 2026: the Analyst's canvas and diagrams, one above the other.
    "worker-analyst": ("page-excalidraw", "page-mermaid"),
}


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


@pytest.mark.parametrize(
    "ui_id,tools",
    [("side-panels", ["open_side_panel", "close_side_panel"]), ("notices", ["show_notice"])],
)
def test_the_side_panels_and_the_notices_are_page_uis(ui_id, tools):
    spec = ui.UI_CATALOGUE[ui_id]
    assert ui.hands_frontend_tools(ui_id)
    assert spec.plugin == f"@datalayer/loop-plugin-{ui_id}"
    assert [p.value for p in spec.placements] == ["message"]
    assert sorted(spec.contributions.points) == [
        "loop.chat.extras",
        "reactor.ui.renderer",
        "reactor.ui.toolBinding",
    ]
    assert spec.contributions.slots == (["loop.viewOverlay"] if ui_id == "notices" else [])
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
        assert "show_notice" in words and "at most once in a turn" in words
    placed = PLACED.get(agent_id)
    # The side panels, for those with something placed there: opened by its first call.
    assert ("side-panels" in sets) == bool(placed) == ("side-panels" in plugins)
    for each in placed or ():
        assert {"plugin": each, "placement": "right"} in agent["ui"]
        assert {"plugin": each, "placement": "right"} in demo["ui"]
    if placed:
        assert {"plugin": "side-panels"} in demo["ui"]
        for words in (prompt, said):
            assert "open_side_panel" in words and "close_side_panel" in words
            assert "right panel" in words
    assert ui.ui_choices_problems(agent["ui"], to_ship=False) == []
    assert ui.ui_choices_problems(demo["ui"], to_ship=True) == []


def test_the_analyst_and_the_steward_say_what_their_sheet_holds():
    analyst = " ".join(raw("agents", "jupyter-data-analyst")["system_prompt"].split())
    assert "a tab Profile with one row per column" in analyst and "sheet_insert_chart" in analyst
    steward = " ".join(raw("agents", "worker-steward-aws")["system_prompt"].split())
    assert "Monthly saving" in steward and "=SUM(E2:E7)" in steward
    for demo in ("demo-jupyter-data-analyst", "demo-aws-steward"):
        said = " ".join(raw("apps", demo)["instructions"].split())
        assert "sheet_create" in said and "they too are tools you use here" in said
        assert "only" in said
    # The Analyst's demo still runs nothing, and says so.
    assert "nothing ran here" in " ".join(
        raw("apps", "demo-jupyter-data-analyst")["instructions"].split()
    )


def test_only_the_agents_that_name_a_set_name_its_ui():
    for path in sorted((ROOT / "agents").glob("*.yaml")):
        agent = yaml.safe_load(path.read_text(encoding="utf-8"))
        sets = {str(each).split(":")[0] for each in agent.get("frontend_tools") or []}
        plugins = {each["plugin"] for each in agent.get("ui") or [] if isinstance(each, dict)}
        for ui_id in ("side-panels", "notices"):
            assert (ui_id in sets) == (ui_id in plugins), (
                f"{path.stem}: {ui_id} is named on one side only"
            )
