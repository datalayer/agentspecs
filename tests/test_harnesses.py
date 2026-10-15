# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The harnesses catalogue (SHIELD.md SH-01, §3.1) and its register (SH-04, §3.3)."""

from __future__ import annotations

import pathlib

import pytest
import yaml
from pydantic import ValidationError

from agentspecs import harnesses

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"


def test_the_catalogue_holds_the_harnesses_of_decision_4_and_one_framework():
    # Claude Code and Codex first, then goose and OpenCode; Gemini CLI with its tier
    # restriction; OpenHands; `custom` only as an organization's own; and one framework
    # exposing its agents over ACP (§2.5), fast-agent.
    assert set(harnesses.HARNESS_CATALOGUE) == {
        "claude-code", "codex", "gemini-cli", "goose", "opencode", "openhands", "fast-agent", "custom",
    }
    for spec in harnesses.HARNESS_CATALOGUE.values():
        if spec.id == "custom":
            assert spec.acp is None and not spec.enabled
        else:
            assert spec.acp is not None and spec.enabled and spec.acp.protocol_version == 1
            assert spec.acp.mcp is harnesses.McpLending.LEND
    assert harnesses.get_harness("claude-code").terms.served_to_third_parties is harnesses.ThirdPartyServing.API_KEY_ONLY
    assert harnesses.get_harness("codex").terms.served_to_third_parties is harnesses.ThirdPartyServing.API_KEY_ONLY
    assert "18 June 2026" in harnesses.get_harness("gemini-cli").terms.tier_restrictions
    assert "@agentclientprotocol/claude-agent-acp@" in " ".join(harnesses.get_harness("claude-code").acp.args)


def test_every_harness_has_a_register_entry_and_its_version_is_pinned():
    for spec in harnesses.HARNESS_CATALOGUE.values():
        entry = harnesses.HARNESS_REGISTER[spec.id]
        assert entry.licence == spec.terms.licence
        assert entry.served_to_third_parties is spec.terms.served_to_third_parties
        if spec.acp is not None:
            assert entry.version in " ".join([spec.acp.command, *spec.acp.args, *spec.requires.binaries])
    assert set(harnesses.HARNESS_REGISTER) == set(harnesses.HARNESS_CATALOGUE)


def test_a_harness_without_a_register_entry_does_not_load(tmp_path):
    register = yaml.safe_load(harnesses.REGISTER_PATH.read_text())
    register["entries"] = [entry for entry in register["entries"] if entry["harness"] != "codex"]
    (tmp_path / "register.yaml").write_text(yaml.safe_dump(register))
    for path in harnesses.HARNESSES_DIR.glob("*.yaml"):
        if path.name != "register.yaml":
            (tmp_path / path.name).write_text(path.read_text())
    with pytest.raises(harnesses.HarnessError, match="'codex' has no entry in the register"):
        harnesses.load_harnesses(tmp_path, tmp_path / "register.yaml")


def test_a_register_entry_that_disagrees_with_its_spec_does_not_load(tmp_path):
    register = yaml.safe_load(harnesses.REGISTER_PATH.read_text())
    for entry in register["entries"]:
        if entry["harness"] == "claude-code":
            entry["served_to_third_parties"] = "permitted"
    (tmp_path / "register.yaml").write_text(yaml.safe_dump(register))
    for path in harnesses.HARNESSES_DIR.glob("*.yaml"):
        if path.name != "register.yaml":
            (tmp_path / path.name).write_text(path.read_text())
    with pytest.raises(harnesses.HarnessError, match="third parties"):
        harnesses.load_harnesses(tmp_path, tmp_path / "register.yaml")


def test_the_schema_and_the_reference_are_the_specs():
    assert harnesses.SCHEMA_PATH.read_text() == harnesses.schema_text()
    if harnesses.REFERENCE_PATH.is_file():
        assert harnesses.REFERENCE_PATH.read_text() == harnesses.reference_text()


@pytest.mark.parametrize(
    "change,why",
    [
        ({"id": "Not An Id"}, "not a harness id"),
        ({"docs": "http://x.example"}, "https"),
        ({"acp": None}, "says how it is launched"),
        ({"requires": {"secrets": ["NOT_DECLARED"]}}, "not declared in env-vars"),
        ({"skills": {"format": "skill-md"}}, "says the directory"),
        ({"skills": {"format": "none", "dir": ".x/skills"}}, "names no directory"),
        ({"terms": {"served_to_third_parties": "maybe", "licence": "MIT"}}, "served_to_third_parties"),
        ({"acp": {"command": "x", "mcp": "steal"}}, "mcp"),
        ({"token": "x"}, "Extra inputs"),
    ],
)
def test_a_spec_refuses(change, why):
    good = yaml.safe_load((ROOT / "harnesses" / "claude-code.yaml").read_text())
    with pytest.raises(ValidationError, match=why):
        harnesses.HarnessSpec.model_validate({**good, **change})


def test_custom_names_no_command_and_is_not_offered():
    good = yaml.safe_load((ROOT / "harnesses" / "custom.yaml").read_text())
    with pytest.raises(ValidationError, match="names no command"):
        harnesses.HarnessSpec.model_validate({**good, "acp": {"command": "mine", "mcp": "lend"}})
    with pytest.raises(ValidationError, match="not offered"):
        harnesses.HarnessSpec.model_validate({**good, "enabled": True})


def test_every_agent_names_a_harness_it_can_ask_for():
    for path in sorted((ROOT / "agents").rglob("*.yaml")):
        spec = yaml.safe_load(path.read_text()) or {}
        assert harnesses.agent_harness_problems(spec) == [], path.name


def test_what_a_harness_cannot_honour_is_refused_in_a_sentence():
    assert harnesses.harness_problems("pydantic-ai", model="x", subagents=["a"]) == []
    assert harnesses.harness_problems("claude-code", model="bedrock:x") == []
    assert harnesses.harness_problems("claude-code", subagents=[{"id": "a"}]) == [
        "The harness 'claude-code' has its own subagents: drop `subagents:`."
    ]
    assert harnesses.harness_problems("custom") == [
        "The harness 'custom' names no command: an organization's own harness spec names it, and is never typed into a form."
    ]
    assert harnesses.harness_problems("nope")[0].startswith("There is no harness named 'nope': one of pydantic-ai, vercel-ai, ")
    # A harness that takes no model and reads no skills, as an organization's own could say.
    mute = harnesses.HARNESS_CATALOGUE["goose"].model_copy(
        update={
            "honours": harnesses.HarnessHonours(model=False, subagents=False),
            "skills": harnesses.HarnessSkills(format=harnesses.SkillsFormat.NONE),
        }
    )
    assert harnesses.harness_problems("goose", model="x", skills=["crawl"], catalogue={"goose": mute}) == [
        "The harness 'goose' does not take a model: drop `model:`.",
        "The harness 'goose' reads no skills: drop `skills:`.",
    ]
