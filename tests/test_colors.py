# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""A spec's colour: a name of the palette, or a hex where no name fits."""

import os
import re
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from agentspecs.colors import COLOR_NAMES, check_color
from agentspecs.ops import OpSpec
from agentspecs.teams import TeamSpec

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "agentspecs"

#: The palette's sources: `PRIMER_ADDONS_DIR`, else where the monorepo keeps them.
PRIMER_ADDONS = Path(
    os.environ.get("PRIMER_ADDONS_DIR", ROOT.parent.parent.parent / "tech" / "primer" / "addons")
)


def _colors():
    """Every `color` a catalogue's YAML gives at its top level."""
    for path in sorted(SPECS.rglob("*.yaml")):
        spec = yaml.safe_load(path.read_text())
        if isinstance(spec, dict) and "color" in spec:
            yield path.relative_to(SPECS), spec["color"]


def test_a_name_of_the_palette_is_taken():
    for name in ("indigo", "teal", "gray", "primary", "textMuted"):
        assert check_color(name) == name


def test_a_hex_is_taken_short_or_long():
    for value in ("#F38020", "#f38020", "#abc"):
        assert check_color(value) == value


def test_no_colour_is_taken():
    assert check_color("") == ""


@pytest.mark.parametrize("value", ["Indigo", "navy", "#12345", "F38020", "rgb(0, 0, 0)", "isLight"])
def test_anything_else_is_refused_with_the_names(value):
    with pytest.raises(ValueError) as refused:
        check_color(value)
    said = str(refused.value)
    assert repr(value) in said
    assert "indigo" in said and "textMuted" in said and "#RRGGBB" in said


@pytest.mark.parametrize(
    "model, path",
    [(TeamSpec, SPECS / "teams" / "jupyter.yaml"), (OpSpec, next((SPECS / "ops").glob("*.yaml")))],
)
def test_a_team_and_an_op_check_their_colour(model, path):
    spec = yaml.safe_load(path.read_text())
    assert model.model_validate({**spec, "color": "teal"}).color == "teal"
    assert model.model_validate({**spec, "color": "#0F766E"}).color == "#0F766E"
    with pytest.raises(ValidationError, match="neither a name of the palette nor a hex"):
        model.model_validate({**spec, "color": "navy"})


def test_every_colour_of_the_catalogue_is_a_name_or_a_hex():
    seen = 0
    for where, color in _colors():
        seen += 1
        assert isinstance(color, str), where
        check_color(color)
    assert seen > 100


def test_the_catalogue_names_its_colours():
    """A hex is kept only for a brand's own colour, which no theme should change."""
    hexes = {str(where): color for where, color in _colors() if color.startswith("#")}
    assert hexes == {
        "agents/example-cloudflare.yaml": "#F38020",
        "teams/jupyter.yaml": "#F37726",
    }


def test_the_names_are_the_palettes():
    """The palette is the one source of the names: this copy is checked against its list."""
    source = PRIMER_ADDONS / "src" / "theme" / "palettes" / "ColorPalette.tsx"
    hues_source = PRIMER_ADDONS / "src" / "theme" / "colors" / "hueColors.ts"
    if not source.exists():
        pytest.skip(f"the primer-addons sources are not at {PRIMER_ADDONS}")
    text = source.read_text()
    roles = re.search(r"export const paletteRoleNames = \[(.*?)\] as const;", text, re.S)
    hues = re.search(r"export const hueNames = \[(.*?)\] as const;", hues_source.read_text(), re.S)
    assert roles and hues
    names = re.findall(r"'([A-Za-z]+)'", roles.group(1)) + re.findall(
        r"'([A-Za-z]+)'", hues.group(1)
    )
    marked = re.search(r"palette-color-names:start(.*?)palette-color-names:end", text, re.S)
    assert marked and "...paletteRoleNames" in marked.group(1) and "...hueNames" in marked.group(1)
    assert tuple(names) == COLOR_NAMES
