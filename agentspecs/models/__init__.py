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
    """What the provider lists a model at, per million tokens, in dollars."""

    input_usd_per_million: float = Field(default=0.0, description="Dollars per million input tokens")
    output_usd_per_million: float = Field(default=0.0, description="Dollars per million output tokens")


#: What a model can be trusted with. ``judgments`` is a typed-judgment model
#: (noul, choice and score questions, answered as probabilities — Jev);
#: ``judge`` is a chat model that may be asked those questions and made to
#: answer in the same shape, whose probabilities are what it says they are.
MODEL_CAPABILITIES = ("chat", "tools", "codemode", "vision", "thinking", "judgments", "judge")

#: How a Cloudflare model is reached. ``workers-ai``: a model Cloudflare hosts
#: (``@cf/…``), at Workers AI's own endpoint or through AI Gateway; billed in
#: neurons (``billing: standard``), or from gateway credits for the frontier
#: ones (``billing: credits``). ``ai-gateway``: a third-party model the
#: gateway fronts (``typesafe/jev``), reachable only through the gateway and
#: paid from its credits. Other providers leave it unset.
MODEL_ROUTES = ("workers-ai", "ai-gateway")


class AIModel(BaseModel):
    """Specification for an AI model."""

    id: str = Field(..., description="Unique model identifier (e.g., 'anthropic:claude-sonnet-4-5-20250514')")
    name: str = Field(..., description="Display name for the model")
    description: str = Field(default="", description="Model description")
    provider: str = Field(..., description="Provider name (anthropic, openai, bedrock, azure-openai)")
    default: bool = Field(default=False, description="Whether this is the default model")
    available: bool = Field(
        default=False,
        description="Whether this model is offered to a person choosing one. The catalogue is what the platform knows how to talk to; this is what it is worth offering today. Without the distinction a picker lists twenty-six models, most of them superseded, and the choice becomes a chore rather than a help.",
    )
    required_env_vars: List[str] = Field(default_factory=list, description="Required environment variable names")
    tokens_limit: Optional[int] = Field(default=None, description="Maximum output tokens the model can generate in a single run")
    capabilities: List[str] = Field(default_factory=list, description="What the model can be trusted with: chat, tools, codemode, vision, thinking, judgments, judge")
    billing: Optional[str] = Field(default=None, description="How the provider bills it, when worth telling: 'standard' or 'credits'")
    route: Optional[str] = Field(default=None, description="How a Cloudflare model is reached: 'workers-ai' (a model Cloudflare hosts) or 'ai-gateway' (a third-party model the gateway fronts)")
    context_window: Optional[int] = Field(default=None, description="The tokens a request may carry, input and output together")
    zero_data_retention: Optional[bool] = Field(default=None, description="Whether the provider keeps nothing of a request once it is answered")
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
            specs.append(spec)
    return specs


def _build_enum() -> type:
    """Build the AIModels enum dynamically from YAML specs."""
    specs = _load_model_specs()
    members = {}
    for spec in specs:
        # Convert id to enum name: "anthropic:claude-sonnet-4-5-20250514" -> "ANTHROPIC_CLAUDE_SONNET_4_5"
        name = spec.id.replace(":", "_").replace("-", "_").replace(".", "_").replace("/", "_").upper()
        # Remove version suffixes like _20250514 or _V1_0
        # Keep the name readable
        members[name] = spec.id
    return Enum("AIModels", members, type=str)


# Build the enum and catalogue at import time
AI_MODEL_CATALOGUE: List[AIModel] = _load_model_specs()

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
        if model.id == model_id:
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
