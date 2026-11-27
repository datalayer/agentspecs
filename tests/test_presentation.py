# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Presentations: what an agent or an application is, as one Markdown document."""

from pathlib import Path

import pytest
import yaml

from agentspecs.apps import APP_CATALOGUE, AppError, json_schema, parse_app
from agentspecs.presentation import (
    PRESENTATION_MAX,
    TAGLINE_MAX,
    PresentationAction,
    presentation_blocks,
    presentation_problems,
    tagline_problems,
)

AGENTS = Path(__file__).resolve().parents[1] / "agentspecs" / "agents"

#: The seed agents and their public demos.
DEMOS = {
    "marketer-tryout": "worker-marketer",
    "shopper-tryout": "worker-shopper",
    "accountant-tryout": "worker-accountant",
    "traveller-tryout": "worker-traveller",
    "terra-tryout": "worker-terra",
    "aws-steward-tryout": "worker-steward-aws",
    "data-analyst-tryout": "worker-data-analyst",
    "functional-analyst-tryout": "worker-functional-analyst",
}


def agent(agent_id: str) -> dict:
    return yaml.safe_load((AGENTS / f"{agent_id}.yaml").read_text())


def raw(app_id: str = "marketer-tryout") -> dict:
    return yaml.safe_load((AGENTS.parent / "apps" / f"{app_id}.yaml").read_text())


def one_line(text: str) -> str:
    return " ".join(text.split())


def test_a_document_is_read_into_its_blocks():
    blocks = presentation_blocks(
        "What it is,\nin a sentence.\n\n"
        "- Does this\n- Does that,\n  on two lines\n\n"
        "*Try it here: nothing\nis posted.*\n\n"
        "**[Start building](/signin)**\n[In slides](/decks/agents)\n"
    )
    assert [block.kind for block in blocks] == ["paragraph", "list", "note", "actions"]
    assert blocks[0].text == "What it is, in a sentence."
    assert blocks[1].items == ("Does this", "Does that, on two lines")
    assert blocks[2].text == "Try it here: nothing is posted."
    assert blocks[3].actions == (
        PresentationAction(label="Start building", href="/signin", primary=True),
        PresentationAction(label="In slides", href="/decks/agents"),
    )


def test_a_paragraph_with_words_beside_its_links_is_a_paragraph():
    (block,) = presentation_blocks("Read [the guide](/docs/guide) first.")
    assert block.kind == "paragraph"
    # Emphasis inside a sentence is not a note, nor is bold.
    assert [block.kind for block in presentation_blocks("It *never* posts.\n\n**Bold.**")] == ["paragraph", "paragraph"]


def test_html_headings_and_length_are_refused():
    assert presentation_problems("A paragraph.\n\n- An item") == []
    assert presentation_problems("") == []
    assert presentation_problems("<script>alert(1)</script>") == ["a presentation is Markdown: raw HTML is refused"]
    assert presentation_problems("# Marketer\n\nPlans.") == [
        "a presentation has no heading: its name and its emoji are the heading above it"
    ]
    assert presentation_problems("a" * (PRESENTATION_MAX + 1)) == [
        f"a presentation is {PRESENTATION_MAX} characters at most, this one is {PRESENTATION_MAX + 1}"
    ]
    assert tagline_problems("Plans, drafts, reads the replies") == []
    assert tagline_problems("a\nb") == ["a tagline is one line"]
    assert tagline_problems("a" * (TAGLINE_MAX + 1)) == [f"a tagline is {TAGLINE_MAX} characters at most, this one is {TAGLINE_MAX + 1}"]


def test_the_appspec_takes_a_presentation_and_refuses_html():
    app = parse_app({**raw(), "presentation": "\nWhat it is.\n\n- Does this\n\n"})
    assert app.presentation == "What it is.\n\n- Does this"
    assert parse_app({key: value for key, value in raw().items() if key != "presentation"}).presentation == ""
    with pytest.raises(AppError, match="raw HTML is refused"):
        parse_app({**raw(), "presentation": "<b>Bold</b>"})
    with pytest.raises(AppError, match="has no heading"):
        parse_app({**raw(), "presentation": "## Marketer"})
    assert json_schema()["properties"]["presentation"]["maxLength"] == PRESENTATION_MAX


@pytest.mark.parametrize("app_id, agent_id", sorted(DEMOS.items()))
def test_a_seed_agent_presents_itself(app_id: str, agent_id: str):
    spec = agent(agent_id)
    assert tagline_problems(spec["tagline"]) == []
    assert presentation_problems(spec["presentation"]) == []
    blocks = presentation_blocks(spec["presentation"])
    assert [block.kind for block in blocks] == ["paragraph", "list", "actions"]
    # Its paragraph is its description, as it stands.
    assert blocks[0].text == one_line(spec["description"])
    assert len(blocks[1].items) == 5
    # Where to read more: one link, none the main one.
    assert [action.primary for action in blocks[2].actions] == [False]


@pytest.mark.parametrize("app_id, agent_id", sorted(DEMOS.items()))
def test_a_demo_repeats_its_agent_then_says_what_it_is(app_id: str, agent_id: str):
    app = APP_CATALOGUE[app_id]
    assert app.agent.split(":")[0] == agent_id
    own = presentation_blocks(agent(agent_id)["presentation"])
    blocks = presentation_blocks(app.presentation)
    assert [block.kind for block in blocks] == ["paragraph", "list", "note", "actions"]
    # Its agent's paragraph and list, word for word.
    assert blocks[:2] == own[:2]
    assert blocks[2].text.startswith("Try it here: ")
    # Start building, the main button, then where its agent says to read more.
    assert blocks[3].actions == (
        PresentationAction(label="Start building", href="/signin", primary=True),
        *own[2].actions,
    )


def test_no_other_application_presents_itself_yet():
    assert sorted(app.id for app in APP_CATALOGUE.values() if app.presentation) == sorted(DEMOS)
