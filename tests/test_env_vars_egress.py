# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Where a credential is sent: an env-var's ``egress``, and the remote servers' headers.

A runtime engine whose sandbox may hold no secret (Kagent) gives the sandbox a
placeholder and has the credential put in at egress, in one request header, for
named hosts. So a variable says ``egress`` only when that is how it travels.
Tavily is a local process again (26 November 2026): its key is read in that
process, so ``TAVILY_API_KEY`` says no ``egress``.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml

import agentspecs

ROOT = Path(agentspecs.__file__).parent
HOST = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)+$")
HEADER = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$")
PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _specs(kind: str) -> dict[str, dict]:
    return {path.stem: yaml.safe_load(path.read_text()) for path in sorted((ROOT / kind).glob("*.yaml"))}


def _egress() -> dict[str, dict]:
    return {name: spec["egress"] for name, spec in _specs("env-vars").items() if "egress" in spec}


def test_an_egress_names_hosts_a_header_and_a_prefix_and_nothing_else():
    declared = _egress()
    assert declared, "no env-var says where it is sent"
    for name, egress in declared.items():
        assert set(egress) == {"hosts", "header", "prefix"}, name
        assert egress["hosts"] and len(set(egress["hosts"])) == len(egress["hosts"]), name
        for host in egress["hosts"]:
            # A DNS name, lowercase: never `*`, never an address or a URL.
            assert isinstance(host, str) and HOST.match(host), (name, host)
        assert isinstance(egress["header"], str) and HEADER.match(egress["header"]), name
        assert isinstance(egress["prefix"], str), name


def test_the_variables_that_say_where_they_are_sent():
    assert _egress() == {
        "GITHUB_TOKEN": {"hosts": ["api.github.com"], "header": "Authorization", "prefix": "Bearer "},
    }


def test_an_egress_agrees_with_the_remote_server_that_sends_the_variable():
    """One variable, one way out: a remote server that sends a variable with an
    ``egress`` sends it to one of those hosts, in that header, after that prefix."""
    declared = _egress()
    for server_id, server in _specs("mcp-servers").items():
        if not server.get("url") or server.get("command"):
            continue
        host = urlsplit(server["url"]).hostname
        for header, value in (server.get("headers") or {}).items():
            for name in PLACEHOLDER.findall(str(value)):
                if name not in declared:
                    continue
                egress = declared[name]
                assert host in egress["hosts"], (server_id, name)
                assert header.lower() == egress["header"].lower(), (server_id, name)
                assert value == egress["prefix"] + "${" + name + "}", (server_id, name)


def test_a_remote_servers_secret_is_a_headers_whole_value_never_in_its_address():
    for server_id, server in _specs("mcp-servers").items():
        if not server.get("url") or server.get("command"):
            continue
        assert not PLACEHOLDER.findall(server["url"]), server_id
        for header, value in (server.get("headers") or {}).items():
            names = PLACEHOLDER.findall(str(value))
            assert len(names) <= 1, (server_id, header)
            if names:
                assert str(value).endswith("${" + names[0] + "}"), (server_id, header)


def test_tavily_is_a_local_process_reading_its_key_again():
    """The hosted server (0.1.22, 0.1.23) left codemode agents without its tools:
    the entry is ``npx -y tavily-mcp`` over stdio again, as in 0.1.21, the key in
    its environment (the user, 26 November 2026)."""
    tavily = _specs("mcp-servers")["tavily"]
    assert tavily["transport"] == "stdio"
    assert tavily["command"] == "npx"
    assert tavily["args"] == ["-y", "tavily-mcp"]
    assert tavily["env"] == {"TAVILY_API_KEY": "${TAVILY_API_KEY}"}
    assert "url" not in tavily and "headers" not in tavily
    assert tavily["install"]["type"] == "npm"
    assert tavily["envvars"] == ["TAVILY_API_KEY:0.0.1"]
    assert tavily["enabled"] is True
    # Read in a process, so the key travels in no header: it says no egress.
    assert "egress" not in _specs("env-vars")["TAVILY_API_KEY"]


def test_tavily_keeps_the_tools_the_specs_name():
    """The package's tools: what the agents, the applications' rules and the
    action classes say."""
    tavily = _specs("mcp-servers")["tavily"]
    assert tavily["actions"]["tools"] == {
        "tavily_search": "read",
        "tavily_extract": "read",
        "tavily_crawl": "read",
        "tavily_map": "read",
        "tavily_research": "read",
    }
    named = set()
    pattern = re.compile(r"\btavily[._]{1,2}(tavily_[a-z_]+)")
    for kind in ("agents", "apps", "frames", "skills", "teams", "battles"):
        for path in (ROOT / kind).glob("*.yaml"):
            named.update(pattern.findall(path.read_text()))
    assert named <= set(tavily["actions"]["tools"]), named - set(tavily["actions"]["tools"])
