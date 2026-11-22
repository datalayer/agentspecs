# Copyright (c) 2025-2026 Datalayer, Inc.
# Distributed under the terms of the Modified BSD License.

"""Overture Maps in the catalogue (the user, 19 November 2026).

The gateway's `overture` toolset as its own server, its three tools classed
read under it and under `datalayer` (the gateway's table), the Traveller
holding it always with show_trip_map, and the map plugin both bring.
"""

from __future__ import annotations

import yaml

from agentspecs.actions import classes_of, connection_tool_classes, server_specs

from agentspecs.mcp_servers import MCP_SERVERS_DIR

from pathlib import Path

ROOT = Path(MCP_SERVERS_DIR).parent
TOOLS = ("overture_search_places", "overture_place_details", "overture_place_categories")


def _spec(kind: str, name: str) -> dict:
    return yaml.safe_load((ROOT / kind / f"{name}.yaml").read_text())


def test_the_server_is_the_gateways_overture_toolset() -> None:
    server = server_specs()["overture"]
    assert server["url"] == "https://mcp.datalayer.run/mcp?only=overture"
    assert server["transport"] == "streamable-http"
    assert server["headers"] == {"Authorization": "Bearer ${DATALAYER_API_KEY}"}
    assert [ref.split(":")[0] for ref in server["envvars"]] == ["DATALAYER_API_KEY"]
    assert server["documentation_url"] == "https://datalayer.ai/docs/mcp/toolsets"
    assert "OpenStreetMap contributors, Overture Maps Foundation" in server["setup"]
    assert [ui["plugin"] for ui in server["ui"]] == ["trip-map"]


def test_its_tools_only_read_as_a_connection_and_on_the_gateway() -> None:
    for tool in TOOLS:
        assert [str(getattr(c, "value", c)) for c in connection_tool_classes("overture", tool)] == ["read"]
        assert [str(getattr(c, "value", c)) for c in classes_of(f"datalayer.{tool}")] == ["read"]
    assert set(server_specs()["overture"]["actions"]["tools"]) == set(TOOLS)


def test_the_traveller_holds_it_optional_with_its_map() -> None:
    # Optional since 22 November 2026 (the user: "make the overture mcp server optional for traveller, we
    # need to show traveller for anonymous visitors"): the Traveller starts without the gateway's key.
    agent = _spec("agents", "worker-traveller")
    assert "overture:0.0.1" in agent["mcp_servers"]
    assert "overture:0.0.1" in agent["optional"]["mcp_servers"]
    assert "show-trip-map:0.0.1" in agent["backend_tools"]
    prompt = agent["system_prompt"]
    assert "overture_search_places" in prompt and "show_trip_map" in prompt
    # Overture for places, Google Maps for travel times when the person has a key.
    assert "travel times" in prompt and "when the person has a key" in prompt


def test_the_map_card_and_its_plugin() -> None:
    tool = _spec("backend-tools", "show-trip-map")
    assert tool["runtime"] == {"language": "python", "package": "agent_runtimes.tools.cards", "method": "show_trip_map"}
    assert tool["action"] == "read"
    assert [ui["plugin"] for ui in tool["ui"]] == ["trip-map"]
    plugin = _spec("ui", "trip-map")
    assert plugin["plugin"] == "@datalayer/agent-plugin-trip-map"
    assert plugin["folder"] == "trip-map"
