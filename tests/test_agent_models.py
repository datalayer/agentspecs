# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""An agent's models: its `model` and, optionally, `model_additionals` — the
other models of the catalogue it may be switched to."""

from pathlib import Path

import yaml

from agentspecs.models import get_model

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agentspecs" / "agents"

#: The chat models datalayer-ai-inference serves from the catalogue: the
#: ones its catalogue marks available (`chat_models()`), as of 0.0.25.
AI_INFERENCE_CHAT_MODELS = {
    "bedrock:us.anthropic.claude-sonnet-4-6",
    "alibaba:qwen-max",
}


def _agents():
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        yield path.name, yaml.safe_load(path.read_text()) or {}


def test_an_additional_model_is_a_chat_model_of_the_catalogue():
    """An id the catalogue does not know is refused, and so is a typed-judgment
    model (Jev), which answers typed questions and runs no chat."""
    seen = 0
    for name, agent in _agents():
        additionals = agent.get("model_additionals")
        if additionals is None:
            continue
        seen += 1
        assert isinstance(additionals, list), name
        for model_id in additionals:
            model = get_model(model_id)
            assert model is not None, f"{name}: {model_id} is not in the models catalogue"
            assert model.id == model_id, f"{name}: {model_id} is an alias of {model.id}"
            assert "judgments" not in model.capabilities, f"{name}: {model_id}"
        assert agent.get("model") not in additionals, f"{name}: its own model is not additional"
        assert len(set(additionals)) == len(additionals), name
    assert seen > 0


def test_every_enabled_agent_may_switch_to_what_ai_inference_serves():
    enabled = [(name, agent) for name, agent in _agents() if agent.get("enabled") is True]
    assert enabled
    for name, agent in enabled:
        expected = AI_INFERENCE_CHAT_MODELS - {agent.get("model")}
        assert set(agent.get("model_additionals") or []) == expected, name
