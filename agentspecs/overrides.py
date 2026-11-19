# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Overriding an application on stage (the user, 7 November 2026).

A Battle's contestant and a scene's cast member put an application of the
catalogue on stage as it is. With `overrides`, they say what this one plays
differently — as a child spec says it with `extends`
(https://agentspecs.datalayer.tech/modularity/extension), but for one
appearance, with no new spec: the `model` it answers with, its
`instructions`, its `skills`, its `context`. Nothing else of an application
may be overridden there: what it is, its rules and its tests stay its own.

The override is applied where the application is played: a member played in
the page answers with the model it names; a member at a deployment answers
as it was shipped, and the override is said, not applied.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

#: What a contestant or a cast member may say differently of its application.
OVERRIDABLE: Tuple[str, ...] = ("model", "instructions", "skills", "context")


def check_overrides(overrides: Mapping[str, Any], who: str) -> Dict[str, Any]:
    """The overrides as written, each key one of `OVERRIDABLE` with a value of its kind; raised otherwise."""
    checked: Dict[str, Any] = {}
    for key, value in overrides.items():
        if key not in OVERRIDABLE:
            raise ValueError(f"{who} overrides {key!r}; an application's {', '.join(OVERRIDABLE)} may be overridden, nothing else")
        if key in ("model", "instructions"):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{who} overrides {key!r} with {value!r}; it is a sentence, never empty")
            checked[key] = " ".join(value.split()) if key == "instructions" else value.strip()
        else:
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                raise ValueError(f"{who} overrides {key!r} with {value!r}; it is a list of names")
            checked[key] = [item.strip() for item in value]
    return checked


def override_model_problem(overrides: Mapping[str, Any], who: str) -> str:
    """A sentence when the model an override names is not in the catalogue; empty otherwise."""
    model = overrides.get("model")
    if not model:
        return ""
    from .models import get_model  # noqa: PLC0415

    if get_model(model) is None:
        return f"{who} overrides the model with {model!r}, which is not a model of the catalogue"
    return ""


__all__ = ["OVERRIDABLE", "check_overrides", "override_model_problem"]
