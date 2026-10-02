# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Action classes: what a tool does to the world, said in one word.

A rule written by a person — *ask me before it sends anything* — has to
reach a tool call, and a tool's name does not say what it does. So every tool
of the catalogue carries a **class**:

- ``read`` — looks, and changes nothing;
- ``write`` — creates or changes something that can be changed back;
- ``send`` — puts something in front of another person (a mail, a message, an invitation);
- ``buy`` — spends money, or commits to;
- ``delete`` — removes something;
- ``publish`` — makes something reachable by people who could not reach it.

A tool that can do several of these (``manage_event`` creates, invites and
deletes) carries several, and is treated as the most restricted of them.

Where the class is written:

- a tool of ``agentspecs/tools`` says ``action: send``;
- an MCP server of ``agentspecs/mcp-servers`` says, under ``actions``, the
  class of each tool it serves, by name or by a pattern (``search_*``), and the
  day those names were read off the running server (``checked``).

**A tool with no class is unknown, and unknown is the most restricted**: it
is never taken for a reader. What a server says of its own tools — the
``readOnlyHint`` of the protocol — is a claim by the server, and is not read
here: the class is the catalogue's, written by somebody who looked.
"""

from __future__ import annotations

import fnmatch
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import yaml

_ROOT = Path(__file__).parent


class ActionError(ValueError):
    """An action class that cannot be read — named plainly."""


class ActionClass(str, Enum):
    """What a tool does to the world."""

    READ = "read"
    WRITE = "write"
    SEND = "send"
    BUY = "buy"
    DELETE = "delete"
    PUBLISH = "publish"


#: The classes that act: everything but reading.
ACTING = (
    ActionClass.WRITE,
    ActionClass.SEND,
    ActionClass.BUY,
    ActionClass.DELETE,
    ActionClass.PUBLISH,
)

#: The classes a person is asked about before anything else: what cannot be taken back.
IRREVERSIBLE = (
    ActionClass.SEND,
    ActionClass.BUY,
    ActionClass.DELETE,
    ActionClass.PUBLISH,
)

Classes = Tuple[ActionClass, ...]


def classes_from(value: Any, *, where: str = "an action") -> Classes:
    """One class or a list of them, as a tuple without repeats; refuses a word that is not a class."""
    if value is None:
        return ()
    names = [value] if isinstance(value, str) else list(value)
    classes: List[ActionClass] = []
    for name in names:
        try:
            read = ActionClass(str(name))
        except ValueError:
            raise ActionError(
                f"{where}: {name!r} is not an action class; write one of "
                + ", ".join(item.value for item in ActionClass)
            ) from None
        if read not in classes:
            classes.append(read)
    return tuple(classes)


def is_read_only(classes: Sequence[ActionClass]) -> bool:
    """Whether a tool only reads. An unknown tool — no class — does not."""
    return len(classes) > 0 and all(item is ActionClass.READ for item in classes)


def tool_classes(tool: Mapping[str, Any]) -> Classes:
    """The classes of a tool spec of ``agentspecs/tools``: its ``action``."""
    return classes_from(tool.get("action"), where=f"tool {tool.get('id', '?')!r}")


def server_tool_classes(server: Mapping[str, Any], tool_name: str) -> Classes:
    """The classes of one tool of an MCP server spec; empty when the spec does not say.

    An exact name wins over a pattern, and the first pattern that matches
    wins over the next; ``default`` answers for what nothing matched.
    """
    actions = server.get("actions") or {}
    tools = actions.get("tools") or {}
    where = f"MCP server {server.get('id', '?')!r}, tool {tool_name!r}"
    if tool_name in tools:
        return classes_from(tools[tool_name], where=where)
    for pattern, value in tools.items():
        if any(mark in pattern for mark in "*?[") and fnmatch.fnmatchcase(tool_name, pattern):
            return classes_from(value, where=where)
    return classes_from(actions.get("default"), where=where)


def _load(directory: Path) -> Dict[str, Dict[str, Any]]:
    """Every YAML spec of a directory, by id."""
    specs: Dict[str, Dict[str, Any]] = {}
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        specs[str(data.get("id", path.stem))] = data
    return specs


_TOOLS: Dict[str, Dict[str, Any]] = {}
_SERVERS: Dict[str, Dict[str, Any]] = {}


def tool_specs() -> Dict[str, Dict[str, Any]]:
    """This package's tools, as plain data, read once."""
    if not _TOOLS:
        _TOOLS.update(_load(_ROOT / "tools"))
    return _TOOLS


def server_specs() -> Dict[str, Dict[str, Any]]:
    """This package's MCP servers, as plain data, read once."""
    if not _SERVERS:
        _SERVERS.update(_load(_ROOT / "mcp-servers"))
    return _SERVERS


#: `server.tool`, the server with or without its version: `tavily.tavily_search`,
#: `google-workspace:0.0.1.send_gmail_message`.
_SERVER_TOOL = re.compile(r"^(?P<server>[A-Za-z0-9_-]+)(?::\d+(?:\.\d+)*)?\.(?P<tool>[A-Za-z_][A-Za-z0-9_-]*)$")


def split_ref(ref: str) -> Tuple[Optional[str], str]:
    """A tool reference as (server, tool).

    ``tavily.tavily_search`` is a tool of an MCP server; ``runtime-send-mail``,
    alone, a tool of the tools catalogue. A version is accepted on the server
    or on the bare tool, and dropped.
    """
    matched = _SERVER_TOOL.match(str(ref))
    if matched is not None:
        return matched.group("server"), matched.group("tool")
    return None, _id_of(str(ref))


def classes_of(
    ref: str,
    *,
    tools: Optional[Mapping[str, Mapping[str, Any]]] = None,
    servers: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> Classes:
    """The classes of a tool, by reference; empty when nothing says.

    ``server.tool`` is a tool of an MCP server; a bare id is a tool of the
    tools catalogue. Versions (``id:0.0.1``) are accepted on either.
    """
    server_id, tool_name = split_ref(ref)
    if server_id is None:
        tool = (tools if tools is not None else tool_specs()).get(_id_of(tool_name))
        return tool_classes(tool) if tool else ()
    server = (servers if servers is not None else server_specs()).get(_id_of(server_id))
    return server_tool_classes(server, tool_name) if server else ()


def _id_of(ref: str) -> str:
    """The id of a reference, ``id`` or ``id:version``."""
    base, _, version = str(ref).rpartition(":")
    return base if base and "." in version else str(ref)


def server_actions_problems(server: Mapping[str, Any]) -> List[str]:
    """What is wrong with the ``actions`` of an MCP server spec; empty when nothing is."""
    identity = server.get("id", "?")
    if "actions" not in server:
        return [f"MCP server {identity!r} says nothing of what its tools do: add `actions`"]
    actions = server["actions"] or {}
    problems: List[str] = []
    unknown = sorted(set(actions) - {"checked", "default", "tools", "note"})
    if unknown:
        problems.append(f"MCP server {identity!r}: `actions` does not know {', '.join(unknown)}")
    values: List[Union[str, List[str], None]] = list((actions.get("tools") or {}).values())
    values.append(actions.get("default"))
    for value in values:
        try:
            classes_from(value, where=f"MCP server {identity!r}")
        except ActionError as error:
            problems.append(str(error))
    if actions.get("checked") and not actions.get("tools"):
        problems.append(f"MCP server {identity!r} was checked and names no tool")
    return problems


__all__ = [
    "ACTING",
    "IRREVERSIBLE",
    "ActionClass",
    "ActionError",
    "Classes",
    "classes_from",
    "classes_of",
    "is_read_only",
    "server_actions_problems",
    "server_specs",
    "server_tool_classes",
    "split_ref",
    "tool_classes",
    "tool_specs",
]
