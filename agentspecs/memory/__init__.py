# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Memory specifications.

This module defines the MemorySpec Pydantic class and helpers for loading
memory definitions from YAML specifications.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class MemoryCreation(BaseModel):
    """How memories are created."""

    mode: str = Field(default="automatic", description="Creation mode: automatic, tool-call, or explicit")
    description: str = Field(default="", description="Description of the creation process")


class MemoryRetrieval(BaseModel):
    """How memories are retrieved."""

    method: str = Field(default="exact-match", description="Retrieval method: exact-match, rag, llm, or hybrid")
    description: str = Field(default="", description="Description of the retrieval process")
    modes: List[Dict[str, Any]] = Field(default_factory=list, description="Available retrieval modes")


class MemoryVerification(BaseModel):
    """Memory verification settings."""

    enabled: bool = Field(default=False, description="Whether citation-based verification is enabled")
    description: str = Field(default="", description="Description of the verification process")


class MemorySharing(BaseModel):
    """Cross-agent memory sharing settings."""

    enabled: bool = Field(default=False, description="Whether cross-agent sharing is enabled")
    description: str = Field(default="", description="Description of the sharing capabilities")


class MemoryResources(BaseModel):
    """Resource requirements for the memory backend."""

    embedding_model: Optional[str] = Field(default=None, description="Embedding model required")
    vector_store: Optional[str] = Field(default=None, description="Vector store backend")
    llm_for_extraction: bool = Field(default=False, description="Whether an LLM is needed for memory extraction")


class MemoryConfig(BaseModel):
    """Configuration for the memory backend."""

    platform: str = Field(default="self-hosted", description="Deployment mode: self-hosted or hosted/cloud")
    repo_url: Optional[str] = Field(default=None, description="Source repository URL")
    docs_url: Optional[str] = Field(default=None, description="Documentation URL")
    hosted_url: Optional[str] = Field(default=None, description="Hosted platform URL")
    cloud_url: Optional[str] = Field(default=None, description="Cloud service URL")
    api_url: Optional[str] = Field(default=None, description="API documentation URL")
    mcp_url: Optional[str] = Field(default=None, description="MCP server URL")
    paper_url: Optional[str] = Field(default=None, description="Research paper URL")


class MemorySpec(BaseModel):
    """Specification for a memory backend."""

    id: str = Field(..., description="Unique memory identifier (e.g., 'ephemeral', 'mem0')")
    name: str = Field(..., description="Display name for the memory backend")
    description: str = Field(default="", description="Memory backend description")
    persistence: str = Field(default="none", description="Persistence level: none, session, cross-session, permanent")
    scope: str = Field(default="agent", description="Memory scope: agent, team, repository, user, global")
    backend: str = Field(default="in-memory", description="Storage backend identifier")
    creation: Optional[MemoryCreation] = Field(default=None, description="Memory creation settings")
    retrieval: Optional[MemoryRetrieval] = Field(default=None, description="Memory retrieval settings")
    verification: Optional[MemoryVerification] = Field(default=None, description="Verification settings")
    sharing: Optional[MemorySharing] = Field(default=None, description="Cross-agent sharing settings")
    resources: Optional[MemoryResources] = Field(default=None, description="Resource requirements")
    config: Optional[MemoryConfig] = Field(default=None, description="Backend configuration")
    dependencies: List[str] = Field(default_factory=list, description="Python package dependencies")
    required_env_vars: List[str] = Field(default_factory=list, description="Required environment variable names")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    icon: str = Field(default="database", description="Icon identifier")
    emoji: str = Field(default="🧠", description="Emoji representation")


def _load_memory_specs() -> List[MemorySpec]:
    """Load all memory YAML specifications from the memory directory."""
    memory_dir = Path(__file__).parent
    specs = []
    for yaml_file in sorted(memory_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            specs.append(MemorySpec(**data))
    return specs


def _build_enum() -> type:
    """Build the Memories enum dynamically from YAML specs."""
    specs = _load_memory_specs()
    members = {}
    for spec in specs:
        name = spec.id.replace("-", "_").upper()
        members[name] = spec.id
    return Enum("Memories", members, type=str)


# Build the enum and catalogue at import time
MEMORY_CATALOGUE: List[MemorySpec] = _load_memory_specs()

Memories = _build_enum()


def get_memory(memory_id: str) -> Optional[MemorySpec]:
    """Get a memory specification by ID.

    Args:
        memory_id: The unique memory identifier.

    Returns:
        The MemorySpec, or None if not found.
    """
    for memory in MEMORY_CATALOGUE:
        if memory.id == memory_id:
            return memory
    return None


def list_memories() -> List[MemorySpec]:
    """List all available memory specifications.

    Returns:
        List of all MemorySpec specifications.
    """
    return list(MEMORY_CATALOGUE)
