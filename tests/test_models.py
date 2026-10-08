# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The model catalogue: typed, and checked when it loads."""

from pathlib import Path

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


def test_a_cloudflare_id_carries_its_flavour_and_so_does_its_file():
    """`cloudflare:wrk/…` is Workers AI, `cloudflare:gtw/…` is AI Gateway: the id, the
    file and the route agree, so a reader tells the two apart at a glance."""
    import yaml

    models_dir = Path(__file__).resolve().parent.parent / "agentspecs" / "models"
    seen = 0
    for path in sorted(models_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if data["provider"] != "cloudflare":
            assert "route" not in data, path.name
            continue
        flavour = data["id"].split(":", 1)[1].split("/", 1)[0]
        assert (flavour, data["route"]) in {("wrk", "workers-ai"), ("gtw", "ai-gateway")}, path.name
        assert path.name.startswith(f"cloudflare-{flavour}-"), path.name
        seen += 1
    assert seen == 8


def test_the_rules_are_enforced_when_the_catalogue_loads(tmp_path):
    from agentspecs.models import _load_model_specs

    def spec(name, text):
        for stale in tmp_path.glob("*.yaml"):
            stale.unlink()
        (tmp_path / name).write_text(text)
        return _load_model_specs(tmp_path)

    # A non-Cloudflare model carries no route.
    with pytest.raises(ValueError, match="carries none"):
        spec(
            "openai-x.yaml",
            'id: "openai:x"\nversion: 0.0.1\nname: x\nprovider: openai\nroute: workers-ai\n',
        )
    # A Cloudflare id names its flavour…
    with pytest.raises(ValueError, match="cloudflare:<wrk|gtw>"):
        spec(
            "cloudflare-wrk-x.yaml",
            'id: "cloudflare:openai/x"\nversion: 0.0.1\nname: x\nprovider: cloudflare\nroute: workers-ai\n',
        )
    # …which agrees with its route…
    with pytest.raises(ValueError, match="means route"):
        spec(
            "cloudflare-wrk-x.yaml",
            'id: "cloudflare:wrk/openai/x"\nversion: 0.0.1\nname: x\nprovider: cloudflare\nroute: ai-gateway\n',
        )
    # …and with its file's name.
    with pytest.raises(ValueError, match="named cloudflare-gtw"):
        spec(
            "cloudflare-wrk-x.yaml",
            'id: "cloudflare:gtw/openai/x"\nversion: 0.0.1\nname: x\nprovider: cloudflare\nroute: ai-gateway\n',
        )
    assert (
        spec(
            "cloudflare-gtw-x.yaml",
            'id: "cloudflare:gtw/openai/x"\nversion: 0.0.1\nname: x\nprovider: cloudflare\nroute: ai-gateway\n',
        )[0].route
        == "ai-gateway"
    )
    with pytest.raises(ValueError, match="request_logging"):
        spec(
            "cloudflare-gtw-x.yaml",
            'id: "cloudflare:gtw/openai/x"\nversion: 0.0.1\nname: x\nprovider: cloudflare\nroute: ai-gateway\nrequest_logging: diary\n',
        )


def test_a_price_names_both_sides_and_is_never_negative():
    from pydantic import ValidationError

    from agentspecs.models import ModelPricing

    assert (
        ModelPricing(input_usd_per_million=0.042, output_usd_per_million=0.0).output_usd_per_million
        == 0.0
    )
    with pytest.raises(ValidationError):
        ModelPricing(input_usd_per_million=0.042)
    with pytest.raises(ValidationError):
        ModelPricing(input_usd_per_million=-1, output_usd_per_million=0)
    with pytest.raises(ValidationError):
        ModelPricing(input_usd_per_million=float("inf"), output_usd_per_million=0)


def test_an_older_id_still_resolves():
    """The six chat models were `cloudflare:<vendor>/<model>` before 0.0.9 named their
    route: the ids are kept as aliases, so `get_model` and the enum still answer them."""
    from agentspecs.models import AIModels

    spec = get_model("cloudflare:openai/gpt-oss-120b")
    assert spec is not None and spec.id == "cloudflare:wrk/openai/gpt-oss-120b"
    assert AIModels.CLOUDFLARE_OPENAI_GPT_OSS_120B.value == "cloudflare:openai/gpt-oss-120b"
    assert AIModels.CLOUDFLARE_WRK_OPENAI_GPT_OSS_120B.value == "cloudflare:wrk/openai/gpt-oss-120b"
    assert all(
        len(m.aliases) == 1
        for m in AI_MODEL_CATALOGUE
        if m.provider == "cloudflare" and "typesafe" not in m.id
    )


def test_retention_and_route_logging_are_told_apart():
    """Jev keeps nothing; the gateway in front of it keeps request logs. The two
    flavours say so separately, so a route for sensitive data is chosen on both."""
    gateway = get_model("cloudflare:gtw/typesafe/jev")
    workers = get_model("cloudflare:wrk/typesafe/jev")
    assert gateway.zero_data_retention is True and gateway.request_logging == "gateway"
    assert workers.zero_data_retention is True and workers.request_logging == "none"


def test_jev_is_a_decision_model_once_per_route():
    gateway = get_model("cloudflare:gtw/typesafe/jev")
    workers = get_model("cloudflare:wrk/typesafe/jev")
    for jev in (gateway, workers):
        assert jev is not None
        assert jev.capabilities == ["decisions"]
        assert jev.billing == "credits"
        assert jev.context_window == 32000
        assert jev.zero_data_retention is True
        assert jev.pricing is not None and jev.pricing.input_usd_per_million == 0.042
    assert gateway.route == "ai-gateway" and workers.route == "workers-ai"


def test_the_deciders_are_chat_models():
    deciders = [m for m in AI_MODEL_CATALOGUE if "decider" in m.capabilities]
    assert {m.id for m in deciders} == {
        "cloudflare:wrk/openai/gpt-oss-120b",
        "bedrock:us.anthropic.claude-sonnet-4-6",
    }
    assert all("chat" in m.capabilities for m in deciders)


def test_a_chat_picker_leaves_the_decision_models_out():
    chat = [m for m in AI_MODEL_CATALOGUE if "chat" in m.capabilities]
    assert not any("decisions" in m.capabilities for m in chat)


def test_an_unknown_capability_or_route_is_refused_when_the_catalogue_loads(tmp_path):
    from agentspecs.models import _load_model_specs

    (tmp_path / "x.yaml").write_text(
        'id: "x:y"\nversion: 0.0.1\nname: y\nprovider: x\ncapabilities: [chat, telepathy]\n'
    )
    with pytest.raises(ValueError, match="telepathy"):
        _load_model_specs(tmp_path)
    (tmp_path / "x.yaml").write_text(
        'id: "x:y"\nversion: 0.0.1\nname: y\nprovider: x\nroute: tunnel\n'
    )
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
    assert cloudflare.terms_url.startswith("https://") and cloudflare.privacy_url.startswith(
        "https://"
    )
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


def test_every_bedrock_openai_anthropic_and_workers_ai_model_has_a_price():
    """ai-inference meters a call by its model's price: a model it routes with
    no price would be recorded as not priced, and the account not charged."""
    from agentspecs.models import AI_MODEL_CATALOGUE

    routed = ("bedrock:", "anthropic:", "openai:", "cloudflare:wrk/")
    unpriced = [m.id for m in AI_MODEL_CATALOGUE if m.id.startswith(routed) and m.pricing is None]
    assert unpriced == []
