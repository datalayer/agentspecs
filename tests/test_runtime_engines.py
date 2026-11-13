# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""``runtime_engine``: what runs and hosts an agent, ``datalayer`` or ``kagent``."""

from __future__ import annotations

import pathlib

import yaml

from agentspecs.runtime_engines import (
    DEFAULT_RUNTIME_ENGINE,
    RUNTIME_ENGINES,
    agent_runtime_engine_problems,
)

AGENTS = pathlib.Path(__file__).resolve().parent.parent / "agentspecs" / "agents"


def _agents() -> list[tuple[pathlib.Path, dict]]:
    return [(path, yaml.safe_load(path.read_text())) for path in sorted(AGENTS.glob("*.yaml"))]


def test_the_engines_are_datalayer_then_kagent():
    assert RUNTIME_ENGINES == ("datalayer", "kagent")
    assert DEFAULT_RUNTIME_ENGINE == "datalayer"


def test_every_agent_names_a_known_engine():
    agents = _agents()
    assert agents
    for path, spec in agents:
        assert agent_runtime_engine_problems(spec) == [], path.name


def test_every_agent_says_it_on_the_line_after_its_harness():
    for path in sorted(AGENTS.glob("*.yaml")):
        lines = path.read_text().splitlines()
        harness = [i for i, line in enumerate(lines) if line.startswith("harness:")]
        assert len(harness) == 1, path.name
        assert lines[harness[0] + 1].startswith("runtime_engine: "), path.name


def test_the_kagent_example_is_the_one_agent_on_kagent():
    on_kagent = [spec["id"] for _, spec in _agents() if spec["runtime_engine"] == "kagent"]
    assert on_kagent == ["example-kagent"]
    spec = yaml.safe_load((AGENTS / "example-kagent.yaml").read_text())
    assert spec["harness"] == "pydantic-ai"
    assert "/agents/{namespace}/{name}" in spec["description"]


def test_a_spec_without_an_engine_is_refused():
    assert agent_runtime_engine_problems({"id": "a", "harness": "pydantic-ai"}) == [
        "a: names no runtime_engine: one of datalayer, kagent, on the line after harness"
    ]
    assert agent_runtime_engine_problems({"id": "a", "runtime_engine": None}) != []


def test_an_unknown_engine_is_refused():
    assert agent_runtime_engine_problems({"id": "a", "runtime_engine": "agentcore"}) == [
        "a: there is no runtime_engine named 'agentcore': one of datalayer, kagent"
    ]


def test_kagent_runs_pydantic_ai_only():
    assert agent_runtime_engine_problems({"id": "a", "runtime_engine": "kagent"}) == []
    assert agent_runtime_engine_problems(
        {"id": "a", "harness": "vercel-ai", "runtime_engine": "kagent"}
    ) == ["a: the runtime_engine 'kagent' runs the harness pydantic-ai, not 'vercel-ai'"]
    assert (
        agent_runtime_engine_problems(
            {"id": "a", "harness": "codex", "runtime_engine": "datalayer"}
        )
        == []
    )
