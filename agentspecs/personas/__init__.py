# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Persona specifications.

A Persona is a lightweight identity built on top of an Agent spec.
It bundles a display name, a short description and a set of tags that
describe the role and tone of the underlying agent.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class Persona(BaseModel):
    """Specification for a Persona."""

    id: str = Field(..., description="Unique persona identifier (e.g., 'tutor', 'sentinel')")
    version: str = Field(default="0.0.1", description="Persona spec version")
    name: str = Field(..., description="Display name of the persona")
    description: str = Field(default="", description="Short persona description")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    icon: Optional[str] = Field(default=None, description="Icon identifier")
    emoji: Optional[str] = Field(default=None, description="Emoji representation")
    agent: Optional[str] = Field(
        default=None,
        description="Optional reference to the underlying agent spec id",
    )


def _load_persona_specs() -> List[Persona]:
    """Load all persona YAML specifications from the personas directory."""
    personas_dir = Path(__file__).parent
    specs: List[Persona] = []
    for yaml_file in sorted(personas_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            specs.append(Persona(**data))
    return specs


def _build_enum() -> type:
    """Build the Personas enum dynamically from YAML specs."""
    specs = _load_persona_specs()
    members = {spec.id.replace("-", "_").upper(): spec.id for spec in specs}
    if not members:
        members["__EMPTY__"] = "__empty__"
    return Enum("Personas", members, type=str)


# Build the enum and catalogue at import time
PERSONA_CATALOGUE: List[Persona] = _load_persona_specs()

Personas = _build_enum()


def get_persona(persona_id: str) -> Optional[Persona]:
    """Get a persona specification by ID.

    Args:
        persona_id: The unique persona identifier.

    Returns:
        The Persona specification, or None if not found.
    """
    for persona in PERSONA_CATALOGUE:
        if persona.id == persona_id:
            return persona
    return None


def list_personas() -> List[Persona]:
    """List all available persona specifications.

    Returns:
        List of all Persona specifications.
    """
    return list(PERSONA_CATALOGUE)


__all__ = [
    "Persona",
    "Personas",
    "PERSONA_CATALOGUE",
    "get_persona",
    "list_personas",
]
