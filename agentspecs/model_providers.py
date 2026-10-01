# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Model provider specifications.

Who serves a model: the vendor's own API (Anthropic, OpenAI), a cloud that
hosts it (Amazon Bedrock, Azure OpenAI, Alibaba Cloud Model Studio,
Cloudflare), or the user's machine (Ollama). One YAML per provider under
``agentspecs/model-providers/``, with where it lives, its documentation,
its terms of service, its privacy policy and what it says about the data a
request carries — what a person choosing a model, or a team signing off on
one, has to be able to read. A model spec's ``provider`` names one of these
and is refused if it names none.
"""

from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field

#: Where the YAML specs are: a hyphenated folder, not a package, beside the others.
MODEL_PROVIDERS_DIR = Path(__file__).parent / "model-providers"

#: Where a provider runs the model.
PROVIDER_HOSTING = ("cloud", "local")


class ModelProvider(BaseModel):
    """Specification for a model provider."""

    id: str = Field(..., description="Provider id, what a model spec's `provider` names (e.g. 'anthropic')")
    version: str = Field(default="0.0.1", description="Specification version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What the provider is, and what is worth knowing before choosing it")
    website: str = Field(default="", description="The provider's product page")
    docs_url: str = Field(default="", description="The provider's documentation")
    terms_url: str = Field(default="", description="The terms of service a call is made under")
    privacy_url: str = Field(default="", description="The provider's privacy policy")
    data_usage_url: Optional[str] = Field(default=None, description="What the provider says about the data a request carries (retention, training), when it has a page for it")
    hosting: str = Field(default="cloud", description="Where the model runs: 'cloud' (the provider's) or 'local' (the user's machine)")


def _load_provider_specs(providers_dir: Optional[Path] = None) -> List[ModelProvider]:
    providers_dir = providers_dir or MODEL_PROVIDERS_DIR
    specs: List[ModelProvider] = []
    for yaml_file in sorted(providers_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f) or {}
        spec = ModelProvider(**data)
        if spec.hosting not in PROVIDER_HOSTING:
            raise ValueError(f"{yaml_file.name}: unknown hosting {spec.hosting!r}; one of {list(PROVIDER_HOSTING)}")
        if spec.id != yaml_file.stem:
            raise ValueError(f"{yaml_file.name}: the file is named for id {yaml_file.stem!r}, the spec says {spec.id!r}")
        specs.append(spec)
    return specs


MODEL_PROVIDER_CATALOGUE: List[ModelProvider] = _load_provider_specs()


def get_model_provider(provider_id: str) -> Optional[ModelProvider]:
    for provider in MODEL_PROVIDER_CATALOGUE:
        if provider.id == provider_id:
            return provider
    return None


def list_model_providers() -> List[ModelProvider]:
    return list(MODEL_PROVIDER_CATALOGUE)
