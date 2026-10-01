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


def test_every_model_names_a_provider_the_catalogue_has_and_its_page():
    from agentspecs.model_providers import MODEL_PROVIDER_CATALOGUE, get_model_provider

    known = {provider.id for provider in MODEL_PROVIDER_CATALOGUE}
    for model in AI_MODEL_CATALOGUE:
        assert model.provider in known, model.id
        assert model.provider_url and model.provider_url.startswith("https://"), model.id
    cloudflare = get_model_provider("cloudflare")
    assert cloudflare is not None and cloudflare.hosting == "cloud"
    assert cloudflare.terms_url.startswith("https://") and cloudflare.privacy_url.startswith("https://")
    assert get_model_provider("ollama").hosting == "local"


def test_a_model_naming_an_unknown_provider_is_refused():
    from agentspecs.models import _check_providers

    with pytest.raises(ValueError, match="no spec under model-providers"):
        _check_providers([AIModel(id="x:y", name="y", provider="nowhere")])


def test_a_provider_file_is_named_for_its_id(tmp_path):
    from agentspecs.model_providers import _load_provider_specs

    (tmp_path / "acme.yaml").write_text('id: "acme"\nname: Acme\nhosting: cloud\n')
    assert [p.id for p in _load_provider_specs(tmp_path)] == ["acme"]
    (tmp_path / "other.yaml").write_text('id: "acme"\nname: Acme\n')
    with pytest.raises(ValueError, match="named for id"):
        _load_provider_specs(tmp_path)
    (tmp_path / "other.yaml").write_text('id: "other"\nname: Other\nhosting: orbit\n')
    with pytest.raises(ValueError, match="orbit"):
        _load_provider_specs(tmp_path)
