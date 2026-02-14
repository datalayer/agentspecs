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


class AIModel(BaseModel):
    """Specification for an AI model."""

    id: str = Field(..., description="Unique model identifier (e.g., 'anthropic:claude-sonnet-4-5-20250514')")
    name: str = Field(..., description="Display name for the model")
    description: str = Field(default="", description="Model description")
    provider: str = Field(..., description="Provider name (anthropic, openai, bedrock, azure-openai)")
    default: bool = Field(default=False, description="Whether this is the default model")
    required_env_vars: List[str] = Field(default_factory=list, description="Required environment variable names")


def _load_model_specs() -> List[AIModel]:
    """Load all model YAML specifications from the models directory."""
    models_dir = Path(__file__).parent
    specs = []
    for yaml_file in sorted(models_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            specs.append(AIModel(**data))
    return specs


def _build_enum() -> type:
    """Build the AIModels enum dynamically from YAML specs."""
    specs = _load_model_specs()
    members = {}
    for spec in specs:
        # Convert id to enum name: "anthropic:claude-sonnet-4-5-20250514" -> "ANTHROPIC_CLAUDE_SONNET_4_5"
        name = spec.id.replace(":", "_").replace("-", "_").replace(".", "_").upper()
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
