# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Decisions: a kind of the catalogue, and a capability an agent's spec names."""

from pathlib import Path

import pytest
import yaml

from agentspecs.decisions import (
    DECIDE_TOOL,
    DECISIONS_CATALOGUE,
    DecisionsError,
    DecisionsSpec,
    agent_decisions,
    check_decisions,
    get_decisions,
    id_of,
    list_decisions,
)
from agentspecs.models import get_model

ROOT = Path(__file__).resolve().parent.parent / "agentspecs"


def _specs(folder: str):
    for path in sorted((ROOT / folder).glob("*.yaml")):
        yield path.name, yaml.safe_load(path.read_text()) or {}


def test_jev_is_the_shipped_decisions_spec():
    jev = get_decisions("jev:0.0.1")
    assert jev is not None and jev is get_decisions("jev")
    assert jev.enabled
    assert jev.model == "cloudflare:wrk/typesafe/jev"
    assert jev.questions == ["noul", "choice", "score"]
    assert jev.max_questions == 10 and jev.max_text_length == 20000
    assert [spec.id for spec in list_decisions()] == sorted(DECISIONS_CATALOGUE)


def test_every_decisions_spec_asks_a_typed_decision_model_of_the_catalogue():
    for spec in list_decisions():
        model = get_model(spec.model)
        assert model is not None and model.id == spec.model, spec.id
        assert "decisions" in model.capabilities, spec.id


def test_a_model_that_is_unknown_or_answers_no_decisions_is_refused():
    base = {"id": "other", "name": "Other"}
    with pytest.raises(DecisionsError, match="not in the models catalogue"):
        check_decisions(DecisionsSpec(**base, model="nowhere:nothing"))
    with pytest.raises(DecisionsError, match="answers no typed decisions"):
        check_decisions(DecisionsSpec(**base, model="alibaba:qwen-max"))


def test_a_spec_answers_at_least_one_known_question_type_once():
    base = {"id": "other", "name": "Other", "model": "cloudflare:wrk/typesafe/jev"}
    with pytest.raises(ValueError):
        DecisionsSpec(**base, questions=[])
    with pytest.raises(ValueError):
        DecisionsSpec(**base, questions=["noul", "noul"])
    with pytest.raises(ValueError):
        DecisionsSpec(**base, questions=["essay"])
    with pytest.raises(ValueError):
        DecisionsSpec(**base, max_questions=0)


def test_an_agent_decides_only_when_its_spec_names_one():
    assert agent_decisions({"id": "plain", "backend_tools": ["runtime-echo:0.0.1"]}) is None
    named = agent_decisions({"id": "decider", "decisions": "jev:0.0.1"})
    assert named is not None and named.id == "jev"


def test_decide_without_decisions_is_refused_in_a_sentence_naming_the_agent():
    with pytest.raises(DecisionsError) as refused:
        agent_decisions({"id": "sneaky", "backend_tools": ["decide:0.0.1"]})
    assert "'sneaky'" in str(refused.value)
    assert "names no decisions" in str(refused.value)
    assert "decisions: jev:0.0.1" in str(refused.value)


def test_an_unknown_a_mis_versioned_or_a_disabled_spec_is_refused():
    with pytest.raises(DecisionsError, match="does not have"):
        agent_decisions({"id": "a", "decisions": "oracle:0.0.1"})
    with pytest.raises(DecisionsError, match="the catalogue has jev:0.0.1"):
        agent_decisions({"id": "a", "decisions": "jev:9.9.9"})
    off = {"jev": DECISIONS_CATALOGUE["jev"].model_copy(update={"enabled": False})}
    with pytest.raises(DecisionsError, match="not enabled"):
        agent_decisions({"id": "a", "decisions": "jev:0.0.1"}, off)


def test_every_shipped_agent_keeps_the_rule():
    """No agent lists `decide` by hand; those that decide name `decisions`."""
    deciders = []
    for name, agent in _specs("agents"):
        spec = agent_decisions(agent)
        tools = [id_of(tool) for tool in agent.get("backend_tools") or []]
        assert DECIDE_TOOL not in tools, f"{name}: decisions brings `decide`"
        if spec is not None:
            deciders.append(agent["id"])
    assert "example-simple" in deciders


def test_an_application_that_lists_decide_runs_an_agent_that_decides():
    agents = {agent["id"]: agent for _, agent in _specs("agents")}
    seen = 0
    for name, app in _specs("apps"):
        tools = [id_of(tool) for tool in app.get("backend_tools") or []]
        if DECIDE_TOOL not in tools:
            continue
        seen += 1
        agent = agents.get(id_of(app.get("agent") or ""))
        assert agent is not None and agent.get("decisions"), name
    assert seen > 0
