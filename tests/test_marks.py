# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Marks: an MCP server, skill, tool or frontend tool set has a packaged icon and an emoji."""

from __future__ import annotations

import pathlib

import jsonschema
import pytest
import yaml

from agentspecs.marks import (
    ICON_PACKAGES,
    MARKED_CATALOGUES,
    MARKS_SCHEMA,
    icon_problem,
    marks_problems,
    parse_icon,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"


def _entries() -> list[tuple[str, dict]]:
    return [
        (f"{catalogue}/{path.name}", yaml.safe_load(path.read_text()))
        for catalogue in MARKED_CATALOGUES
        for path in sorted((ROOT / catalogue).glob("*.yaml"))
    ]


def test_every_entry_of_a_marked_catalogue_has_both_marks_well_formed():
    entries = _entries()
    assert len(entries) > 40
    problems = {where: marks_problems(spec) for where, spec in entries}
    assert {where: said for where, said in problems.items() if said} == {}


def test_the_schema_says_the_same():
    for _, spec in _entries():
        jsonschema.validate({"icon": spec["icon"], "emoji": spec["emoji"]}, MARKS_SCHEMA)


@pytest.mark.parametrize(
    "value",
    [
        "@datalayer/icons-react:odoo",
        "@datalayer/icons-react:github-mark",
        "@primer/octicons-react:mark-github",
        "@primer/octicons-react:file-directory",
    ],
)
def test_a_reference_names_its_package_and_its_icon(value):
    assert icon_problem(value) is None
    package, name = parse_icon(value)
    assert package in ICON_PACKAGES
    assert f"{package}:{name}" == value


@pytest.mark.parametrize(
    "value, said",
    [
        ("notebook", "names no package"),
        ("@mui/icons-material:home", "not one of"),
        ("@primer/octicons-react:ToolsIcon", "kebab case"),
        ("@primer/octicons-react:", "kebab case"),
        (3, "not a string"),
    ],
)
def test_anything_else_is_refused(value, said):
    problem = icon_problem(value)
    assert problem and said in problem
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"icon": value, "emoji": "🧮"}, MARKS_SCHEMA)
    if isinstance(value, str):
        with pytest.raises(ValueError, match=said):
            parse_icon(value)


def test_an_entry_without_marks_is_refused():
    assert marks_problems({}) == ["it has no icon", "it has no emoji"]
    assert marks_problems({"icon": "@primer/octicons-react:tools", "emoji": "tools"}) == [
        "the emoji 'tools' is text, not an emoji"
    ]


def test_the_odoo_accounting_server_is_the_datalayer_server_with_one_toolset():
    spec = yaml.safe_load((ROOT / "mcp-servers" / "odoo-accounting.yaml").read_text())
    datalayer = yaml.safe_load((ROOT / "mcp-servers" / "datalayer.yaml").read_text())
    assert spec["icon"] == "@datalayer/icons-react:odoo"
    assert "https://mcp.datalayer.run/mcp?only=odoo-accounting" in spec["args"]
    assert spec["envvars"] == datalayer["envvars"]
    accounting = {
        name: classes
        for name, classes in datalayer["actions"]["tools"].items()
        if name.startswith("odoo_accounting_")
    }
    assert spec["actions"]["tools"] == accounting
