# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The colour of a spec: a name of the palette, or a hex where no name fits.

An agent, a team and an Op each carry a ``color``. It names a colour of the Datalayer palette
(`@datalayer/primer-addons`, its ``paletteColorNames``), so that the page drawing it gives the
value the current theme and mode give that name: ``indigo`` is a deep indigo on a light page
and a bright one on a dark page, in every theme. The names are the palette's roles — ``primary``,
``glow``, ``surge``…, whose colour changes with the theme — and its hues, ``red`` … ``rose``
round the wheel and the neutrals ``slate``, ``gray`` and ``stone``, whose hue does not.

A hex, ``#RGB`` or ``#RRGGBB``, is still taken, and drawn as it is in every theme: for a colour
that is not one of the palette's, such as a brand's own.

:data:`COLOR_NAMES` is a copy of the palette's list. The palette is the one source:
``tests/test_colors.py`` checks this copy against it when the primer-addons sources are beside
this checkout (``PRIMER_ADDONS_DIR``, else ``../../../tech/primer/addons``).
"""

from __future__ import annotations

import re

#: The palette's roles: their colour changes with the theme.
COLOR_ROLE_NAMES: tuple[str, ...] = (
    "bg",
    "bgPanel",
    "bgAlt",
    "primary",
    "secondary",
    "accent",
    "glow",
    "pop",
    "spark",
    "blaze",
    "surge",
    "flame",
    "gold",
    "textLight",
    "textMuted",
)

#: The palette's hues, round the wheel, then the neutrals: each keeps its hue in every theme, deep
#: on light and bright on dark.
COLOR_HUE_NAMES: tuple[str, ...] = (
    "red",
    "orange",
    "amber",
    "yellow",
    "lime",
    "green",
    "emerald",
    "teal",
    "cyan",
    "sky",
    "blue",
    "indigo",
    "violet",
    "purple",
    "fuchsia",
    "pink",
    "rose",
    "slate",
    "gray",
    "stone",
)

#: Every name of the palette, in its order: the roles, then the hues.
COLOR_NAMES: tuple[str, ...] = COLOR_ROLE_NAMES + COLOR_HUE_NAMES

#: A hex colour, ``#RGB`` or ``#RRGGBB``.
HEX_COLOR_PATTERN = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"

_HEX = re.compile(HEX_COLOR_PATTERN)


def is_hex_color(value: str) -> bool:
    """Whether a value is a hex colour, ``#RGB`` or ``#RRGGBB``."""
    return bool(_HEX.match(value))


def check_color(value: str) -> str:
    """A spec's colour, as it is when the palette names it or it is a hex; empty is no colour.

    Anything else is refused, in a sentence that lists the names.
    """
    if value == "" or value in COLOR_NAMES or is_hex_color(value):
        return value
    raise ValueError(
        f"the colour {value!r} is neither a name of the palette nor a hex (#RGB or #RRGGBB); "
        f"the names are {', '.join(COLOR_NAMES)}"
    )
