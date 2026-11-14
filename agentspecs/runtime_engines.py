# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The runtime engine of an agent: what runs and hosts the agent.

``harness`` says which agent program turns the agent's loop (pydantic-ai,
vercel-ai, Claude Code…). ``runtime_engine``, on the line after it, says what
runs that program and keeps it alive:

- ``datalayer``: a Datalayer agent runtime, launched from the platform's
  pools (or on the developer's own machine), metered in credits and known by
  its uid;
- ``kagent``: `kagent <https://kagent.dev>`_, a Kubernetes control plane for
  agents. The agent is a kagent ``Agent`` (an ``AgentTemplate`` and a
  ``Harness`` running ``agent-runtimes serve --target kagent`` behind the
  kagent bridge), reached through kagent's A2A gateway at
  ``/agents/{namespace}/{name}``; each conversation is a session actor of
  Agent Substrate, suspended when idle and resumed on the next message.

Every agent spec of the catalogue says its engine; a spec without one, or
naming another, is refused at load in a sentence
(:func:`agent_runtime_engine_problems`). ``kagent`` and ``agentcore`` serve an
agent through the agent-runtimes server, so they take the ``pydantic-ai``
harness only.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: The engines an agent may name, the default first.
RUNTIME_ENGINES: tuple[str, ...] = ("datalayer", "kagent", "agentcore")

#: The engine of an agent built in code that names none.
DEFAULT_RUNTIME_ENGINE = RUNTIME_ENGINES[0]

#: The harnesses each engine can run; an engine absent here runs any.
ENGINE_HARNESSES: dict[str, tuple[str, ...]] = {
    "kagent": ("pydantic-ai",),
    "agentcore": ("pydantic-ai",),
}


def agent_runtime_engine_problems(spec: Mapping[str, Any]) -> list[str]:
    """What is wrong with an agent spec's ``runtime_engine``, one sentence each.

    Empty when the spec names a known engine that can run its harness.
    """
    agent = spec.get("id") or "an agent"
    if "runtime_engine" not in spec or spec.get("runtime_engine") in (None, ""):
        return [
            f"{agent}: names no runtime_engine: one of {', '.join(RUNTIME_ENGINES)}, "
            "on the line after harness"
        ]
    engine = spec["runtime_engine"]
    if engine not in RUNTIME_ENGINES:
        return [
            f"{agent}: there is no runtime_engine named {engine!r}: one of "
            f"{', '.join(RUNTIME_ENGINES)}"
        ]
    harness = str(spec.get("harness") or "pydantic-ai")
    allowed = ENGINE_HARNESSES.get(engine)
    if allowed is not None and harness not in allowed:
        return [
            f"{agent}: the runtime_engine {engine!r} runs the harness "
            f"{' or '.join(allowed)}, not {harness!r}"
        ]
    return []
