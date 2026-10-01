# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The model catalogue: typed, and checked when it loads."""

import pytest

from agentspecs.models import (
    AI_MODEL_CATALOGUE,
    MODEL_CAPABILITIES,
    MODEL_ROUTES,
    AIModel,
    get_model,
)


def test_every_spec_keeps_to_the_vocabulary():
    for model in AI_MODEL_CATALOGUE:
        assert set(model.capabilities) <= set(MODEL_CAPABILITIES), model.id
        assert model.route is None or model.route in MODEL_ROUTES, model.id


def test_a_cloudflare_id_carries_its_flavour():
    """`cloudflare:wrk/…` is Workers AI, `cloudflare:gtw/…` is AI Gateway: the id, the
    file and the route agree, so a reader tells the two apart at a glance."""
    for model in AI_MODEL_CATALOGUE:
        if model.provider != "cloudflare":
            continue
        flavour = model.id.split(":", 1)[1].split("/", 1)[0]
        assert (flavour, model.route) in {("wrk", "workers-ai"), ("gtw", "ai-gateway")}, model.id


def test_jev_is_a_judgment_model_once_per_route():
    gateway = get_model("cloudflare:gtw/typesafe/jev")
    workers = get_model("cloudflare:wrk/typesafe/jev")
    for jev in (gateway, workers):
        assert jev is not None
        assert jev.capabilities == ["judgments"]
        assert jev.billing == "credits"
        assert jev.context_window == 32000
        assert jev.zero_data_retention is True
        assert jev.pricing is not None and jev.pricing.input_usd_per_million == 0.042
    assert gateway.route == "ai-gateway" and workers.route == "workers-ai"


def test_the_judges_are_chat_models():
    judges = [m for m in AI_MODEL_CATALOGUE if "judge" in m.capabilities]
    assert {m.id for m in judges} == {"cloudflare:wrk/openai/gpt-oss-120b", "bedrock:us.anthropic.claude-sonnet-4-6"}
    assert all("chat" in m.capabilities for m in judges)


def test_a_chat_picker_leaves_the_judgment_models_out():
    chat = [m for m in AI_MODEL_CATALOGUE if "chat" in m.capabilities]
    assert not any("judgments" in m.capabilities for m in chat)


def test_an_unknown_capability_or_route_is_refused_when_the_catalogue_loads(tmp_path):
    from agentspecs.models import _load_model_specs

    (tmp_path / "x.yaml").write_text(
        'id: "x:y"\nversion: 0.0.1\nname: y\nprovider: x\ncapabilities: [chat, telepathy]\n'
    )
    with pytest.raises(ValueError, match="telepathy"):
        _load_model_specs(tmp_path)
    (tmp_path / "x.yaml").write_text('id: "x:y"\nversion: 0.0.1\nname: y\nprovider: x\nroute: tunnel\n')
    with pytest.raises(ValueError, match="tunnel"):
        _load_model_specs(tmp_path)
