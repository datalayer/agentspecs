# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""An agent's ``policy``: its ``shield`` section, the firewall's rules in agent-shield's schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from agentspecs import policies

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agentspecs" / "agents"


def _agents():
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        yield path.name, yaml.safe_load(path.read_text()) or {}


def test_every_agents_policy_holds():
    for name, agent in _agents():
        if "policy" in agent:
            assert policies.agent_policy_problems(agent["policy"]) == [], name


#: Agents that name the exact hosts they reach instead of ``*`` (the user, 15 November 2026: the
#: Accountant and Terra join the Steward).
EXACT_EGRESS = {"worker-steward-aws.yaml", "worker-accountant.yaml", "worker-terra.yaml"}
#: Agents that reach the web only: any public address on 80 and 443 (the user, 15 November 2026).
WEB_EGRESS = {"worker-marketer.yaml", "worker-shopper.yaml", "worker-traveller.yaml"}


def test_datalayers_catalogue_agents_reach_any_public_address():
    """Decided by the user, 8 November 2026: our agents allow * for egress.

    Except those of ``EXACT_EGRESS``, which name every host they reach.
    """
    names = []
    for name, agent in _agents():
        if name in EXACT_EGRESS or name in WEB_EGRESS:
            continue
        assert agent.get("policy", {}).get("shield", {}).get("egress") == ["*"], name
        names.append(name)
    assert len(names) > 100


def test_the_marketer_shopper_and_traveller_reach_the_web_only():
    for name in sorted(WEB_EGRESS):
        agent = yaml.safe_load((AGENTS_DIR / name).read_text())
        assert agent["policy"]["shield"]["egress"] == ["*:80", "*:443"], name


@pytest.mark.parametrize("name", sorted(EXACT_EGRESS))
def test_an_exact_egress_agent_names_hosts_on_443_and_no_wildcard(name):
    egress = yaml.safe_load((AGENTS_DIR / name).read_text())["policy"]["shield"]["egress"]
    assert egress and not any("*" in entry for entry in egress), egress
    assert all(entry.endswith(":443") for entry in egress), egress
    assert {"r1.datalayer.run:443", "prod1.datalayer.run:443"} <= set(egress)
    # The tokenizer file every runtime fetches (the user, 15 November 2026).
    assert "openaipublic.blob.core.windows.net:443" in egress


def test_the_accountant_reaches_its_odoo_through_the_gateway_and_terra_nasa():
    accountant = yaml.safe_load((AGENTS_DIR / "worker-accountant.yaml").read_text())["policy"]["shield"]["egress"]
    assert "mcp.datalayer.run:443" in accountant
    assert not any("odoo" in entry for entry in accountant)
    terra = yaml.safe_load((AGENTS_DIR / "worker-terra.yaml").read_text())["policy"]["shield"]["egress"]
    assert {
        "mcp.datalayer.run:443",
        "urs.earthdata.nasa.gov:443",
        "cmr.earthdata.nasa.gov:443",
        "data.lpdaac.earthdatacloud.nasa.gov:443",
    } <= set(terra)


def test_the_steward_names_each_host_it_reaches():
    """No ``*``: AWS's endpoints its tools call, by region, and Datalayer's own."""
    agent = yaml.safe_load((AGENTS_DIR / "worker-steward-aws.yaml").read_text())
    egress = agent["policy"]["shield"]["egress"]
    assert egress and not any("*" in entry for entry in egress), egress
    assert policies.agent_policy_problems(agent["policy"]) == []
    hosts = {entry.rsplit(":", 1)[0] for entry in egress}
    assert {"ce.us-east-1.amazonaws.com", "cost-optimization-hub.us-east-1.amazonaws.com"} <= hosts
    for region in ("us-east-1", "eu-west-1", "ap-southeast-2"):
        assert {f"sts.{region}.amazonaws.com", f"compute-optimizer.{region}.amazonaws.com"} <= hosts
    assert {"r1.datalayer.run", "prod1.datalayer.run"} <= hosts
    assert all(entry.endswith(":443") for entry in egress)


@pytest.mark.parametrize(
    "shield",
    [
        {"egress": ["*"]},
        {"egress": ["*:80", "*:443"]},
        {"egress": ["*:443", "smtp.example.com:587"]},
        {"ingress": ["platform", "*:8765"]},
        {"egress": ["api.tavily.com", "registry.npmjs.org:443", "8.8.8.8", "1.1.1.0/24:53"]},
        {"ingress": ["platform", "10.42.0.0/16:8765"]},
        {},
    ],
)
def test_a_firewall_rule_the_shield_takes(shield):
    assert policies.agent_policy_problems({"shield": shield}) == []


@pytest.mark.parametrize(
    "policy,said",
    [
        ({"shield": {"egress": ["*.example.com"]}}, "addresses, not names"),
        ({"shield": {"egress": ["10.0.0.0/8"]}}, "private or reserved"),
        ({"shield": {"egress": ["169.254.169.254"]}}, "private or reserved"),
        ({"shield": {"egress": ["*", "example.com"]}}, "stands alone"),
        ({"shield": {"egress": ["*", "*:443"]}}, "stands alone"),
        ({"shield": {"egress": ["*:70000"]}}, "between 1 and 65535"),
        ({"shield": {"egress": ["*:443", "*:443"]}}, "named twice"),
        ({"shield": {"egress": ["example.com", "example.com"]}}, "named twice"),
        ({"shield": {"egress": ["platform"]}}, "ingress source"),
        ({"shield": {"egress": ["localhost"]}}, "fully qualified"),
        ({"shield": {"egress": ["example.com:70000"]}}, "between 1 and 65535"),
        ({"shield": {"ingress": ["example.com"]}}, "not a host name"),
        ({"shield": {"fetch": ["example.com"]}}, "Additional properties"),
        ({"network": {}}, "takes shield only"),
        (["shield"], "is a mapping"),
    ],
)
def test_a_firewall_rule_refused_with_its_reason(policy, said):
    problems = policies.agent_policy_problems(policy)
    assert problems and any(said in problem for problem in problems), problems


def test_the_firewall_schema_is_agent_shields_own_verbatim():
    firewall = pytest.importorskip(
        "agent_shield.firewall",
        reason="datalayer-agent-shield is not installed here; CI installs it to hold the copy",
    )
    from agent_shield.__version__ import __version__ as installed

    def parts(version: str) -> tuple[int, ...]:
        return tuple(int(piece) for piece in version.split(".")[:3])

    if parts(installed) < parts(policies.SHIELD_FIREWALL_SCHEMA_SOURCE_VERSION):
        pytest.skip(f"the carried firewall schema is agent-shield {policies.SHIELD_FIREWALL_SCHEMA_SOURCE_VERSION}'s")
    carried = json.loads(policies.SHIELD_FIREWALL_SCHEMA_PATH.read_text())
    assert carried == firewall.firewall_json_schema()
    # And every agent's rules are ones the package's own model takes.
    for name, agent in _agents():
        firewall.rules_of_spec(agent)


def test_agentspecs_and_the_shield_refuse_the_same_ranges():
    model = pytest.importorskip("agent_shield.firewall.model")
    assert tuple(model.NON_PUBLIC) == policies.NON_PUBLIC
