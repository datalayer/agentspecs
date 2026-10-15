# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""An agent's voice (VOICE.md VO-41): the ``voice:`` of an agent spec, the
block an application says under ``interface.voice``, checked the same way."""

from pathlib import Path

import pytest
import yaml

from agentspecs.apps import agent_voice_problems

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agentspecs" / "agents"


def test_every_agent_that_says_a_voice_says_one_of_the_catalogue():
    for path in sorted(AGENTS_DIR.rglob("*.yaml")):
        agent = yaml.safe_load(path.read_text()) or {}
        if "voice" in agent:
            assert agent_voice_problems(str(agent.get("id")), agent["voice"]) == [], path.name


def test_a_voice_of_the_catalogue_speaking_its_language_is_taken():
    assert (
        agent_voice_problems(
            "desk",
            {"enabled": True, "output": "always", "voice": "kokoro-ff-siwis", "language": "fr-FR"},
        )
        == []
    )
    # Unsaid, the voice is the language's first: nothing to check.
    assert agent_voice_problems("desk", {"enabled": True}) == []


@pytest.mark.parametrize(
    "block, said",
    [
        ({"enabled": True, "voice": "kokoro-lessac"}, "There is no voice named 'kokoro-lessac'"),
        ({"enabled": True, "voice": "kokoro-ff-siwis", "language": "en-US"}, "does not speak en-US"),
        ({"enabled": True, "input": "shout"}, "voice: input:"),
        ({"enabled": True, "colour": "blue"}, "colour is not a field of the spec"),
        ({"enabled": True, "language": "english"}, "voice: language:"),
        ("on", "voice is a mapping"),
    ],
)
def test_a_wrong_voice_is_refused_in_a_sentence(block, said):
    problems = agent_voice_problems("desk", block)
    assert len(problems) == 1
    assert problems[0].startswith("desk: ")
    assert said in problems[0]
