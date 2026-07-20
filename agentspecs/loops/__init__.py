# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Loop specifications.

This module defines the ``LoopSpec`` Pydantic class and helpers for loading
agent execution-loop definitions from YAML specifications.

A *loop* describes how an agent progresses from one decision to the next: the
control cycle (observe → think → act → evaluate), the goal/objective it works
toward, the constraints and success criteria that bound it, where state lives
between iterations, how the human participates, and when the loop terminates.

The specification is deliberately framework-agnostic. It captures the
*execution model* independently of any particular runtime (PydanticAI,
LangGraph, Google ADK, OpenAI Responses, ...), so planners, runtimes, UIs and
observability tools can share a common notion of an agent loop.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class LoopHuman(BaseModel):
    """How the human participates in (or around) the loop."""

    mode: str = Field(
        default="initiate",
        description="Human interaction pattern: none, initiate, approve, feedback, or tool",
    )
    approval_required: bool = Field(
        default=False,
        description="Whether the loop pauses for human approval before sensitive actions",
    )
    approval_for: List[str] = Field(
        default_factory=list,
        description="Actions that require explicit human approval (e.g. delete, send-email)",
    )
    description: str = Field(
        default="",
        description="Description of the human-in-the-loop behaviour",
    )


class LoopTermination(BaseModel):
    """When and how the loop stops iterating."""

    max_iterations: int = Field(
        default=10,
        ge=1,
        description="Maximum number of iterations before the loop is forced to stop",
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions that mark the goal as reached",
    )
    failure_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions that mark the loop as failed and stop it",
    )
    on_blocked: str = Field(
        default="ask-human",
        description="What to do when blocked: ask-human, retry, or abort",
    )


class LoopSpec(BaseModel):
    """Specification for an agent execution loop."""

    id: str = Field(..., description="Unique loop identifier (e.g., 'data-analysis')")
    version: str = Field(default="0.0.1", description="Loop spec version")
    name: str = Field(..., description="Display name for the loop")
    description: str = Field(default="", description="Loop description")
    objective: str = Field(
        default="",
        description="Default goal/objective the loop works toward",
    )
    strategy: str = Field(
        default="observe-think-act-evaluate",
        description="Loop strategy family (e.g. observe-think-act-evaluate, plan-execute-critic, ooda, react)",
    )
    phases: List[str] = Field(
        default_factory=lambda: ["observe", "think", "act", "evaluate"],
        description="Ordered phase names that make up one iteration of the loop",
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Boundaries the agent must respect (e.g. read-only, max-cost)",
    )
    termination: Optional[LoopTermination] = Field(
        default=None,
        description="Termination policy (iteration cap, success/failure criteria)",
    )
    human: Optional[LoopHuman] = Field(
        default=None,
        description="Human-in-the-loop participation settings",
    )
    state_backends: List[str] = Field(
        default_factory=list,
        description="Where loop state lives between iterations (notebook, runtime, filesystem, sql, vector, mcp)",
    )
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    icon: str = Field(default="sync", description="Icon identifier")
    emoji: str = Field(default="\U0001f504", description="Emoji representation")


def _load_loop_specs() -> List[LoopSpec]:
    """Load all loop YAML specifications from the loops directory."""
    loops_dir = Path(__file__).parent
    specs: List[LoopSpec] = []
    for yaml_file in sorted(loops_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            specs.append(LoopSpec(**data))
    return specs


def _build_enum() -> type:
    """Build the Loops enum dynamically from YAML specs."""
    specs = _load_loop_specs()
    members = {}
    for spec in specs:
        name = spec.id.replace("-", "_").upper()
        members[name] = spec.id
    return Enum("Loops", members, type=str)


# Build the catalogue and enum at import time
LOOP_CATALOGUE: List[LoopSpec] = _load_loop_specs()

Loops = _build_enum()


def get_loop(loop_id: str) -> Optional[LoopSpec]:
    """Get a loop specification by ID.

    Args:
        loop_id: The unique loop identifier.

    Returns:
        The LoopSpec, or None if not found.
    """
    for loop in LOOP_CATALOGUE:
        if loop.id == loop_id:
            return loop
    return None


def list_loops() -> List[LoopSpec]:
    """List all available loop specifications.

    Returns:
        List of all LoopSpec specifications.
    """
    return list(LOOP_CATALOGUE)
