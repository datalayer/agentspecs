# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The protocols catalogue (AGENT_PROTOCOLS PS-01) and what speaks them (PS-02)."""

from __future__ import annotations

import pathlib

import pytest
import yaml
from pydantic import ValidationError

from agentspecs import protocols
from agentspecs.apps import APP_CATALOGUE, AppSpec

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"


def test_the_catalogue_holds_the_protocols_the_plan_targets_as_they_stand():
    catalogue = protocols.PROTOCOL_CATALOGUE
    # UCP and ACP in applications at test merchants only (decided 2026-10-13).
    shipped = {"mcp", "a2a", "a2ui", "ag-ui", "pap", "pact", "web-bot-auth", "ucp", "acp"}
    planned = {"tap"}
    assert set(catalogue) == shipped | planned
    assert {p for p, spec in catalogue.items() if spec.status.value == "shipped"} == shipped
    assert {p.id: p.appspec_block.value for p in catalogue.values() if p.appspec_block} == {
        "pap": "pap",
        "pact": "pact",
        "a2a": "a2a",
        "web-bot-auth": "signed_fetch",
    }
    assert {p.layer.value for p in catalogue.values()} == {"transport", "consent", "identity", "commerce", "ui"}


def test_the_schema_and_the_reference_are_the_specs():
    assert protocols.SCHEMA_PATH.read_text() == protocols.schema_text()
    if protocols.REFERENCE_PATH.is_file():
        assert protocols.REFERENCE_PATH.read_text() == protocols.reference_text()


@pytest.mark.parametrize(
    "change,why",
    [
        ({"id": "Not An Id"}, "not a protocol id"),
        ({"spec_url": "http://x.example"}, "https"),
        ({"status": "soon"}, "status"),
        ({"protocol_tools": ["nothing"]}, "no protocol-tools table"),
        ({"token": "x"}, "Extra inputs"),
    ],
)
def test_a_spec_refuses(change, why):
    good = yaml.safe_load((ROOT / "protocols" / "pap.yaml").read_text())
    with pytest.raises(ValidationError, match=why):
        protocols.ProtocolSpec.model_validate({**good, **change})


def test_an_agent_lists_only_protocols_of_the_catalogue():
    for path in sorted((ROOT / "agents").rglob("*.yaml")):
        spec = yaml.safe_load(path.read_text()) or {}
        assert protocols.protocols_problems(list(spec.get("protocols") or []), to_ship=False) == [], path.name


BASE = {"id": "shop", "name": "Shop", "kind": "chat", "agent": "a"}
PAP = {"profile": "draft-01", "connections": [{"id": "orders", "company": "manzanita.example"}]}


def test_an_application_lists_what_it_speaks():
    assert AppSpec.model_validate({**BASE, "protocols": ["mcp", "pap"], "pap": PAP}).protocols == ["mcp", "pap"]
    assert APP_CATALOGUE["order-desk"].protocols == ["pap"]
    assert APP_CATALOGUE["travel-desk"].protocols == ["pact"]


@pytest.mark.parametrize(
    "spec,why",
    [
        ({"pap": PAP}, "add 'pap' to `protocols`"),
        ({"pact": {"connections": [{"id": "air", "brand": "air.example", "audience": "https://p.example/a2a"}]}},
         "add 'pact' to `protocols`"),
        ({"a2a": {"extensions": [{"uri": "https://ext.example/v1"}]}}, "add 'a2a' to `protocols`"),
        ({"protocols": ["smtp"]}, "no protocol named 'smtp'"),
        ({"protocols": ["mcp", "mcp"]}, "twice"),
        ({"protocols": ["tap"]}, "planned, not shipped"),
    ],
)
def test_an_application_is_refused(spec, why):
    with pytest.raises(ValidationError, match=why):
        AppSpec.model_validate({**BASE, **spec})


def test_a_planned_protocol_is_listed_only_while_the_application_is_not_offered():
    off = {**BASE, "protocols": ["tap"], "enabled": False, "unavailable_because": "Card networks wait on TAP."}
    assert AppSpec.model_validate(off).protocols == ["tap"]
