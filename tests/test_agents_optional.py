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
    assert marketer["mcp_servers"] == [
        "discord:0.0.1",
        "linkedin:0.0.1",
    ]
    assert marketer["skills"] == [
        "github:0.0.1",
        "datalayer-email:0.0.1",
        "image-stock:0.0.1",
    ]
    assert marketer["backend_tools"] == [
        "social-post-x:0.0.1",
        "social-read-x:0.0.1",
        "social-reply-x:0.0.1",
        "social-like-x:0.0.1",
        "social-repost-x:0.0.1",
        "social-post-bluesky:0.0.1",
        "social-read-bluesky:0.0.1",
        "social-reply-bluesky:0.0.1",
        "social-like-bluesky:0.0.1",
        "social-repost-bluesky:0.0.1",
        "social-follow-bluesky:0.0.1",
        "social-post-linkedin:0.0.1",
        "social-comment-linkedin:0.0.1",
    ]
    assert marketer["at_least_one"] == [
        [
            "discord:0.0.1",
            "linkedin:0.0.1",
            "social-post-x:0.0.1",
            "social-post-bluesky:0.0.1",
            "social-post-linkedin:0.0.1",
        ]
    ]
    # Crawling asks no key (25 November 2026): nothing of the Shopper's is optional.
    assert "optional" not in agents["worker-shopper"]
    assert "crawl:0.0.1" in agents["worker-shopper"]["skills"]


def test_the_skill_said_optional_is_the_one_reading_github():
    spec = yaml.safe_load((ROOT / "skills" / "github.yaml").read_text())
    assert "GITHUB_TOKEN:0.0.1" in spec["envvars"]


def test_crawl_asks_no_key_and_no_agent_calls_it_optional():
    """The crawl skill fetches pages itself and reads no key (the user, 25 November 2026: "Drop it").

    Its scripts (datalayer-skills) never read TAVILY_API_KEY: web search is the
    tavily MCP server's, which declares the key itself. So the skill declares no
    variable, and an agent that carries it does not list it as something it may
    start without: nothing can be missing.
    """
    crawl = yaml.safe_load((ROOT / "skills" / "crawl.yaml").read_text())
    assert crawl["envvars"] == []
    assert not crawl.get("optional_env_vars")
    carrying = [name for name, agent in _agents() if "crawl:0.0.1" in (agent.get("skills") or [])]
    assert {"worker-marketer", "worker-shopper", "worker-traveller"} <= set(carrying)
    for name, agent in _agents():
        assert "crawl:0.0.1" not in ((agent.get("optional") or {}).get("skills") or []), name


def test_an_agent_that_searches_with_tavily_declares_the_server_that_reads_the_key():
    """Nothing relied on crawl to bring TAVILY_API_KEY in: an agent that names the key names the tavily server."""
    tavily = yaml.safe_load((ROOT / "mcp-servers" / "tavily.yaml").read_text())
    assert "TAVILY_API_KEY:0.0.1" in tavily["envvars"]
    for name, agent in _agents():
        if "TAVILY_API_KEY:0.0.1" in (agent.get("envvars") or []):
            assert "tavily:0.0.1" in (agent.get("mcp_servers") or []), name


def test_every_agent_that_names_tavily_may_start_without_it():
    """Tavily is a local process reading TAVILY_API_KEY (the user, 26 November 2026:
    "make it optional, so agent can launch on kagent without tavily").

    Every agent that names the server lists it optional: started whenever the key
    is there, left out without it or on an engine whose sandbox holds no secret.
    """
    naming = [name for name, agent in _agents() if "tavily:0.0.1" in (agent.get("mcp_servers") or [])]
    assert len(naming) == 37
    assert {"worker-crawler", "example-codemode", "example-no-codemode", "example-mcp"} <= set(naming)
    for name, agent in _agents():
        if "tavily:0.0.1" in (agent.get("mcp_servers") or []):
            assert "tavily:0.0.1" in ((agent.get("optional") or {}).get("mcp_servers") or []), name


def test_terras_earthdata_login_is_never_required():
    earthdata = yaml.safe_load((ROOT / "mcp-servers" / "earthdata.yaml").read_text())
    assert "EARTHDATA_USERNAME:0.0.1" in earthdata["sandbox_envvars"]
    assert not any(_base(ref).startswith("EARTHDATA_") for ref in earthdata["envvars"])


def test_linkedin_through_iam_and_its_browser_server():
    """LinkedIn through datalayer-social (14 November 2026) and the linkedin server (15 November).

    The Marketer posts and comments through IAM with the person's linked
    account; with the linkedin server, on a browser session the person signs in
    from the chat, it reads LinkedIn too. Both optional, in its one-network group.
    """
    agents = dict(_agents())
    marketer = agents["worker-marketer"]
    assert "linkedin:0.0.1" in marketer["mcp_servers"]
    assert "linkedin:0.0.1" in marketer["optional"]["mcp_servers"]
    assert "linkedin:0.0.1" in marketer["optional"]["at_least_one"][0]
    prompt = " ".join(marketer["system_prompt"].split())
    assert "LinkedIn" in marketer["description"]
    assert "Sign in to LinkedIn" in prompt and "read nothing back" in prompt
    for ref in ("social-post-linkedin:0.0.1", "social-comment-linkedin:0.0.1"):
        assert ref in marketer["backend_tools"] and ref in marketer["optional"]["backend_tools"]
    assert "social-post-linkedin:0.0.1" in marketer["optional"]["at_least_one"][0]
    for app in ("marketer", "demo-marketer"):
        spec = yaml.safe_load((ROOT / "apps" / f"{app}.yaml").read_text())
        assert "linkedin:0.0.1" not in [c.get("server") for c in spec.get("connections") or []]
        assert "LinkedIn" in spec["description"], app
    linkedin = yaml.safe_load((ROOT / "mcp-servers" / "linkedin.yaml").read_text())
    assert linkedin["envvars"] == []
    assert "Sign in to LinkedIn" in linkedin["setup"]
    # The person's own session, pasted in Settings › LinkedIn (15 November 2026):
    # given when the account has it, never required.
    assert linkedin["optional_envvars"] == ["LINKEDIN_LI_AT:0.0.1"]
    assert "Settings › LinkedIn" in linkedin["setup"]
    assert "Settings › LinkedIn" in prompt


def test_the_linkedin_session_cookie_says_which_cookie_to_copy():
    """LINKEDIN_LI_AT (the user, 15 November 2026): the cookie named, the others not, the steps."""
    spec = yaml.safe_load((ROOT / "env-vars" / "LINKEDIN_LI_AT.yaml").read_text())
    assert spec["id"] == "LINKEDIN_LI_AT"
    assert spec["name"] == "LinkedIn session cookie (li_at)"
    said = " ".join(spec["description"].split())
    assert "`li_at`" in said and "AQED" in said
    for other in ("JSESSIONID", "bcookie", "bscookie", "liap", "lidc"):
        assert other in said
    for step in ("Chrome or Edge", "Application › Storage › Cookies", "Firefox", "Storage › Cookies", "Value"):
        assert step in said
    assert "sign out" in said and "about a year" in said and "password" in said
    assert spec["registrationUrl"] == "https://www.linkedin.com"


def test_the_marketer_posts_through_the_linked_accounts_and_asks_first():
    """datalayer-social (0.0.189): no pasted secret, a linked account, every post approved."""
    marketer = dict(_agents())["worker-marketer"]
    for ref in (
        "social-accounts:0.0.1",
        "social-post-x:0.0.1",
        "social-post-bluesky:0.0.1",
        "social-post-linkedin:0.0.1",
        "social-comment-linkedin:0.0.1",
    ):
        assert ref in marketer["backend_tools"]
    for tool, account in (
        ("social-post-x", "x"),
        ("social-post-bluesky", "bluesky"),
        ("social-post-linkedin", "linkedin"),
        ("social-comment-linkedin", "linkedin"),
    ):
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
        ("discord:0.0.1", True),
    ]
    assert app_problems(parse_app(spec)) == []
    # Only a server its agent says optional may be.
    spec["agent"] = "worker-shopper:0.0.1"
    assert any("is optional, and its agent does not start without it" in p for p in app_problems(parse_app(spec)))


def test_the_marketer_does_everything_on_bluesky_with_the_linked_account():
    """15 November 2026: Bluesky read and acted on through IAM, no app password; the server stays in the catalogue."""
    marketer = dict(_agents())["worker-marketer"]
    servers = [_base(ref) for ref in marketer["mcp_servers"]]
    assert "bluesky" not in servers
    assert "bluesky:0.0.1" not in [c.get("server") for c in yaml.safe_load((ROOT / "apps" / "marketer.yaml").read_text())["connections"]]
    assert (ROOT / "mcp-servers" / "bluesky.yaml").exists()
    for tool, action, approval in (
        ("social-read-bluesky", "read", "auto"),
        ("social-reply-bluesky", "publish", "manual"),
        ("social-like-bluesky", "write", "manual"),
        ("social-repost-bluesky", "publish", "manual"),
        ("social-follow-bluesky", "write", "manual"),
    ):
        assert f"{tool}:0.0.1" in marketer["backend_tools"]
        assert f"{tool}:0.0.1" in marketer["optional"]["backend_tools"]
        spec = yaml.safe_load((ROOT / "backend-tools" / f"{tool}.yaml").read_text())
        assert (spec["action"], spec["approval"]) == (action, approval), tool
        assert spec["linked_accounts"] == ["bluesky"] and "envvars" not in spec
        assert spec["runtime"]["package"] == "agent_runtimes.tools.social"
    assert "read_bluesky" in marketer["system_prompt"]


def test_the_marketer_reads_and_acts_on_x_with_the_linked_account_within_a_budget():
    """15 November 2026: X read and acted on through IAM, no X_BEARER_TOKEN; what X costs held by the x-api-budget guardrail."""
    marketer = dict(_agents())["worker-marketer"]
    assert "x" not in [_base(ref) for ref in marketer["mcp_servers"]]
    assert "x:0.0.1" not in [c.get("server") for c in yaml.safe_load((ROOT / "apps" / "marketer.yaml").read_text())["connections"]]
    assert (ROOT / "mcp-servers" / "x.yaml").exists()
    for tool, action, approval in (
        ("social-read-x", "read", "auto"),
        ("social-reply-x", "publish", "manual"),
        ("social-like-x", "write", "manual"),
        ("social-repost-x", "publish", "manual"),
    ):
        assert f"{tool}:0.0.1" in marketer["backend_tools"]
        assert f"{tool}:0.0.1" in marketer["optional"]["backend_tools"]
        spec = yaml.safe_load((ROOT / "backend-tools" / f"{tool}.yaml").read_text())
        assert (spec["action"], spec["approval"]) == (action, approval), tool
        assert spec["linked_accounts"] == ["x"] and "envvars" not in spec
        assert spec["runtime"]["package"] == "agent_runtimes.tools.social"
    (budget,) = [entry["api_budget"] for entry in marketer["guardrails"] if "api_budget" in entry]
    assert budget["id"] == "x-api-budget" and budget["provider"] == "X" and budget["currency"] == "USD"
    # X's pay-per-use prices (docs.x.com/x-api/getting-started/pricing, November 2026).
    assert budget["prices"] == {
        "post_read": 0.005,
        "user_read": 0.010,
        "owned_read": 0.001,
        "create_post": 0.015,
        "create_post_with_url": 0.200,
    }
    assert budget["budgets"] == {"per_person_daily": 0.5, "per_person_monthly": 5.0, "platform_monthly": 100.0}
    assert budget["results"]["most"] == 20
    # Every X tool the Marketer carries is priced, each in a unit of the table.
    x_tools = {"read_x", "post_to_x", "reply_on_x", "like_on_x", "repost_on_x"}
    assert set(budget["tools"]) == x_tools
    units = {rule.get("unit") for rule in budget["tools"].values()} | {
        read["unit"] for read in budget["tools"]["read_x"]["reads"].values()
    }
    assert units - {None} <= set(budget["prices"])
    assert "X_BEARER_TOKEN" not in yaml.safe_dump(marketer["optional"]) and "read_x" in marketer["system_prompt"]


def test_the_traveller_plans_with_kiwi_and_starts_without_booking_and_maps():
    """The Traveller (the user, 15 November 2026): Kiwi.com anonymous, Booking.com and Google Maps the person's own."""
    traveller = dict(_agents())["worker-traveller"]
    # Overture Maps (19 November 2026): the gateway's open places. Optional since 22 November 2026 (the
    # gateway takes a DATALAYER_API_KEY), so that an anonymous visitor is shown the Traveller.
    assert traveller["mcp_servers"] == ["kiwi:0.0.1", "overture:0.0.1", "booking-com:0.0.1", "google-maps:0.0.1"]
    assert traveller["optional"] == {
        "mcp_servers": ["overture:0.0.1", "booking-com:0.0.1", "google-maps:0.0.1"],
    }
    assert "could not check restaurants and sights" in " ".join(traveller["system_prompt"].split())
    for skill in ("travel-planning:0.0.1", "fare-and-stay-comparison:0.0.1", "dining:0.0.1"):
        assert skill in traveller["skills"]
        spec = yaml.safe_load((ROOT / "skills" / f"{_base(skill)}.yaml").read_text())
        assert spec["enabled"] is True and spec["module"].startswith("datalayer_skills.skills.")
    servers = {
        name: yaml.safe_load((ROOT / "mcp-servers" / f"{name}.yaml").read_text())
        for name in ("kiwi", "booking-com", "google-maps")
    }
    assert servers["kiwi"]["envvars"] == [] and servers["kiwi"]["headers"] == {}
    assert servers["kiwi"]["actions"]["tools"]["search-flight"] == "read"
    assert servers["google-maps"]["envvars"] == ["GOOGLE_MAPS_API_KEY:0.0.1"]
    assert servers["booking-com"]["envvars"] == ["BOOKING_AFFILIATE_ID:0.0.1", "BOOKING_DEMAND_API_KEY:0.0.1"]
    for name in ("GOOGLE_MAPS_API_KEY", "BOOKING_AFFILIATE_ID", "BOOKING_DEMAND_API_KEY"):
        assert (ROOT / "env-vars" / f"{name}.yaml").exists(), name
    prompt = " ".join(traveller["system_prompt"].split())
    assert "You book nothing and pay nothing" in prompt and "can change" in prompt


def test_the_marketer_mails_the_person_alone_through_datalayer():
    """15 November 2026: datalayer-skills' email skill, optional for the Marketer; no address, no mail credential."""
    marketer = dict(_agents())["worker-marketer"]
    assert "datalayer-email:0.0.1" in marketer["skills"]
    assert "datalayer-email:0.0.1" in marketer["optional"]["skills"]
    spec = yaml.safe_load((ROOT / "skills" / "datalayer-email.yaml").read_text())
    assert spec["module"] == "datalayer_skills.skills.email"
    assert spec["dependencies"] == ["datalayer-skills>=0.6.0"]
    assert "envvars" not in spec
    assert "datalayer-email" in marketer["system_prompt"] and "to\n  them alone" not in marketer["system_prompt"]


def test_the_marketer_finds_stock_pictures_when_the_person_has_a_key():
    """18 November 2026: datalayer-skills' image-stock, optional for the Marketer; no key is required, one is enough."""
    marketer = dict(_agents())["worker-marketer"]
    assert "image-stock:0.0.1" in marketer["skills"]
    assert "image-stock:0.0.1" in marketer["optional"]["skills"]
    assert "image-stock" in marketer["system_prompt"] and "credit line" in marketer["system_prompt"]
    spec = yaml.safe_load((ROOT / "skills" / "image-stock.yaml").read_text())
    assert spec["module"] == "datalayer_skills.skills.image_stock"
    assert spec["dependencies"] == ["datalayer-skills>=0.7.0"]
    assert spec["enabled"] is True
    assert "envvars" not in spec
    keys = [
        "UNSPLASH_ACCESS_KEY:0.0.1",
        "PEXELS_API_KEY:0.0.1",
        "PIXABAY_API_KEY:0.0.1",
        "FREEPIK_API_KEY:0.0.1",
    ]
    assert spec["any_of_env_vars"] == keys
    assert spec["optional_env_vars"] == [*keys, "UNSPLASH_TIER:0.0.1"]
    # What activates it is among what it is given, and each is a declared env var.
    assert set(spec["any_of_env_vars"]) <= set(spec["optional_env_vars"])
    for ref in spec["optional_env_vars"]:
        name, version = ref.split(":")
        declared = yaml.safe_load((ROOT / "env-vars" / f"{name}.yaml").read_text())
        assert (declared["id"], declared["version"]) == (name, version)
    # Only the Marketer carries it: its firewall opens the web, the others' name their hosts.
    carriers = [name for name, agent in _agents() if "image-stock:0.0.1" in (agent.get("skills") or [])]
    assert carriers == ["worker-marketer"]
