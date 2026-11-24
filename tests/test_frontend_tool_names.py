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

import json
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
    # The kernel tools, handed under their editor's domain (agent-runtimes' notebook and Lexical adapters).
    "executeCodeInNotebook": "notebookExecuteCodeInNotebook",
    "executeCodeInDocument": "documentExecuteCodeInDocument",
}

#: The domains the notebook and Lexical adapters hand their tools under: a bare camel-case name
#: whose domain-prefixed form is a tool is that tool's old name.
DOMAINS = ("notebook", "document")

#: The notebook's tools were camel case already, without their domain.
NOTEBOOK_OLD = {"readCell", "readAllCells", "insertCell", "updateCell", "runCell", "executeCode", "proposeCellUpdate"}


def _camel(name: str) -> str:
    return re.sub(r"_+([a-zA-Z0-9])", lambda m: m.group(1).upper(), name.removeprefix("datalayer_"))


#: The tools of the sets declared ``toolset: all``, which name none: vendored from agent-runtimes'
#: export of its UI plugins' tools, held to it below when agent-runtimes is beside this checkout.
INVENTORY_PATH = Path(__file__).resolve().parent / "fixtures" / "wildcard_frontend_tools.json"
INVENTORY = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
#: agent-runtimes' export: agentspecs nested in its checkout, or beside it in one workspace.
_EXPORT = Path("src") / "specs" / "uiFrontendTools.generated.ts"
EXPORT_CANDIDATES = (ROOT.parents[1] / _EXPORT, ROOT.parents[1] / "agent-runtimes" / _EXPORT)
EXPORT_PATH = next((path for path in EXPORT_CANDIDATES if path.is_file()), EXPORT_CANDIDATES[0])


def _frontend_tools() -> set[str]:
    names: set[str] = set()
    for path in (ROOT / "frontend-tools").glob("*.yaml"):
        toolset = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("toolset")
        if isinstance(toolset, list):
            names.update(toolset)
        elif toolset == "all":
            names.update(INVENTORY["tools"][INVENTORY["sources"][path.stem]])
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
        renamed = {SPECIAL.get(token) or (_camel(token) if "_" in token else None)}
        if token in NOTEBOOK_OLD or "_" not in token:
            renamed |= {domain + token[0].upper() + token[1:] for domain in DOMAINS}
        if renamed & TOOLS:
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
    # A set declared `toolset: all` names its tools through the inventory (page-document's here).
    assert stale_names("read it with document_read_all_blocks, then document_insert_block") == [
        "document_read_all_blocks",
        "document_insert_block",
    ]
    assert stale_names("documentReadAllBlocks, then documentInsertBlock") == []
    # The kernel tools take their editor's domain.
    assert stale_names("run it with executeCodeInNotebook or executeCodeInDocument") == [
        "executeCodeInNotebook",
        "executeCodeInDocument",
    ]
    assert stale_names("run it with notebookExecuteCodeInNotebook or documentExecuteCodeInDocument") == []


def test_the_export_is_looked_for_nested_and_beside():
    assert EXPORT_CANDIDATES[0].parts[-3:] == ("src", "specs", "uiFrontendTools.generated.ts")
    assert EXPORT_CANDIDATES[0].parent.parent.parent == ROOT.parents[1]
    assert EXPORT_CANDIDATES[1].parent.parent.parent == ROOT.parents[1] / "agent-runtimes"


def test_every_set_of_all_its_tools_has_an_inventory():
    for path in sorted((ROOT / "frontend-tools").glob("*.yaml")):
        if (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("toolset") == "all":
            assert INVENTORY["tools"].get(INVENTORY["sources"].get(path.stem, "")), path.stem


@pytest.mark.skipif(not EXPORT_PATH.is_file(), reason="agent-runtimes is not beside this checkout")
def test_the_inventory_is_agent_runtimes_export():
    text = EXPORT_PATH.read_text(encoding="utf-8")
    exported = json.loads(text[text.index("= {") + 2 : text.rindex("};") + 1])
    for plugin, tools in INVENTORY["tools"].items():
        assert tools == [tool["name"] for tool in exported[plugin]], plugin


@pytest.mark.parametrize("path", SPECS, ids=lambda path: f"{path.parent.name}/{path.stem}")
def test_a_spec_names_frontend_tools_as_the_page_hands_them(path):
    assert stale_names(path.read_text(encoding="utf-8")) == [], path.name
