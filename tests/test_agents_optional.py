# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""An agent's `optional`: the MCP servers and skills it starts without (0.0.188).

The user, 14 November 2026: Start is allowed without Terra's Earthdata login, with one
network at least for the Marketer, and without web search and the repositories for the
Marketer and the Shopper; the agent says what it cannot do. An optional entry names one
of the agent's own servers or skills; a group (`at_least_one`) names optional entries.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent / "agentspecs"
AGENTS_DIR = ROOT / "agents"


def _base(ref: str) -> str:
    return str(ref).split(":")[0]


def _agents():
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        yield path.stem, yaml.safe_load(path.read_text()) or {}


def test_optional_names_the_agents_own_servers_and_skills():
    for name, agent in _agents():
        optional = agent.get("optional")
        if optional is None:
            continue
        assert set(optional) <= {"mcp_servers", "skills", "backend_tools", "at_least_one"}, name
        servers = {str(ref) for ref in agent.get("mcp_servers") or []}
        skills = {str(ref) for ref in agent.get("skills") or []}
        tools = {str(ref) for ref in agent.get("backend_tools") or []}
        for ref in optional.get("mcp_servers") or []:
            assert ref in servers, f"{name}: optional MCP server {ref} is not among its mcp_servers"
        for ref in optional.get("skills") or []:
            assert ref in skills, f"{name}: optional skill {ref} is not among its skills"
        for ref in optional.get("backend_tools") or []:
            assert ref in tools, f"{name}: optional backend tool {ref} is not among its backend_tools"
            spec = yaml.safe_load((ROOT / "backend-tools" / f"{_base(ref)}.yaml").read_text())
            assert spec.get("linked_accounts"), f"{name}: an optional backend tool is set up by a linked account"
        entries = (
            list(optional.get("mcp_servers") or [])
            + list(optional.get("skills") or [])
            + list(optional.get("backend_tools") or [])
        )
        for group in optional.get("at_least_one") or []:
            assert isinstance(group, list) and len(group) >= 2, f"{name}: a group names two entries or more"
            for ref in group:
                assert entries.count(ref) == 1, f"{name}: {ref} in a group names one optional entry"


def test_the_marketer_needs_one_network_and_neither_search_nor_the_repositories():
    agents = dict(_agents())
    marketer = agents["worker-marketer"]["optional"]
    assert marketer["mcp_servers"] == ["x:0.0.1", "bluesky:0.0.1", "discord:0.0.1"]
    assert marketer["skills"] == ["crawl:0.0.1", "github:0.0.1"]
    assert marketer["backend_tools"] == ["social-post-x:0.0.1", "social-post-bluesky:0.0.1"]
    assert marketer["at_least_one"] == [
        ["x:0.0.1", "bluesky:0.0.1", "discord:0.0.1", "social-post-x:0.0.1", "social-post-bluesky:0.0.1"]
    ]
    assert agents["worker-shopper"]["optional"] == {"skills": ["crawl:0.0.1"]}


def test_the_skills_said_optional_are_the_ones_reading_tavily_and_github():
    for skill, name in (("crawl", "TAVILY_API_KEY:0.0.1"), ("github", "GITHUB_TOKEN:0.0.1")):
        spec = yaml.safe_load((ROOT / "skills" / f"{skill}.yaml").read_text())
        assert name in spec["envvars"]


def test_terras_earthdata_login_is_never_required():
    earthdata = yaml.safe_load((ROOT / "mcp-servers" / "earthdata.yaml").read_text())
    assert "EARTHDATA_USERNAME:0.0.1" in earthdata["sandbox_envvars"]
    assert not any(_base(ref).startswith("EARTHDATA_") for ref in earthdata["envvars"])


def test_the_marketer_has_no_linkedin_and_the_server_stays():
    agents = dict(_agents())
    marketer = agents["worker-marketer"]
    assert "linkedin:0.0.1" not in marketer["mcp_servers"]
    for field in ("description", "system_prompt", "goal"):
        assert "LinkedIn" not in str(marketer.get(field) or ""), field
    for app in ("marketer", "demo-marketer"):
        text = (ROOT / "apps" / f"{app}.yaml").read_text()
        spec = yaml.safe_load(text)
        assert "linkedin:0.0.1" not in [c.get("server") for c in spec.get("connections") or []]
        for field in ("description", "goal", "instructions", "interface"):
            assert "LinkedIn" not in str(spec.get(field) or ""), (app, field)
    assert (ROOT / "mcp-servers" / "linkedin.yaml").exists()


def test_the_marketer_posts_through_the_linked_accounts_and_asks_first():
    """datalayer-social (0.0.189): no pasted secret, a linked account, every post approved."""
    marketer = dict(_agents())["worker-marketer"]
    for ref in ("social-accounts:0.0.1", "social-post-x:0.0.1", "social-post-bluesky:0.0.1"):
        assert ref in marketer["backend_tools"]
    for tool, account in (("social-post-x", "x"), ("social-post-bluesky", "bluesky")):
        spec = yaml.safe_load((ROOT / "backend-tools" / f"{tool}.yaml").read_text())
        assert spec["action"] == "publish" and spec["approval"] == "manual"
        assert spec["linked_accounts"] == [account]
        assert "envvars" not in spec
    accounts = yaml.safe_load((ROOT / "backend-tools" / "social-accounts.yaml").read_text())
    assert accounts["action"] == "read" and "linked_accounts" not in accounts


def test_the_marketer_application_needs_one_network_as_its_agent_does():
    from agentspecs.apps import app_problems, parse_app

    spec = yaml.safe_load((ROOT / "apps" / "marketer.yaml").read_text())
    assert [(c["server"], c.get("optional")) for c in spec["connections"]] == [
        ("x:0.0.1", True),
        ("bluesky:0.0.1", True),
        ("discord:0.0.1", True),
    ]
    assert app_problems(parse_app(spec)) == []
    # Only a server its agent says optional may be.
    spec["agent"] = "worker-shopper:0.0.1"
    assert any("is optional, and its agent does not start without it" in p for p in app_problems(parse_app(spec)))
