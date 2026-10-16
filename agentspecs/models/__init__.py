# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""AI Model specifications.

This module defines the AIModel Pydantic class and helpers for loading
model definitions from YAML specifications.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class ModelPricing(BaseModel):
    """What the provider lists a model at, per million tokens, in dollars.

    Both prices are required: a pricing block that names one and not the
    other would make metered usage look free. An explicit ``0.0`` is a
    price (a model with no output charge); a missing key is not.
    """

    input_usd_per_million: float = Field(..., ge=0, allow_inf_nan=False, description="Dollars per million input tokens")
    output_usd_per_million: float = Field(..., ge=0, allow_inf_nan=False, description="Dollars per million output tokens")


#: What a model can be trusted with. ``decisions`` is a typed-decision model
#: (noul, choice and score questions, answered as probabilities — Jev);
#: ``decider`` is a chat model that may be asked those questions and made to
#: answer in the same shape, whose probabilities are what it says they are.
MODEL_CAPABILITIES = ("chat", "tools", "codemode", "vision", "thinking", "decisions", "decider")

#: Which Cloudflare endpoint a model is asked at — a product, not a kind of
#: model. ``workers-ai``: Workers AI's own endpoint
#: (``api.cloudflare.com/client/v4/accounts/{account}/ai/…``), which serves
#: the models Cloudflare hosts under ``@cf/`` and the third-party ones it
#: fronts (``typesafe/jev``) alike. ``ai-gateway``: through the account's AI
#: Gateway (``gateway.ai.cloudflare.com``), which logs the call and bills it
#: from prepaid credits. A Cloudflare model carries one, in its id
#: (``cloudflare:wrk/…``, ``cloudflare:gtw/…``) and its file name
#: (``cloudflare-wrk-*.yaml``, ``cloudflare-gtw-*.yaml``); a model of any
#: other provider carries none.
MODEL_ROUTES = ("workers-ai", "ai-gateway")
ROUTE_FLAVOURS = {"wrk": "workers-ai", "gtw": "ai-gateway"}

#: Where a route keeps a log of the requests it carries, apart from what
#: the model's provider retains: ``none``, or ``gateway`` (AI Gateway keeps
#: request and response logs for the account). A service choosing a route
#: for sensitive data reads this beside ``zero_data_retention``.
REQUEST_LOGGING = ("none", "gateway")


class AIModel(BaseModel):
    """Specification for an AI model."""

    id: str = Field(..., description="Unique model identifier (e.g., 'anthropic:claude-sonnet-4-5-20250514')")
    name: str = Field(..., description="Display name for the model")
    description: str = Field(default="", description="Model description")
    provider: str = Field(..., description="Provider id (anthropic, openai, bedrock, azure-openai, alibaba, cloudflare, ollama): one of the model-providers specs")
    provider_url: Optional[str] = Field(default=None, description="The page on the provider's website that describes this model")
    default: bool = Field(default=False, description="Whether this is the default model")
    available: bool = Field(
        default=False,
        description="Whether this model is offered to a person choosing one. The catalogue is what the platform knows how to talk to; this is what it is worth offering today. Without the distinction a picker lists twenty-six models, most of them superseded, and the choice becomes a chore rather than a help.",
    )
    required_env_vars: List[str] = Field(default_factory=list, description="Required environment variable names")
    tokens_limit: Optional[int] = Field(default=None, description="Maximum output tokens the model can generate in a single run")
    capabilities: List[str] = Field(default_factory=list, description="What the model can be trusted with: chat, tools, codemode, vision, thinking, decisions, decider")
    billing: Optional[str] = Field(default=None, description="How the provider bills it, when worth telling: 'standard' or 'credits'")
    route: Optional[str] = Field(default=None, description="Which Cloudflare endpoint the model is asked at: 'workers-ai' (Workers AI's own endpoint) or 'ai-gateway' (through the account's AI Gateway). Set on every Cloudflare model, on no other")
    context_window: Optional[int] = Field(default=None, description="The tokens a request may carry, input and output together")
    zero_data_retention: Optional[bool] = Field(default=None, description="Whether the model's provider keeps nothing of a request once it is answered. Says nothing of the route: see request_logging")
    request_logging: Optional[str] = Field(default=None, description="Where the route keeps a log of the requests it carries: 'none', or 'gateway' (AI Gateway's request logs)")
    aliases: List[str] = Field(default_factory=list, description="Older ids this spec answers to, kept so a consumer that named the model before its id moved still finds it (get_model, the AIModels enum)")
    pricing: Optional[ModelPricing] = Field(default=None, description="The provider's list price per million tokens, when a service meters by it")


def _load_model_specs(models_dir: Optional[Path] = None) -> List[AIModel]:
    """Load all model YAML specifications from the models directory."""
    models_dir = models_dir or Path(__file__).parent
    specs = []
    for yaml_file in sorted(models_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            spec = AIModel(**data)
            unknown = [c for c in spec.capabilities if c not in MODEL_CAPABILITIES]
            if unknown:
                raise ValueError(f"{yaml_file.name}: unknown capabilities {unknown}; the vocabulary is {list(MODEL_CAPABILITIES)}")
            if spec.route is not None and spec.route not in MODEL_ROUTES:
                raise ValueError(f"{yaml_file.name}: unknown route {spec.route!r}; one of {list(MODEL_ROUTES)}")
            if spec.request_logging is not None and spec.request_logging not in REQUEST_LOGGING:
                raise ValueError(f"{yaml_file.name}: unknown request_logging {spec.request_logging!r}; one of {list(REQUEST_LOGGING)}")
            _check_route(yaml_file.name, spec)
            specs.append(spec)
    return specs


def _check_route(file_name: str, spec: "AIModel") -> None:
    """A Cloudflare model carries its route in its id, its file name and its
    ``route``, and the three agree; a model of any other provider carries none."""
    if spec.provider != "cloudflare":
        if spec.route is not None:
            raise ValueError(f"{file_name}: route is Cloudflare's; a {spec.provider} model carries none")
        return
    flavour = spec.id.split(":", 1)[1].split("/", 1)[0] if ":" in spec.id else ""
    if flavour not in ROUTE_FLAVOURS:
        raise ValueError(f"{file_name}: a Cloudflare id is cloudflare:<wrk|gtw>/<vendor>/<model>, not {spec.id!r}")
    if spec.route != ROUTE_FLAVOURS[flavour]:
        raise ValueError(f"{file_name}: id flavour {flavour!r} means route {ROUTE_FLAVOURS[flavour]!r}, the spec says {spec.route!r}")
    if not file_name.startswith(f"cloudflare-{flavour}-"):
        raise ValueError(f"{file_name}: a {flavour} model's file is named cloudflare-{flavour}-*.yaml")


def _check_providers(specs: List[AIModel]) -> None:
    """Every model names a provider the model-providers catalogue has."""
    from agentspecs.model_providers import MODEL_PROVIDER_CATALOGUE

    known = {provider.id for provider in MODEL_PROVIDER_CATALOGUE}
    for spec in specs:
        if spec.provider not in known:
            raise ValueError(f"{spec.id}: provider {spec.provider!r} has no spec under model-providers/ (known: {sorted(known)})")


def _build_enum() -> type:
    """Build the AIModels enum dynamically from YAML specs."""
    specs = _load_model_specs()
    members = {}
    for spec in specs:
        # Convert id to enum name: "anthropic:claude-sonnet-4-5-20250514" -> "ANTHROPIC_CLAUDE_SONNET_4_5"
        members[_enum_name(spec.id)] = spec.id
        # An older id keeps its member, with the older value: what a consumer
        # named before the id moved still means what it meant.
        for alias in spec.aliases:
            members.setdefault(_enum_name(alias), alias)
    return Enum("AIModels", members, type=str)


def _enum_name(model_id: str) -> str:
    return model_id.replace(":", "_").replace("-", "_").replace(".", "_").replace("/", "_").upper()


# Build the enum and catalogue at import time
AI_MODEL_CATALOGUE: List[AIModel] = _load_model_specs()
_check_providers(AI_MODEL_CATALOGUE)

AIModels = _build_enum()

# Find the default model
_defaults = [m for m in AI_MODEL_CATALOGUE if m.default]
DEFAULT_MODEL = AIModels(_defaults[0].id) if _defaults else None


def get_model(model_id: str) -> Optional[AIModel]:
    """Get a model specification by ID.

    Args:
        model_id: The unique model identifier.

    Returns:
        The AIModel specification, or None if not found.
    """
    for model in AI_MODEL_CATALOGUE:
        if model.id == model_id or model_id in model.aliases:
            return model
    return None


def get_default_model() -> Optional[AIModel]:
    """Get the default model specification.

    Returns:
        The default AIModel, or None if no default is set.
    """
    for model in AI_MODEL_CATALOGUE:
        if model.default:
            return model
    return None


def list_models() -> List[AIModel]:
    """List all available model specifications.

    Returns:
        List of all AIModel specifications.
    """
    return list(AI_MODEL_CATALOGUE)
