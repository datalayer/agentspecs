# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The runtime engines, as specs: what runs and hosts an agent.

``harness`` says which agent program turns the agent's loop (pydantic-ai,
vercel-ai, Claude Code…). ``runtime_engine``, on the line after it, says what
runs that program and keeps it alive. One YAML per engine under
``runtime-engines/``: its id, its name, what it is, its own documentation,
its place where the engines are offered (``position``, the default first),
the harnesses it runs (``harnesses``, null for any) and whether it is
``enabled`` today:

- ``datalayer``: a Datalayer agent runtime, launched from the platform's
  pools (or on the developer's own machine), metered in credits and known by
  its uid;
- ``kagent``: Kagent (`kagent.dev <https://kagent.dev>`_), a Kubernetes
  control plane for agents. The agent is a Kagent ``Agent`` (an
  ``AgentTemplate`` and a ``Harness`` running
  ``agent-runtimes serve --target kagent`` behind the Kagent bridge), reached
  through Kagent's A2A gateway at ``/agents/{namespace}/{name}``; each
  conversation is a session actor of Agent Substrate, suspended when idle and
  resumed on the next message;
- ``agentcore``: AWS AgentCore, Amazon Bedrock AgentCore Runtime in the AWS
  account of the organization that launches the agent.

Every agent spec of the catalogue says its engine; a spec without one, or
naming another, or one that is not enabled, is refused at load in a sentence
(:func:`agent_runtime_engine_problems`). ``kagent`` and ``agentcore`` serve an
agent through the agent-runtimes server, so they take the ``pydantic-ai``
harness only.

``python -m agentspecs.runtime_engines`` writes the JSON Schema beside the
specs and the reference page of the documentation.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

#: The runtime engine specs.
RUNTIME_ENGINES_DIR = Path(__file__).resolve().parent / "runtime-engines"

#: Where the JSON Schema is kept, beside the specs.
SCHEMA_PATH = RUNTIME_ENGINES_DIR / "runtime-engine.schema.json"

#: Where the reference page is kept in the documentation site, when the checkout has one.
REFERENCE_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "docs" / "runtime-engines" / "index.md"
)

_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")


class RuntimeEngineSpec(BaseModel):
    """One runtime engine: what runs and hosts an agent."""

    model_config = ConfigDict(extra="forbid")

    # The rules the validators below hold a spec to are said in the schema
    # too (`json_schema_extra`): what the loader refuses, the published
    # schema refuses. The validators keep the sentences.
    id: str = Field(
        description="Its id, the file's name: what an agent's `runtime_engine` says",
        json_schema_extra={"pattern": _ID.pattern},
    )
    version: str = Field(description="The version of this spec")
    name: str = Field(min_length=1, description="Its name, as a person reads it")
    description: str = Field(min_length=1, description="What it is, in a sentence or two")
    docs_url: str = Field(
        description="Its own documentation, https",
        json_schema_extra={"pattern": "^https://"},
    )
    position: int = Field(
        ge=1, description="Its place where the engines are offered; 1 is the default"
    )
    harnesses: list[str] | None = Field(
        description="The harnesses it runs, by id; null when it runs any",
        # Read of a list alone: null is not held to them.
        json_schema_extra={"minItems": 1, "uniqueItems": True},
    )
    enabled: bool = Field(
        description="Whether an agent may run on it today: a disabled engine stays in the "
        "catalogue and is not one an agent may name"
    )

    @field_validator("id")
    @classmethod
    def _an_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError(
                f"{value!r} is not a runtime engine id: lower-case letters, digits and hyphens"
            )
        return value

    @field_validator("docs_url")
    @classmethod
    def _https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("a runtime engine's documentation is read at an https address")
        return value

    @field_validator("harnesses")
    @classmethod
    def _some_harnesses(cls, value: list[str] | None) -> list[str] | None:
        if value is not None:
            if not value:
                raise ValueError("an engine runs some harness: list them, or say null for any")
            if len(set(value)) != len(value):
                raise ValueError("a harness is listed twice")
        return value


def load_runtime_engines(directory: Path = RUNTIME_ENGINES_DIR) -> dict[str, RuntimeEngineSpec]:
    """Every runtime engine of a directory, validated, by id, in their order.

    Each file is named for its id.
    """
    found: list[RuntimeEngineSpec] = []
    for path in sorted(directory.glob("*.yaml")):
        spec = RuntimeEngineSpec.model_validate(yaml.safe_load(path.read_text()) or {})
        if spec.id != path.stem:
            raise ValueError(
                f"{path.name}: the file is named for {path.stem!r}, the spec says {spec.id!r}"
            )
        found.append(spec)
    positions = sorted(spec.position for spec in found)
    if positions != list(range(1, len(found) + 1)):
        raise ValueError(
            f"the runtime engines take the positions 1 to {len(found)}, each once: {positions}"
        )
    if found and not any(spec.enabled for spec in found):
        raise ValueError(
            "no runtime engine is enabled: an agent has nowhere to run, and there is no "
            "default. Enable one at least."
        )
    return {spec.id: spec for spec in sorted(found, key=lambda spec: spec.position)}


def enabled_engines(catalogue: Mapping[str, RuntimeEngineSpec]) -> tuple[str, ...]:
    """The engines of a catalogue an agent may name: the enabled ones, in their order."""
    return tuple(spec.id for spec in catalogue.values() if spec.enabled)


#: Every runtime engine of the catalogue, by id, in their order: the disabled
#: ones too, which stay known (a name, a page) and are not offered.
RUNTIME_ENGINE_CATALOGUE: dict[str, RuntimeEngineSpec] = load_runtime_engines()

#: The engines an agent may name, the default first: the enabled ones alone.
RUNTIME_ENGINES: tuple[str, ...] = enabled_engines(RUNTIME_ENGINE_CATALOGUE)

#: The engine of an agent built in code that names none: the first enabled
#: one (a catalogue with none is refused as it loads).
DEFAULT_RUNTIME_ENGINE = RUNTIME_ENGINES[0]

#: The harnesses each engine can run; an engine absent here runs any.
ENGINE_HARNESSES: dict[str, tuple[str, ...]] = {
    spec.id: tuple(spec.harnesses)
    for spec in RUNTIME_ENGINE_CATALOGUE.values()
    if spec.harnesses is not None
}


def get_runtime_engine(engine_id: str) -> RuntimeEngineSpec | None:
    """A runtime engine by id, or None."""
    return RUNTIME_ENGINE_CATALOGUE.get(engine_id)


def agent_runtime_engine_problems(spec: Mapping[str, Any]) -> list[str]:
    """What is wrong with an agent spec's ``runtime_engine``, one sentence each.

    Empty when the spec names an enabled engine that can run its harness.
    """
    agent = spec.get("id") or "an agent"
    if "runtime_engine" not in spec or spec.get("runtime_engine") in (None, ""):
        return [
            f"{agent}: names no runtime_engine: one of {', '.join(RUNTIME_ENGINES)}, "
            "on the line after harness"
        ]
    engine = spec["runtime_engine"]
    known = isinstance(engine, str) and engine in RUNTIME_ENGINE_CATALOGUE
    if known and engine not in RUNTIME_ENGINES:
        return [
            f"{agent}: the runtime_engine {engine!r} is not enabled: one of "
            f"{', '.join(RUNTIME_ENGINES)}"
        ]
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


def json_schema() -> dict[str, object]:
    """The JSON Schema of a runtime engine spec."""
    schema = RuntimeEngineSpec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://agentspecs.datalayer.tech/schemas/runtime-engine.json"
    schema["title"] = "Runtime engine"
    return schema


def schema_text() -> str:
    """The JSON Schema as it is written to :data:`SCHEMA_PATH`."""
    return json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"


def _cell(text: object) -> str:
    words = " ".join(str(text if text is not None else "").split())
    return words.replace("|", "\\|").replace("<", "&lt;").replace("{", "\\{").replace("}", "\\}")


def _harnesses(spec: RuntimeEngineSpec) -> str:
    if spec.harnesses is None:
        return "any"
    return ", ".join(f"`{each}`" for each in spec.harnesses)


def reference_text() -> str:
    """The reference page: every runtime engine, the default first."""
    lines: list[str] = [
        "---",
        "title: Runtime engines",
        "---",
        "",
        "<!-- Generated by `python -m agentspecs.runtime_engines` from runtime-engines/*.yaml."
        " Do not edit. -->",
        "",
        "# Runtime engines",
        "",
        "What runs and hosts an agent, one spec each under `agentspecs/runtime-engines/`. An agent",
        "spec names one with `runtime_engine:`, on the line after `harness:`; a spec that names",
        "none, or another, is refused at load, and so is an engine asked to run a harness it does",
        "not run. The [harness](../harnesses) says which agent program turns the agent's loop; the",
        "runtime engine says what runs that program and keeps it alive. An engine that is not",
        "enabled stays listed here and is not one an agent may name. The first enabled one is",
        "the default: an agent built in code that names no engine runs there.",
        "",
        "| Engine | Id | Harnesses | Enabled |",
        "| --- | --- | --- | --- |",
    ]
    for spec in RUNTIME_ENGINE_CATALOGUE.values():
        lines.append(
            f"| [{_cell(spec.name)}]({spec.docs_url}) | `{spec.id}` | {_harnesses(spec)} "
            f"| {'yes' if spec.enabled else 'no'} |"
        )
    lines += ["", "## Each engine", ""]
    for spec in RUNTIME_ENGINE_CATALOGUE.values():
        lines += [
            f"### {spec.name} (`{spec.id}`)",
            "",
            _cell(spec.description).replace("\\|", "|"),
            "",
        ]
    return "\n".join(lines)


def main() -> None:
    SCHEMA_PATH.write_text(schema_text())
    if REFERENCE_PATH.parent.is_dir():
        REFERENCE_PATH.write_text(reference_text())


if __name__ == "__main__":
    main()


__all__ = [
    "DEFAULT_RUNTIME_ENGINE",
    "ENGINE_HARNESSES",
    "RUNTIME_ENGINES",
    "RUNTIME_ENGINE_CATALOGUE",
    "RuntimeEngineSpec",
    "agent_runtime_engine_problems",
    "enabled_engines",
    "get_runtime_engine",
    "json_schema",
    "load_runtime_engines",
    "reference_text",
    "schema_text",
]
