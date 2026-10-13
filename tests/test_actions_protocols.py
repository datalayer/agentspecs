# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Agent protocols' tools classed in the catalogue (AGENT_PROTOCOLS PR-54, PAP_DATALAYER R-02)."""

import pytest

from agentspecs.actions import (
    ActionClass,
    connection_tool_classes,
    protocol_of_connection,
    protocol_tool_classes,
    protocol_tool_names,
    protocol_tool_specs,
    protocol_tools_problems,
)

READ, WRITE, BUY, SEND = ActionClass.READ, ActionClass.WRITE, ActionClass.BUY, ActionClass.SEND


def test_every_protocol_spec_is_sound_and_its_prefix_its_own():
    specs = protocol_tool_specs()
    assert sorted(specs) == ["agentic-commerce", "pact", "pap", "signed-fetch", "ucp"]
    assert [problem for spec in specs.values() for problem in protocol_tools_problems(spec)] == []
    prefixes = [spec["connection"] for spec in specs.values()]
    assert sorted(prefixes) == ["acp", "pact", "pap", "signed-fetch", "ucp"]


@pytest.mark.parametrize(
    "server,tool,classes",
    [
        # A message to the company goes out in the person's name: a Rule decides it (R-02).
        ("pap:manzanita.example", "pap_ask", (SEND,)),
        # Asking for one of the company's people is the conversation's own control, classed with it.
        ("pap:manzanita.example", "pap_handoff", (SEND,)),
        ("pap:manzanita.example", "pap_read", (READ,)),
        ("pap:manzanita.example", "pap_mcp_call", (WRITE,)),
        # Confirming does what an operation can do: the most restricted wins.
        ("pap:manzanita.example", "pap_confirm", (WRITE, BUY)),
        ("pap:manzanita.example", "pap_disconnect", (WRITE,)),
        ("pact:air.example", "pact_ask", (READ,)),
        ("pact:air.example", "pact_ask_for_person", (WRITE,)),
        ("ucp:store.example", "ucp_search", (READ,)),
        ("ucp:store.example", "ucp_complete", (BUY,)),
        ("acp:outfitters.example", "acp_update_checkout", (WRITE,)),
        ("acp:outfitters.example", "acp_complete", (BUY,)),
        # A page read at a site it names, signed (AGENT_PROTOCOLS EX-11): GET only.
        ("signed-fetch:verify.examples.datalayer.run", "signed_fetch", (READ,)),
        # An MCP server of the catalogue, as before.
        ("tavily", "tavily_search", (READ,)),
    ],
)
def test_a_tool_reached_through_a_connection_is_classed(server, tool, classes):
    assert connection_tool_classes(server, tool) == classes


@pytest.mark.parametrize(
    "server,tool",
    [
        ("pap:manzanita.example", "pap_unheard_of"),
        ("pact:air.example", "pap_ask"),
        ("nope:example.com", "pap_ask"),
        ("", "pap_ask"),
    ],
)
def test_unknown_is_unclassed_and_so_the_most_restricted(server, tool):
    assert connection_tool_classes(server, tool) == ()


def test_a_protocol_is_named_by_its_connection_prefix_and_a_domain():
    assert protocol_of_connection("pap:manzanita.example")["id"] == "pap"
    assert protocol_of_connection("acp:outfitters.example")["id"] == "agentic-commerce"
    assert protocol_of_connection("pap") is None
    assert protocol_of_connection("pap:") is None
    assert protocol_of_connection("google-workspace") is None
    assert protocol_tool_classes("pap", "pap_confirm") == (WRITE, BUY)
    assert "pap_confirm" in protocol_tool_names("pap")
    assert protocol_tool_names("nope") == ()


def test_a_spec_without_its_prefix_or_tools_is_refused():
    assert protocol_tools_problems({"id": "x", "actions": {"tools": {"a": "read"}}}) != []
    assert protocol_tools_problems({"id": "x", "connection": "x", "actions": {}}) != []
    assert protocol_tools_problems({"id": "x", "connection": "x", "actions": {"tools": {"a": "sell"}}}) != []
