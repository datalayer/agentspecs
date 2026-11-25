# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""``runtime_engine``: what runs and hosts an agent.

``datalayer``, ``kagent`` or ``agentcore``, each a spec of ``runtime-engines/``.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from pydantic import ValidationError

from agentspecs import runtime_engines
from agentspecs.runtime_engines import (
    DEFAULT_RUNTIME_ENGINE,
    ENGINE_HARNESSES,
    RUNTIME_ENGINE_CATALOGUE,
    RUNTIME_ENGINES,
    RuntimeEngineSpec,
    agent_runtime_engine_problems,
    get_runtime_engine,
    load_runtime_engines,
)

AGENTS = pathlib.Path(__file__).resolve().parent.parent / "agentspecs" / "agents"


def _agents() -> list[tuple[pathlib.Path, dict]]:
    return [(path, yaml.safe_load(path.read_text())) for path in sorted(AGENTS.glob("*.yaml"))]


def test_the_engines_are_datalayer_kagent_and_agentcore():
    assert RUNTIME_ENGINES == ("datalayer", "kagent", "agentcore")
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
        "a: names no runtime_engine: one of datalayer, kagent, agentcore, on the line after harness"
    ]
    assert agent_runtime_engine_problems({"id": "a", "runtime_engine": None}) != []


def test_an_unknown_engine_is_refused():
    assert agent_runtime_engine_problems({"id": "a", "runtime_engine": "lambda"}) == [
        "a: there is no runtime_engine named 'lambda': one of datalayer, kagent, agentcore"
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


def test_the_aws_steward_is_the_one_agent_on_agentcore():
    on_agentcore = [spec["id"] for _, spec in _agents() if spec["runtime_engine"] == "agentcore"]
    assert on_agentcore == ["worker-steward-aws"]


def test_agentcore_runs_pydantic_ai_only():
    assert agent_runtime_engine_problems({"id": "a", "runtime_engine": "agentcore"}) == []
    assert agent_runtime_engine_problems(
        {"id": "a", "harness": "claude-code", "runtime_engine": "agentcore"}
    ) == ["a: the runtime_engine 'agentcore' runs the harness pydantic-ai, not 'claude-code'"]


# The runtime engines as specs: one YAML each under `runtime-engines/`, the
# one source the engines' ids, names and harnesses are read from.

ENGINES = pathlib.Path(__file__).resolve().parent.parent / "agentspecs" / "runtime-engines"


def test_the_engines_are_read_from_their_specs():
    assert sorted(path.stem for path in ENGINES.glob("*.yaml")) == sorted(RUNTIME_ENGINES)
    assert tuple(RUNTIME_ENGINE_CATALOGUE) == RUNTIME_ENGINES
    assert [spec.position for spec in RUNTIME_ENGINE_CATALOGUE.values()] == [1, 2, 3]


def test_the_engines_are_named_datalayer_kagent_and_aws_agentcore():
    assert {spec.id: spec.name for spec in RUNTIME_ENGINE_CATALOGUE.values()} == {
        "datalayer": "Datalayer",
        "kagent": "Kagent",
        "agentcore": "AWS AgentCore",
    }
    for spec in RUNTIME_ENGINE_CATALOGUE.values():
        assert spec.enabled, spec.id
        assert "KAgent" not in spec.description, spec.id


def test_the_harnesses_each_engine_runs_come_from_its_spec():
    assert ENGINE_HARNESSES == {"kagent": ("pydantic-ai",), "agentcore": ("pydantic-ai",)}
    assert get_runtime_engine("datalayer").harnesses is None
    assert get_runtime_engine("lambda") is None


def test_every_harness_an_engine_names_is_a_harness():
    from agentspecs.harnesses import BUILTIN_HARNESSES, HARNESS_CATALOGUE

    for spec in RUNTIME_ENGINE_CATALOGUE.values():
        for harness in spec.harnesses or []:
            assert harness in BUILTIN_HARNESSES or harness in HARNESS_CATALOGUE, (spec.id, harness)


def test_the_schema_and_the_reference_page_are_up_to_date():
    assert runtime_engines.SCHEMA_PATH.read_text() == runtime_engines.schema_text()
    if runtime_engines.REFERENCE_PATH.parent.is_dir():
        assert runtime_engines.REFERENCE_PATH.read_text() == runtime_engines.reference_text()


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ({"id": "Not An Id"}, "not a runtime engine id"),
        ({"docs_url": "http://kagent.dev"}, "https address"),
        ({"harnesses": []}, "say null for any"),
        ({"harnesses": ["pydantic-ai", "pydantic-ai"]}, "listed twice"),
        ({"position": 0}, "greater than or equal to 1"),
        ({"label": "KAgent"}, "Extra inputs are not permitted"),
    ],
)
def test_a_malformed_engine_is_refused(change, said):
    spec = yaml.safe_load((ENGINES / "kagent.yaml").read_text())
    with pytest.raises(ValidationError, match=said):
        RuntimeEngineSpec.model_validate({**spec, **change})


def test_an_engine_without_harnesses_said_is_refused():
    spec = yaml.safe_load((ENGINES / "datalayer.yaml").read_text())
    del spec["harnesses"]
    with pytest.raises(ValidationError, match="harnesses"):
        RuntimeEngineSpec.model_validate(spec)


def test_a_directory_whose_positions_clash_is_refused(tmp_path):
    for name in ("datalayer", "kagent"):
        spec = yaml.safe_load((ENGINES / f"{name}.yaml").read_text())
        spec["position"] = 1
        (tmp_path / f"{name}.yaml").write_text(yaml.safe_dump(spec))
    with pytest.raises(ValueError, match="positions 1 to 2"):
        load_runtime_engines(tmp_path)


def test_a_file_named_for_another_engine_is_refused(tmp_path):
    (tmp_path / "other.yaml").write_text((ENGINES / "kagent.yaml").read_text())
    with pytest.raises(ValueError, match="named for 'other'"):
        load_runtime_engines(tmp_path)


# ---- review of 0.1.21 ------------------------------------------------------------------------


def _engines(tmp_path, **changes):
    """A copy of the catalogue's engines, some fields changed by engine id."""
    for path in sorted(ENGINES.glob("*.yaml")):
        spec = yaml.safe_load(path.read_text())
        spec.update(changes.get(spec["id"], {}))
        (tmp_path / path.name).write_text(yaml.safe_dump(spec))
    return tmp_path


def test_a_disabled_engine_stays_in_the_catalogue_and_is_not_one_an_agent_may_name(tmp_path):
    """`enabled: false` keeps the spec and takes the engine out of the allowed ones."""
    catalogue = runtime_engines.load_runtime_engines(_engines(tmp_path, kagent={"enabled": False}))
    assert list(catalogue) == ["datalayer", "kagent", "agentcore"]
    assert runtime_engines.enabled_engines(catalogue) == ("datalayer", "agentcore")


def test_the_default_is_the_first_enabled_engine(tmp_path):
    catalogue = runtime_engines.load_runtime_engines(
        _engines(tmp_path, datalayer={"enabled": False})
    )
    assert runtime_engines.enabled_engines(catalogue)[0] == "kagent"


def test_a_catalogue_with_no_enabled_engine_is_refused(tmp_path):
    off = {engine: {"enabled": False} for engine in ("datalayer", "kagent", "agentcore")}
    with pytest.raises(ValueError, match="no runtime engine is enabled"):
        runtime_engines.load_runtime_engines(_engines(tmp_path, **off))


def test_an_agent_naming_a_disabled_engine_is_refused_in_a_sentence(monkeypatch):
    spec = {"id": "an-agent", "harness": "pydantic-ai", "runtime_engine": "kagent"}
    assert runtime_engines.agent_runtime_engine_problems(spec) == []
    monkeypatch.setattr(runtime_engines, "RUNTIME_ENGINES", ("datalayer", "agentcore"))
    assert runtime_engines.agent_runtime_engine_problems(spec) == [
        "an-agent: the runtime_engine 'kagent' is not enabled: one of datalayer, agentcore"
    ]
    # An engine nobody knows is still told apart from one that is switched off.
    unknown = runtime_engines.agent_runtime_engine_problems({**spec, "runtime_engine": "lambda"})
    assert unknown == [
        "an-agent: there is no runtime_engine named 'lambda': one of datalayer, agentcore"
    ]
    # And a spec naming none is offered the enabled ones alone.
    assert "kagent" not in runtime_engines.agent_runtime_engine_problems({"id": "an-agent"})[0]


def test_the_engines_an_agent_may_name_are_the_enabled_ones():
    assert RUNTIME_ENGINES == tuple(
        spec.id for spec in RUNTIME_ENGINE_CATALOGUE.values() if spec.enabled
    )
    assert runtime_engines.DEFAULT_RUNTIME_ENGINE == RUNTIME_ENGINES[0]


@pytest.mark.parametrize(
    "change",
    [
        {"id": "Not An Id"},
        {"docs_url": "http://kagent.dev"},
        {"harnesses": []},
        {"harnesses": ["pydantic-ai", "pydantic-ai"]},
        {"position": 0},
        {"label": "KAgent"},
        {"name": ""},
    ],
)
def test_what_the_loader_refuses_the_schema_refuses_too(change):
    """The published schema says every rule the loader holds a spec to."""
    import jsonschema

    spec = yaml.safe_load((ENGINES / "kagent.yaml").read_text())
    validator = jsonschema.Draft202012Validator(runtime_engines.json_schema())
    assert list(validator.iter_errors(spec)) == []
    with pytest.raises(ValidationError):
        RuntimeEngineSpec.model_validate({**spec, **change})
    assert list(validator.iter_errors({**spec, **change})), change


def test_every_engine_of_the_catalogue_satisfies_the_schema():
    import jsonschema

    validator = jsonschema.Draft202012Validator(runtime_engines.json_schema())
    for path in sorted(ENGINES.glob("*.yaml")):
        assert list(validator.iter_errors(yaml.safe_load(path.read_text()))) == [], path.name


@pytest.mark.parametrize("value", [[], ["kagent"], {"id": "kagent"}, 3])
def test_a_runtime_engine_that_is_no_name_is_refused_in_the_same_sentence(value):
    """A list or a mapping where the engine's name goes is a problem said, never a crash."""
    problems = runtime_engines.agent_runtime_engine_problems(
        {"id": "an-agent", "runtime_engine": value}
    )
    assert len(problems) == 1 and "there is no runtime_engine named" in problems[0]
