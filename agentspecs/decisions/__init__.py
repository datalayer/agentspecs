# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Decisions specifications.

A *decision* is a typed question about a text — does a statement hold (noul),
which of named options fits (choice), where something sits on a scale (score)
— answered by a typed-decision model. A decisions spec says how an agent
decides: the model the questions are asked of, which question types it
answers, and the limits of one call.

An agent has the capability only when its spec names one
(``decisions: jev:0.0.1``). The capability brings the ``decide`` backend tool:
an agent that names ``decisions`` gets it, asked of that spec's model, and an
agent that lists ``decide`` without naming ``decisions`` is refused.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

#: The question types a decision model may answer.
QUESTION_TYPES = ("noul", "choice", "score")

#: The backend tool the capability brings, by its id.
DECIDE_TOOL = "decide"


class DecisionsError(ValueError):
    """A decisions spec, or an agent's use of one, that cannot be used — named plainly."""


class DecisionsSpec(BaseModel):
    """How an agent decides: the model asked, the question types, the limits."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique decisions identifier")
    version: str = Field(default="0.0.1", description="Decisions spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What it decides, and with what")
    enabled: bool = Field(default=False, description="Whether an agent spec is offered these decisions")
    model: str = Field(..., description="The model the questions are asked of: a model of the catalogue that answers typed decisions")
    questions: List[Literal["noul", "choice", "score"]] = Field(
        default_factory=lambda: list(QUESTION_TYPES),
        description="The question types it answers: noul, choice, score",
    )
    max_questions: int = Field(default=10, ge=1, description="The most questions one call may ask")
    max_text_length: int = Field(default=20000, ge=1, description="The longest text one call may be about, in characters")
    tags: List[str] = Field(default_factory=list, description="Tags")
    icon: Optional[str] = Field(default=None, description="Icon, `<package>:<name>`")
    emoji: Optional[str] = Field(default=None, description="Emoji drawn where there is no icon")

    @field_validator("questions")
    @classmethod
    def _answers_something(cls, questions: List[str]) -> List[str]:
        if not questions:
            raise ValueError("a decisions spec answers at least one question type: noul, choice or score")
        if len(set(questions)) != len(questions):
            raise ValueError("a question type is named once")
        return questions


def id_of(ref: str) -> str:
    """The id of a reference, ``id`` or ``id:version``."""
    base, _, version = str(ref).rpartition(":")
    return base if base and "." in version else str(ref)


def check_decisions(spec: DecisionsSpec) -> DecisionsSpec:
    """Refuse, in a sentence, a decisions spec whose model the catalogue does not have, or that answers no typed decisions."""
    from agentspecs.models import get_model

    model = get_model(spec.model)
    if model is None:
        raise DecisionsError(f"decisions {spec.id!r} asks {spec.model!r}, which is not in the models catalogue")
    if model.id != spec.model:
        raise DecisionsError(f"decisions {spec.id!r} asks {spec.model!r}, an older id of {model.id!r}: name the model by its id")
    if "decisions" not in model.capabilities:
        raise DecisionsError(f"decisions {spec.id!r} asks {spec.model!r}, which answers no typed decisions")
    return spec


def load_decisions(directory: Optional[Path] = None, check: bool = True) -> Dict[str, DecisionsSpec]:
    """Every decisions spec of a directory, by id; the file is named for the id."""
    directory = directory or Path(__file__).parent
    specs: Dict[str, DecisionsSpec] = {}
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        if data.get("id") != path.stem:
            raise DecisionsError(f"{path.name}: the file is named for id {path.stem!r}, the spec says {data.get('id')!r}")
        spec = DecisionsSpec(**data)
        specs[spec.id] = check_decisions(spec) if check else spec
    return specs


DECISIONS_CATALOGUE: Dict[str, DecisionsSpec] = load_decisions()


def get_decisions(ref: str) -> Optional[DecisionsSpec]:
    """The decisions spec a reference names (``id`` or ``id:version``), or None."""
    return DECISIONS_CATALOGUE.get(id_of(ref))


def list_decisions() -> List[DecisionsSpec]:
    """Every decisions spec of the catalogue."""
    return list(DECISIONS_CATALOGUE.values())


def agent_decisions(
    agent: Dict[str, Any],
    decisions: Optional[Dict[str, DecisionsSpec]] = None,
) -> Optional[DecisionsSpec]:
    """The decisions spec an agent's spec names, or None when it names none.

    Refused, in a sentence naming the agent: a ``decisions`` that names a spec
    the catalogue does not have, a version it does not have, or a spec that is
    not enabled; and ``decide`` among its ``backend_tools`` when it names no
    ``decisions`` — the capability brings the tool, not the other way round.
    """
    catalogue = decisions if decisions is not None else DECISIONS_CATALOGUE
    agent_id = agent.get("id")
    ref = agent.get("decisions")
    tools = [id_of(tool) for tool in agent.get("backend_tools") or []]
    if not ref:
        if DECIDE_TOOL in tools:
            raise DecisionsError(
                f"agent {agent_id!r} lists the backend tool `{DECIDE_TOOL}` but its spec names no decisions: "
                f"say `decisions: <id>:<version>` (for example `decisions: jev:0.0.1`), which brings the tool, "
                f"and remove `{DECIDE_TOOL}` from `backend_tools`"
            )
        return None
    if not isinstance(ref, str):
        raise DecisionsError(f"agent {agent_id!r}: `decisions` is one reference, `id:version`, not {ref!r}")
    spec = catalogue.get(id_of(ref))
    if spec is None:
        raise DecisionsError(
            f"agent {agent_id!r} names decisions {ref!r}, which the decisions catalogue does not have (known: {', '.join(sorted(catalogue)) or 'none'})"
        )
    if ref != id_of(ref) and ref != f"{spec.id}:{spec.version}":
        raise DecisionsError(f"agent {agent_id!r} names decisions {ref!r}; the catalogue has {spec.id}:{spec.version}")
    if not spec.enabled:
        raise DecisionsError(f"agent {agent_id!r} names decisions {ref!r}, which is not enabled")
    return spec


__all__ = [
    "DECIDE_TOOL",
    "DECISIONS_CATALOGUE",
    "QUESTION_TYPES",
    "DecisionsError",
    "DecisionsSpec",
    "agent_decisions",
    "check_decisions",
    "get_decisions",
    "id_of",
    "list_decisions",
    "load_decisions",
]
