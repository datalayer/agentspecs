# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The marks of a catalogue entry: the icon and the emoji a page shows beside it.

An MCP server, a skill, a tool and a frontend tool set each carry two marks. A page draws
the icon where it can, the emoji where there is no icon, and nothing where there is neither.

An icon is a reference that says where to find it, so that a page loads the right package
and nothing else: ``<package>:<name>``, the package one of :data:`ICON_PACKAGES` and the name
the icon's own, in kebab case, as that package names it — ``@datalayer/icons-react:odoo``
(the ``odoo.svg`` of the Datalayer icons, exported as ``OdooIcon``),
``@primer/octicons-react:mark-github`` (the octicon ``mark-github``, ``MarkGithubIcon``).
A bare name is refused: it said nothing of the package it came from.

This module only checks the shape. That the name is one the package has is checked where the
package is, by the page that loads it.
"""

from __future__ import annotations

import re
from typing import Any

#: The packages an icon may come from.
ICON_PACKAGES: tuple[str, ...] = (
    "@datalayer/icons-react",
    "@primer/octicons-react",
)

#: An icon reference: ``<package>:<kebab-case name>``.
ICON_PATTERN = (
    "^(" + "|".join(re.escape(package) for package in ICON_PACKAGES) + "):[a-z0-9]+(-[a-z0-9]+)*$"
)

#: The catalogues whose entries carry marks, by their folder under ``agentspecs/``.
MARKED_CATALOGUES: tuple[str, ...] = ("mcp-servers", "skills", "tools", "frontend-tools")

#: The two marks, as a JSON Schema fragment for an entry of a marked catalogue.
MARKS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "icon": {
            "type": "string",
            "pattern": ICON_PATTERN,
            "description": (
                "Where the icon is: <package>:<kebab-case name>, the package one of "
                + ", ".join(ICON_PACKAGES)
            ),
        },
        "emoji": {
            "type": "string",
            "minLength": 1,
            "maxLength": 16,
            "description": "Shown where there is no icon.",
        },
    },
    "required": ["icon", "emoji"],
}

_ICON = re.compile(ICON_PATTERN)


def icon_problem(value: object) -> str | None:
    """Say what is wrong with an icon reference, or None when it is one."""
    if not isinstance(value, str):
        return f"the icon is {type(value).__name__}, not a string"
    if _ICON.match(value):
        return None
    package, sep, _ = value.rpartition(":")
    if not sep:
        return (
            f"the icon {value!r} names no package: write <package>:<name>, "
            f"the package one of {', '.join(ICON_PACKAGES)}"
        )
    if package not in ICON_PACKAGES:
        return f"the icon {value!r} is from {package!r}, not one of {', '.join(ICON_PACKAGES)}"
    return f"the icon {value!r} is not named in kebab case, as its package names it"


def emoji_problem(value: object) -> str | None:
    """Say what is wrong with an emoji, or None when it is one."""
    if not isinstance(value, str) or not value.strip():
        return "the emoji is empty"
    if len(value) > 16 or any(ch.isascii() and ch.isalnum() for ch in value):
        return f"the emoji {value!r} is text, not an emoji"
    return None


def marks_problems(spec: dict[str, Any]) -> list[str]:
    """What is wrong with the marks of one catalogue entry, as sentences."""
    problems = []
    for field, check in (("icon", icon_problem), ("emoji", emoji_problem)):
        if field not in spec:
            problems.append(f"it has no {field}")
            continue
        problem = check(spec[field])
        if problem:
            problems.append(problem)
    return problems


def parse_icon(value: str) -> tuple[str, str]:
    """The package and the name of an icon reference; refuses anything else."""
    problem = icon_problem(value)
    if problem:
        raise ValueError(problem)
    package, _, name = value.rpartition(":")
    return package, name
