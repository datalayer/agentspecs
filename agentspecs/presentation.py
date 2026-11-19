# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""A presentation: what an agent or an application is, as one Markdown
document, for a page that presents it beside its conversation.

An agent says its own (``presentation``, with its one-line ``tagline``) and
an application says its own (the Appspec's ``presentation``): a public demo
of an agent repeats what its agent says of itself, then says what the demo
is and where to go next.

It is plain Markdown and reads as such. A page that presents it draws four
kinds of block in a way of its own, and everything else as Markdown:

- a **paragraph**: what it is, in a sentence or two;
- a **bullet list**: what it does, one line an item (drawn with a check mark
  before each);
- a **note**: a paragraph wholly in emphasis (``*Try it here: …*``), drawn
  quieter, in italics;
- **actions**: a paragraph holding only links, drawn as a row of buttons —
  a link in bold (``**[Start building](/signin)**``) the main one, the others
  beside it. A link that starts with ``/`` is an address of the site that
  shows the presentation.

The name and the face above it are the spec's own ``name`` and ``emoji``,
never written in the document. Raw HTML is refused.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Literal, Tuple

#: The longest a presentation may be, in characters.
PRESENTATION_MAX = 4000

#: The longest an agent's one-line tagline may be, in characters.
TAGLINE_MAX = 80

_LINK = r"\[([^\]\n]+)\]\(([^)\s]+)\)"
_ACTION = re.compile(rf"(\*\*{_LINK}\*\*|{_LINK})")
_HTML = re.compile(r"<[A-Za-z!/][^>]*>")

PresentationKind = Literal["paragraph", "list", "note", "actions"]


@dataclass(frozen=True)
class PresentationAction:
    """A link of an actions paragraph."""

    label: str
    href: str
    #: Written in bold: the main one.
    primary: bool = False


@dataclass(frozen=True)
class PresentationBlock:
    """A block of a presentation, as a page that presents it reads it."""

    kind: PresentationKind
    #: A paragraph's or a note's words on one line; empty for a list or actions.
    text: str = ""
    #: A list's items.
    items: Tuple[str, ...] = ()
    #: An actions paragraph's links.
    actions: Tuple[PresentationAction, ...] = ()


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _actions_of(text: str) -> Tuple[PresentationAction, ...]:
    """The links of a paragraph that holds only links, else none."""
    if _ACTION.sub("", text).strip():
        return ()
    found: List[PresentationAction] = []
    for match in _ACTION.finditer(text):
        bold = match.group(0).startswith("**")
        label, href = (match.group(2), match.group(3)) if bold else (match.group(4), match.group(5))
        found.append(PresentationAction(label=label, href=href, primary=bold))
    return tuple(found)


def presentation_blocks(markdown: str) -> List[PresentationBlock]:
    """A presentation's blocks, in order: paragraphs, lists, notes and actions."""
    blocks: List[PresentationBlock] = []
    for chunk in re.split(r"\n\s*\n", markdown.strip()):
        lines = [line for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        if re.match(r"^[-*+]\s+", lines[0]):
            items: List[str] = []
            for line in lines:
                bullet = re.match(r"^[-*+]\s+(.*)$", line)
                if bullet:
                    items.append(bullet.group(1).strip())
                elif items:
                    # A wrapped item goes on under its bullet.
                    items[-1] = f"{items[-1]} {line.strip()}"
            blocks.append(PresentationBlock(kind="list", items=tuple(items)))
            continue
        text = _one_line(chunk)
        actions = _actions_of(text)
        if actions:
            blocks.append(PresentationBlock(kind="actions", actions=actions))
            continue
        note = re.match(r"^([*_])(?![*_])(.+)(?<![*_])\1$", text)
        if note and note.group(1) not in note.group(2):
            blocks.append(PresentationBlock(kind="note", text=note.group(2).strip()))
            continue
        blocks.append(PresentationBlock(kind="paragraph", text=text))
    return blocks


def presentation_problems(markdown: str) -> List[str]:
    """What is wrong with a presentation, in sentences; none for an empty one."""
    problems: List[str] = []
    if len(markdown) > PRESENTATION_MAX:
        problems.append(f"a presentation is {PRESENTATION_MAX} characters at most, this one is {len(markdown)}")
    if _HTML.search(markdown):
        problems.append("a presentation is Markdown: raw HTML is refused")
    if re.search(r"^\s{0,3}#{1,6}\s", markdown, flags=re.MULTILINE):
        problems.append("a presentation has no heading: its name and its emoji are the heading above it")
    return problems


def tagline_problems(tagline: str) -> List[str]:
    """What is wrong with an agent's tagline, in sentences."""
    problems: List[str] = []
    if "\n" in tagline.strip():
        problems.append("a tagline is one line")
    if len(tagline.strip()) > TAGLINE_MAX:
        problems.append(f"a tagline is {TAGLINE_MAX} characters at most, this one is {len(tagline.strip())}")
    return problems


__all__ = [
    "PRESENTATION_MAX",
    "TAGLINE_MAX",
    "PresentationAction",
    "PresentationBlock",
    "presentation_blocks",
    "presentation_problems",
    "tagline_problems",
]
