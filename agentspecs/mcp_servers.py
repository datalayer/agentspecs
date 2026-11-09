# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""How a remote MCP server of ``agentspecs/mcp-servers`` is authenticated (AC-20).

A remote server says what it is sent in ``headers`` — a static bearer,
``Authorization: "Bearer ${HF_TOKEN}"``. A server whose bearer is minted for
the run instead says so with ``auth``:

.. code-block:: yaml

    transport: streamable-http
    url: "https://<gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp"
    auth:
      kind: agentcore-gateway
      identity: aws-agentcore-gateway

``agentcore-gateway`` is an Amazon Bedrock AgentCore Gateway: its inbound
authorizer trusts the identity named (an Identity of the catalogue issued by
``aws-agentcore`` and speaking ``mcp``), and the runtime sends, as the bearer,
the inbound token its identity provider obtains for the run — never a token
written in the spec. The server then sets no ``Authorization`` header itself.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .guards import load_raw

#: The ways a remote server's bearer is minted for the run.
MCP_SERVER_AUTH_KINDS: tuple[str, ...] = ("agentcore-gateway",)

#: Where the MCP server specifications are.
MCP_SERVERS_DIR = Path(__file__).parent / "mcp-servers"


class McpServerAuth(BaseModel):
    """The bearer a remote MCP server is sent, minted for the run by an identity."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["agentcore-gateway"] = Field(..., description="Who mints the bearer")
    identity: str = Field(..., description="The Identity of the catalogue the server trusts, by id")


def mcp_server_problems(spec: Mapping[str, Any]) -> list[str]:
    """Return what is wrong with an MCP server specification's authentication, in sentences.

    Parameters
    ----------
    spec : Mapping[str, Any]
        The MCP server specification, as its YAML says it.

    Returns
    -------
    list of str
        One sentence per problem; empty when there is none.
    """
    from .identities import IdentityProvider, get_identity

    raw = spec.get("auth")
    if raw is None:
        return []
    name = spec.get("id", "?")
    try:
        auth = McpServerAuth.model_validate(raw)
    except ValidationError as refused:
        return [
            f"MCP server {name!r}: `auth` is a `kind` (one of {', '.join(MCP_SERVER_AUTH_KINDS)}) "
            f"and an `identity`: {refused.errors()[0]['msg']}"
        ]
    problems: list[str] = []
    if spec.get("command"):
        problems.append(f"MCP server {name!r} is local (a `command`): `auth` is a remote server's")
    if spec.get("transport") != "streamable-http" or not str(spec.get("url") or "").startswith(
        "https://"
    ):
        problems.append(
            f"MCP server {name!r}: an {auth.kind} server is remote, reached over "
            "`transport: streamable-http` at an https `url`"
        )
    if any(str(key).lower() == "authorization" for key in (spec.get("headers") or {})):
        problems.append(
            f"MCP server {name!r}: its bearer is the {auth.kind} identity's, so it sets no "
            "`Authorization` header"
        )
    identity = get_identity(auth.identity)
    if identity is None:
        problems.append(
            f"MCP server {name!r} trusts {auth.identity!r}, "
            "which is not an Identity of the catalogue"
        )
    elif identity.provider is not IdentityProvider.AWS_AGENTCORE or "mcp" not in identity.protocols:
        problems.append(
            f"MCP server {name!r}: an {auth.kind} server trusts an Identity issued by "
            f"aws-agentcore that speaks mcp, and {auth.identity!r} is not one"
        )
    return problems


def load_raw_mcp_servers(directory: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return every MCP server YAML of a directory as plain data, by id."""
    return load_raw(directory or MCP_SERVERS_DIR)


def check_mcp_servers(directory: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return every MCP server of a directory, refused when one's authentication is wrong.

    Raises
    ------
    ValueError
        Naming every problem found.
    """
    servers = load_raw_mcp_servers(directory)
    problems = [problem for spec in servers.values() for problem in mcp_server_problems(spec)]
    if problems:
        raise ValueError("; ".join(problems))
    return servers


__all__ = [
    "MCP_SERVERS_DIR",
    "MCP_SERVER_AUTH_KINDS",
    "McpServerAuth",
    "check_mcp_servers",
    "load_raw_mcp_servers",
    "mcp_server_problems",
]
