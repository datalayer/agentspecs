# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Agents, applications and battles name frontend tools as the page hands them (0.1.17).

The frontend tool sets name their tools in camel case under their domain (``deckCreate``,
``arenaWatch``, ``noticeShow``); agent-runtimes' ``frontendToolName`` renames what a plugin
registers to that name, which is the only one the model is given. A prompt, a goal or a rubric that
still says the old name (``deck_create``, ``arena_watch``, ``show_notice``) asks for a tool the model
does not have. This reads every spec that speaks to or about an agent and refuses a token whose
normalized form is a frontend tool while the token itself is not.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from agentspecs import ui

ROOT = Path(ui.__file__).resolve().parent

#: The renames that are not the camel case of the old name (agent-runtimes' ``SPECIAL``).
SPECIAL = {
    "show_notice": "noticeShow",
    "open_side_panel": "sidePanelOpen",
    "close_side_panel": "sidePanelClose",
    "list_shapes": "reactFlowListShapes",
    "insert_shape": "reactFlowInsertShape",
    "link_shapes": "reactFlowLinkShapes",
    "move_shape": "reactFlowMoveShape",
    "set_notebook_header": "notebookSetHeader",
    "search_public_library": "publicLibrarySearch",
    "list_public_library": "publicLibraryList",
    "publish_library_item": "publicLibraryPublishItem",
}

#: The notebook's tools were camel case already, without their domain.
NOTEBOOK_OLD = {"readCell", "readAllCells", "insertCell", "updateCell", "runCell", "executeCode", "proposeCellUpdate"}


def _camel(name: str) -> str:
    return re.sub(r"_+([a-zA-Z0-9])", lambda m: m.group(1).upper(), name.removeprefix("datalayer_"))


def _frontend_tools() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "frontend-tools").glob("*.yaml"):
        toolset = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("toolset")
        if isinstance(toolset, list):
            names.update(toolset)
    # A header's tool, as the model is given it.
    for spec in ui.UI_CATALOGUE.values():
        if spec.header is not None and spec.header.tool:
            names.add(SPECIAL.get(spec.header.tool) or _camel(spec.header.tool))
    return names


TOOLS = _frontend_tools()
TOKEN = re.compile(r"(?<![A-Za-z0-9_])([a-z][a-z0-9]*(?:_[a-z0-9]+)+|[a-z]+[A-Z][A-Za-z0-9]*)(?![A-Za-z0-9_])")


def stale_names(text: str) -> list[str]:
    """The old names of frontend tools a text says."""
    found = []
    for token in TOKEN.findall(text):
        if token in TOOLS:
            continue
        renamed = SPECIAL.get(token) or (_camel(token) if "_" in token else None)
        if token in NOTEBOOK_OLD:
            renamed = "notebook" + token[0].upper() + token[1:]
        if renamed in TOOLS:
            found.append(token)
    return found


SPECS = sorted(
    path
    for folder in ("agents", "apps", "battles", "teams", "scenes")
    if (ROOT / folder).is_dir()
    for path in (ROOT / folder).rglob("*.yaml")
)


def test_it_finds_an_old_name():
    assert stale_names("call arena_watch, then deck_create and show_notice; readAllCells") == [
        "arena_watch",
        "deck_create",
        "show_notice",
        "readAllCells",
    ]
    assert stale_names("call arenaWatch, deckCreate, noticeShow and notebookReadAllCells") == []
    assert stale_names("sales_by_region and set_up are no tools") == []


@pytest.mark.parametrize("path", SPECS, ids=lambda path: f"{path.parent.name}/{path.stem}")
def test_a_spec_names_frontend_tools_as_the_page_hands_them(path):
    assert stale_names(path.read_text(encoding="utf-8")) == [], path.name
