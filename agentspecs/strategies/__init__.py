# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Strategy specifications.

This module defines the ``StrategySpec`` Pydantic class and helpers for loading
agent reasoning-strategy definitions from YAML specifications.

A *strategy* describes the control loop an agent reasons with: how it
progresses from one decision to the next (observe → think → act → evaluate),
the goal/objective it works toward, the constraints and success criteria that
bound it, where state lives between iterations, how the human participates,
and when the iterations terminate.

The specification is deliberately framework-agnostic. It captures the
*execution model* independently of any particular runtime (PydanticAI,
LangGraph, Google ADK, OpenAI Responses, ...), so planners, runtimes, UIs and
observability tools can share a common notion of an agent's strategy.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class StrategyHuman(BaseModel):
    """How the human participates in (or around) the strategy's iterations."""

    mode: str = Field(
        default="initiate",
        description="Human interaction pattern: none, initiate, approve, feedback, or tool",
    )
    approval_required: bool = Field(
        default=False,
        description="Whether the strategy pauses for human approval before sensitive actions",
    )
    approval_for: List[str] = Field(
        default_factory=list,
        description="Actions that require explicit human approval (e.g. delete, send-email)",
    )
    description: str = Field(
        default="",
        description="Description of the human-in-the-loop behaviour",
    )


class StrategyTermination(BaseModel):
    """When and how the strategy stops iterating."""

    max_iterations: int = Field(
        default=10,
        ge=1,
        description="Maximum number of iterations before the strategy is forced to stop",
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions that mark the goal as reached",
    )
    failure_criteria: List[str] = Field(
        default_factory=list,
        description="Conditions that mark the strategy as failed and stop it",
    )
    on_blocked: str = Field(
        default="ask-human",
        description="What to do when blocked: ask-human, retry, or abort",
    )


class StrategySpec(BaseModel):
    """Specification for an agent reasoning strategy (a control loop)."""

    id: str = Field(..., description="Unique strategy identifier (e.g., 'data-analysis')")
    version: str = Field(default="0.0.1", description="Strategy spec version")
    name: str = Field(..., description="Display name for the strategy")
    description: str = Field(default="", description="Strategy description")
    objective: str = Field(
        default="",
        description="Default goal/objective the strategy works toward",
    )
    strategy: str = Field(
        default="observe-think-act-evaluate",
        description="Strategy family (e.g. observe-think-act-evaluate, plan-execute-critic, ooda, react)",
    )
    phases: List[str] = Field(
        default_factory=lambda: ["observe", "think", "act", "evaluate"],
        description="Ordered phase names that make up one iteration of the strategy",
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Boundaries the agent must respect (e.g. read-only, max-cost)",
    )
    termination: Optional[StrategyTermination] = Field(
        default=None,
        description="Termination policy (iteration cap, success/failure criteria)",
    )
    human: Optional[StrategyHuman] = Field(
        default=None,
        description="Human-in-the-loop participation settings",
    )
    state_backends: List[str] = Field(
        default_factory=list,
        description="Where strategy state lives between iterations (notebook, runtime, filesystem, sql, vector, mcp)",
    )
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    icon: str = Field(default="sync", description="Icon identifier")
    emoji: str = Field(default="\U0001f504", description="Emoji representation")


def _load_strategy_specs() -> List[StrategySpec]:
    """Load all strategy YAML specifications from the strategies directory."""
    strategies_dir = Path(__file__).parent
    specs: List[StrategySpec] = []
    for yaml_file in sorted(strategies_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
            specs.append(StrategySpec(**data))
    return specs


def _build_enum() -> type:
    """Build the Strategies enum dynamically from YAML specs."""
    specs = _load_strategy_specs()
    members = {}
    for spec in specs:
        name = spec.id.replace("-", "_").upper()
        members[name] = spec.id
    return Enum("Strategies", members, type=str)


# Build the catalogue and enum at import time
STRATEGY_CATALOGUE: List[StrategySpec] = _load_strategy_specs()

Strategies = _build_enum()


def get_strategy(strategy_id: str) -> Optional[StrategySpec]:
    """Get a strategy specification by ID.

    Args:
        strategy_id: The unique strategy identifier.

    Returns:
        The StrategySpec, or None if not found.
    """
    for strategy in STRATEGY_CATALOGUE:
        if strategy.id == strategy_id:
            return strategy
    return None


def list_strategies() -> List[StrategySpec]:
    """List all available strategy specifications.

    Returns:
        List of all StrategySpec specifications.
    """
    return list(STRATEGY_CATALOGUE)
