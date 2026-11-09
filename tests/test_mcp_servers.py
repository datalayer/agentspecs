# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""A remote MCP server whose bearer an identity mints for the run (AC-20)."""

from __future__ import annotations

import pytest
import yaml

from agentspecs.mcp_servers import MCP_SERVERS_DIR, check_mcp_servers, mcp_server_problems


def _gateway(**changes):
    spec = {
        "id": "my-gateway",
        "transport": "streamable-http",
        "url": "https://g-1.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
        "auth": {"kind": "agentcore-gateway", "identity": "aws-agentcore-gateway"},
    }
    spec.update(changes)
    return spec


def test_every_catalogue_server_is_well_authenticated():
    servers = check_mcp_servers()
    assert "agentcore-gateway-example" in servers


def test_the_example_gateway_is_remote_off_and_trusts_the_gateway_identity():
    spec = yaml.safe_load((MCP_SERVERS_DIR / "agentcore-gateway-example.yaml").read_text())
    assert spec["auth"] == {"kind": "agentcore-gateway", "identity": "aws-agentcore-gateway"}
    assert spec["transport"] == "streamable-http" and "command" not in spec
    assert "headers" not in spec
    assert spec["enabled"] is False
    assert mcp_server_problems(spec) == []


def test_a_server_without_auth_has_nothing_to_check():
    assert mcp_server_problems({"id": "hf", "url": "https://huggingface.co/mcp"}) == []


@pytest.mark.parametrize(
    "changes, said",
    [
        (
            {"auth": {"kind": "agentcore-gateway", "identity": "nobody"}},
            "'nobody', which is not an Identity",
        ),
        (
            {"auth": {"kind": "agentcore-gateway", "identity": "datalayer-person"}},
            "issued by aws-agentcore that speaks mcp, and 'datalayer-person' is not one",
        ),
        ({"auth": {"kind": "magic", "identity": "aws-agentcore-gateway"}}, "`auth` is a `kind`"),
        ({"auth": {"kind": "agentcore-gateway"}}, "`auth` is a `kind`"),
        ({"command": "npx"}, "is local (a `command`)"),
        ({"url": "http://g-1.example/mcp"}, "at an https `url`"),
        ({"transport": "stdio"}, "over `transport: streamable-http`"),
        ({"headers": {"Authorization": "Bearer ${X}"}}, "sets no `Authorization` header"),
    ],
)
def test_what_an_agentcore_gateway_server_may_not_be(changes, said):
    problems = mcp_server_problems(_gateway(**changes))
    assert any(said in problem for problem in problems), problems


def test_a_catalogue_with_a_wrong_server_is_refused(tmp_path):
    (tmp_path / "my-gateway.yaml").write_text(
        yaml.safe_dump(_gateway(auth={"kind": "agentcore-gateway", "identity": "nobody"}))
    )
    with pytest.raises(ValueError, match="my-gateway"):
        check_mcp_servers(tmp_path)
