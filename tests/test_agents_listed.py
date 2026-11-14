# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""An agent's `enabled` and `listed`: whether it runs, and whether the pickers offer it.

`enabled: false` says an agent is not offered today: an application naming it has it to
set up. `listed: false` (0.0.187, the user, 14 November 2026) keeps an enabled agent out
of the pickers — the new agent page, the chats, the assign menu, loop's local and cloud
pickers — while it stays runnable by id, the default of blank applications and quick
launches, and the agent of the applications that name it.
"""

from pathlib import Path

import yaml

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agentspecs" / "agents"

#: The agents the pickers offer: the home page's five.
LISTED = {
    "worker-accountant",
    "worker-marketer",
    "worker-shopper",
    "worker-steward-aws",
    "worker-terra",
}


def _agents():
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        yield path.stem, yaml.safe_load(path.read_text()) or {}


def test_listed_is_a_boolean_said_only_to_keep_an_enabled_agent_out():
    for name, agent in _agents():
        if "listed" not in agent:
            continue
        assert agent["listed"] is False, f"{name}: say `listed` only as false, true is the default"
        assert agent.get("enabled", True) is True, f"{name}: a disabled agent is not offered anyway"


def test_the_pickers_offer_the_home_pages_five_agents():
    offered = {
        name
        for name, agent in _agents()
        if agent.get("enabled", True) is True and agent.get("listed", True) is True
    }
    assert offered == LISTED


def test_the_neutral_default_runs_and_is_not_offered():
    agents = dict(_agents())
    for name in (
        "example-simple",
        "example-blank",
        "jupyter-data-analyst",
    ):
        assert agents[name]["enabled"] is True, name
        assert agents[name]["listed"] is False, name
