# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Scenes: a team, staged (LOOP A-11, A-13).

The catalogue loads, the four scenes of the home page are what the plan says,
and what a scene promises is checked in sentences.
"""

from __future__ import annotations

import copy
import json
import pathlib
from typing import Any, Dict

import pytest
import yaml

import agentspecs.scenes
from agentspecs.actions import ActionClass
from agentspecs.apps import APP_CATALOGUE
from agentspecs.scenes import (
    SCENE_CATALOGUE,
    SCENE_SCHEMA,
    SCHEMA_PATH,
    AnswerKind,
    SceneError,
    SceneSpec,
    Watchers,
    dump_scene,
    get_scene,
    json_schema,
    list_scenes,
    parse_line,
    parse_scene,
    scene_problems,
    scene_setup,
    scenes_staging,
    schema_text,
)
from agentspecs.teams import TeamPlace, TeamProtocol, get_team

SCENES_DIR = pathlib.Path(agentspecs.scenes.__file__).parent

#: The four scenes of the home page (LOOP A-08, A-13): the team each stages,
#: its entry, the members on a runtime, and the system on stage.
HOME_SCENES = {
    "sales-and-accounting": ("sales", ["accounting"], "odoo-accounting"),
    "month-end-close": ("month-end-close", ["month-end-close"], "odoo-accounting"),
    "crop-monitoring": ("crop-monitoring", ["crop-monitoring"], "earthdata"),
    "disaster-assessment": ("event-response", ["disaster-assessment", "change-detection"], "earthdata"),
}


def raw(scene_id: str) -> Dict[str, Any]:
    """A scene of the catalogue as its file holds it, to change one thing of."""
    return copy.deepcopy(yaml.safe_load((SCENES_DIR / f"{scene_id}.yaml").read_text()))


def problems(**changes: Any) -> list:
    """The problems of Sales & Accounting with some of its fields replaced."""
    document = {**raw("sales-and-accounting"), **changes}
    return scene_problems(parse_scene(document))


def _minimal_cast(**overrides: Any) -> Dict[str, Any]:
    """The smallest scene written with its cast inline."""
    document = {
        "id": "pair",
        "name": "Pair",
        "emoji": "\U0001f3ad",
        "cast": [
            {"member": "front", "app": "sales:0.0.1", "role": "initiator", "runs_in": "browser",
             "talks_to": [{"member": "books", "over": "a2a"}], "persona": {"name": "Front"}},
            {"member": "books", "app": "accounting:0.0.1", "runs_in": "runtime"},
        ],
        "script": [
            {"id": "one", "cue": {"say": "Hello?"}, "expect": "An answer.",
             "moves": [{"who": "front", "asks": "books", "over": "a2a"}, {"who": "front", "answers": "words"}]},
        ],
        "deployment": {"addresses": {"books": "BOOKS_A2A_URL"}},
    }
    document.update(overrides)
    return document


# --- the catalogue ----------------------------------------------------------------------


def test_the_catalogue_holds_the_four_scenes_of_the_home_page() -> None:
    assert set(SCENE_CATALOGUE) == set(HOME_SCENES)
    assert get_scene("sales-and-accounting:0.0.1") is SCENE_CATALOGUE["sales-and-accounting"]
    assert get_scene("no-such-scene") is None
    assert [scene.id for scene in list_scenes("earthdata")] == ["crop-monitoring", "disaster-assessment"]
    assert [scene.id for scene in scenes_staging("disaster-assessment:0.0.1")] == ["disaster-assessment"]
    for scene in SCENE_CATALOGUE.values():
        assert scene.schema_ == SCENE_SCHEMA
        assert scene_problems(scene) == [], scene.id


def test_every_scene_file_is_named_for_its_id() -> None:
    for path in SCENES_DIR.glob("*.yaml"):
        assert yaml.safe_load(path.read_text())["id"] == path.stem


def test_every_scene_has_a_face_of_its_own() -> None:
    """A scene's face is one emoji, the scene's own: no default, none twice, none a member's."""
    faces = [scene.emoji for scene in SCENE_CATALOGUE.values()]
    assert len(set(faces)) == len(faces) and "\U0001f440" not in faces
    for scene in SCENE_CATALOGUE.values():
        assert scene.name and scene.description.strip() and scene.icon, scene.id
        members = [member.persona.face for member in scene.cast_of()]
        assert all(members), scene.id
        assert scene.emoji not in members, scene.id
        assert scene.emoji not in {app.emoji for app in APP_CATALOGUE.values()}, scene.id


def test_the_four_scenes_stage_their_teams() -> None:
    """LOOP A-13: each with its setting, four beats, stage directions, a visitor audience and a rehearsal."""
    for scene_id, (entry, on_runtime, system) in HOME_SCENES.items():
        scene = SCENE_CATALOGUE[scene_id]
        team = scene.team_of()
        assert team is get_team(scene_id) and scene.entry_of() == entry, scene_id
        # The cast is the team's, with a persona and a brief each.
        cast = scene.cast_of()
        assert [member.member for member in cast] == [member.id for member in team.agents], scene_id
        assert all(member.persona.name and member.persona.line and member.brief for member in cast), scene_id
        # The setting: one system, what it holds, and the line under the title.
        assert [item.id for item in scene.setting.systems] == [system], scene_id
        assert scene.setting.systems[0].shown_as and scene.setting.systems[0].holds, scene_id
        assert scene.setting.assumes.strip(), scene_id
        # Four beats, their cues the entry's starters, each with moves, what it shows and a narration.
        assert len(scene.script) == 4, scene_id
        front = APP_CATALOGUE[entry]
        assert scene.cues() == [starter.message for starter in front.interface.starters], scene_id
        for beat in scene.script:
            assert beat.moves and beat.narration and beat.shown, (scene_id, beat.id)
            assert any(move.who == entry and not move.asks for move in beat.moves), (scene_id, beat.id)
            assert any(move.over is TeamProtocol.MCP and move.tool for move in beat.moves), (scene_id, beat.id)
        # Stage directions place every member; the entry's balloon opens first.
        assert set(scene.stage.positions) == {member.id for member in team.agents}, scene_id
        assert scene.stage.opens_first == entry and scene.stage.rests_after, scene_id
        # Visitors may watch, within a ceiling.
        assert scene.audience.who is Watchers.VISITORS, scene_id
        assert scene.audience.ceiling_per_ask > 0 and scene.audience.asks_a_day > 0, scene_id
        # A rehearsal of every beat, each starting with the audience and ending on an answer.
        assert [item.beat for item in scene.rehearsal.beats] == [beat.id for beat in scene.script], scene_id
        for item in scene.rehearsal.beats:
            lines = item.parsed()
            assert lines[0].who == "You" and lines[-1].is_answer and item.within, (scene_id, item.beat)
        assert scene.rehearsal.verified.unverified, scene_id
        # Every member on a runtime has the variable its address is read from, as the page names it.
        assert list(scene.deployment.addresses) == on_runtime, scene_id
        for member_id, variable in scene.deployment.addresses.items():
            assert team.member(member_id).runs_in is TeamPlace.RUNTIME, (scene_id, member_id)
            upper = lambda text: text.upper().replace("-", "_")  # noqa: E731
            expected = (
                "DATALAYER_DEMO_TEAM_ACCOUNTING_A2A_URL"
                if (scene_id, member_id) == ("sales-and-accounting", "accounting")
                else f"DATALAYER_DEMO_SCENE_{upper(scene_id)}_{upper(member_id)}_A2A_URL"
            )
            assert variable == expected, (scene_id, member_id)
        assert scene.deployment.account == "demo" and scene.deployment.page == "/", scene_id


def test_a_scene_says_what_each_beat_shows() -> None:
    sales = SCENE_CATALOGUE["sales-and-accounting"]
    assert sales.script[0].shown == [AnswerKind.TABLE]
    crop = SCENE_CATALOGUE["crop-monitoring"]
    assert crop.script[0].shown == [AnswerKind.CHART, AnswerKind.WORDS]
    # Unsaid, what the beat shows is what its answers to the audience are.
    beat = crop.script[0].model_copy(update={"shows": []})
    assert beat.shown == [AnswerKind.CHART, AnswerKind.WORDS]
    assert sales.script[0].branch[0].decision == "the books hold no open invoice"


def test_each_scene_of_the_home_page_answers_four_kinds() -> None:
    """STUDIO H-02, H-03: the starters lead to the sources, a table, a chart and an approval."""
    wanted = {AnswerKind.SOURCES, AnswerKind.TABLE, AnswerKind.CHART, AnswerKind.APPROVAL}
    for scene_id in HOME_SCENES:
        shown = {kind for beat in SCENE_CATALOGUE[scene_id].script for kind in beat.shown}
        assert wanted <= shown, scene_id
        # The approval is answered by a member that only reads: it is asked, not done.
        [approval] = [beat for beat in SCENE_CATALOGUE[scene_id].script if AnswerKind.APPROVAL in beat.shown]
        assert all(move.does in (None, ActionClass.READ) for move in approval.moves), scene_id
    assert parse_line("Accounting: an approval").kind is AnswerKind.APPROVAL
    assert parse_line("Crop monitoring: sources").kind is AnswerKind.SOURCES


def test_what_each_scene_needs_is_said_as_setup() -> None:
    assert scene_setup(SCENE_CATALOGUE["crop-monitoring"]) == [
        "The agent 'worker-crop-monitoring:0.0.1' is not enabled.",
    ]
    assert "The MCP server 'odoo-accounting:0.0.1' is not enabled." in scene_setup(
        SCENE_CATALOGUE["month-end-close"]
    )


# --- reading and writing ---------------------------------------------------------------


def test_a_scene_writes_the_document_it_was_read_from() -> None:
    for scene_id, scene in SCENE_CATALOGUE.items():
        document = dump_scene(scene)
        assert list(document)[0] == "schema" and document["schema"] == SCENE_SCHEMA
        assert "version" not in document and "pace" not in document.get("stage", {}).get("transcript", {})
        again = parse_scene(document)
        assert again == scene and dump_scene(again) == document, scene_id
        # The file says nothing the spec does not read back.
        assert parse_scene(raw(scene_id)) == scene, scene_id


def test_another_schema_or_an_unknown_key_is_refused_in_a_sentence() -> None:
    with pytest.raises(SceneError, match="schema: schema 'loop.scene/v2' is not one this package reads"):
        parse_scene({**raw("month-end-close"), "schema": "loop.scene/v2"})
    with pytest.raises(SceneError, match="month-end-close: curtain is not a field of the spec"):
        parse_scene({**raw("month-end-close"), "curtain": "red"})
    with pytest.raises(SceneError, match="the scene stages nobody"):
        parse_scene({"id": "x", "name": "X", "emoji": "\U0001f3ad"})
    with pytest.raises(SceneError, match="emoji: a scene's `emoji` is one emoji"):
        parse_scene({**raw("month-end-close"), "emoji": "books"})
    with pytest.raises(SceneError, match="a cue is one of `say`, `schedule` or `event`"):
        parse_scene({**raw("month-end-close"), "script": [{"id": "x", "cue": {}, "expect": "y"}]})
    with pytest.raises(SceneError, match="answers the audience: say what kind of answer"):
        parse_scene(
            {**raw("month-end-close"), "script": [{"id": "x", "cue": {"say": "?"}, "expect": "y", "moves": [{"who": "a"}]}]}
        )
    with pytest.raises(SceneError, match="a tool is asked over mcp"):
        parse_scene(
            {
                **raw("month-end-close"),
                "script": [
                    {"id": "x", "cue": {"say": "?"}, "expect": "y",
                     "moves": [{"who": "a", "asks": "b", "over": "a2a", "tool": "t"}]}
                ],
            }
        )
    with pytest.raises(SceneError, match="rests_after"):
        parse_scene({**raw("month-end-close"), "stage": {"rests_after": "ten minutes"}})
    with pytest.raises(SceneError, match="is read from a variable"):
        parse_scene({**raw("month-end-close"), "deployment": {"addresses": {"month-end-close": "http://x"}}})
    with pytest.raises(SceneError, match="is neither an ask"):
        parse_scene({**raw("month-end-close"), "rehearsal": {"beats": [{"beat": "accruals", "lines": ["hello"]}]}})


def test_the_transcript_grammar_is_read() -> None:
    asked = parse_line("Sales → Accounting")
    assert (asked.who, asked.whom, asked.detail, asked.is_answer) == ("Sales", "Accounting", "", False)
    tool = parse_line("Accounting → Odoo: odoo_accounting_*")
    assert (tool.whom, tool.detail) == ("Odoo", "odoo_accounting_*")
    answer = parse_line("Accounting: a table")
    assert answer.is_answer and answer.kind is AnswerKind.TABLE
    assert parse_line("Sales: the figures, as answered").kind is None


def test_the_json_schema_is_the_one_beside_the_specs() -> None:
    schema = json_schema()
    assert schema["title"] == "Scene spec" and schema["additionalProperties"] is False
    assert {"schema", "id", "name", "emoji", "team", "cast", "setting", "script", "stage", "audience", "rehearsal", "deployment"} <= set(
        schema["properties"]
    )
    assert schema["properties"]["schema"]["const"] == SCENE_SCHEMA
    assert "as" in schema["$defs"]["SceneSystem"]["properties"]
    assert json.loads(SCHEMA_PATH.read_text())["$id"].endswith(f"{SCENE_SCHEMA}.json")
    assert SCHEMA_PATH.read_text() == schema_text(), "run `python -m agentspecs.scenes`"


def test_the_reference_says_every_field_and_is_the_one_in_the_docs() -> None:
    from agentspecs.scenes.reference import EXTRA_EXAMPLES, REFERENCE_PATH, reference_markdown

    page = reference_markdown()
    schema = json_schema()
    for name in schema["properties"]:
        assert f"| `{name}`" in page and f"### `{name}`" in page, name
    for name in schema["$defs"]:
        assert name in page, name
    for key, value in EXTRA_EXAMPLES.items():
        parse_scene({**raw("sales-and-accounting"), key: value})
    if REFERENCE_PATH.exists():
        assert REFERENCE_PATH.read_text() == page, "run `python -m agentspecs.scenes`"


# --- a cast written inline --------------------------------------------------------------


def test_a_cast_written_inline_makes_a_team() -> None:
    scene = parse_scene(_minimal_cast())
    assert scene_problems(scene) == []
    team = scene.team_of()
    assert team.id == "pair" and team.entry == "front" and team.supervisor.app == "sales:0.0.1"
    assert team.links() == [("front", "books", TeamProtocol.A2A)]
    cast = scene.cast_of()
    # A persona is filled from the application when the cast says nothing.
    assert [(member.persona.name, member.persona.face) for member in cast] == [("Front", "\U0001f4bc"), ("Accounting", "\U0001f9fe")]
    # The entry is the initiator unless said.
    assert parse_scene(_minimal_cast(entry="books")).entry_of() == "books"
    # A cast that makes no team says why, in the team's words.
    broken = _minimal_cast()
    broken["cast"][0]["talks_to"] = [{"member": "nobody"}]
    assert scene_problems(parse_scene(broken)) == [
        "Its cast makes no team: member 'front' talks to 'nobody', which is not a member of team 'pair'"
    ]
    with pytest.raises(SceneError, match="enters at 'ghost', which is not in its cast"):
        parse_scene(_minimal_cast(entry="ghost")).team_of()


# --- what is refused, in sentences -------------------------------------------------------


def test_a_team_the_catalogue_does_not_have_is_a_problem() -> None:
    assert problems(team="no-such-team:0.0.1") == ["There is no team named 'no-such-team:0.0.1'."]


def test_a_cast_member_not_in_the_team_is_refused() -> None:
    document = raw("sales-and-accounting")
    document["cast"].append({"member": "marketing", "persona": {"name": "Marketing"}})
    assert "The cast names 'marketing', which is not a member of the team 'sales-and-accounting'." in scene_problems(
        parse_scene(document)
    )
    # On a staged team, a cast member says its persona and its brief, nothing of what it is.
    document = raw("sales-and-accounting")
    document["cast"][0]["app"] = "sales:0.0.1"
    assert scene_problems(parse_scene(document)) == [
        "The cast member 'sales' is the team's: it says its persona and its brief, nothing of what it is."
    ]
    assert problems(entry="ghost")[0] == "The scene enters at 'ghost', which is not in its cast."


def test_a_scene_wearing_a_members_face_is_refused() -> None:
    assert problems(emoji="\U0001f9fe") == ["The scene wears \U0001f9fe, a member's face: a scene has a face of its own."]


def test_the_setting_names_systems_the_cast_reaches() -> None:
    assert problems(setting={"systems": [{"server": "no-such-server"}]}) == [
        "There is no MCP server named 'no-such-server'.",
        "Beat 'open-invoices': 'accounting' asks 'odoo' over mcp, which is not a system of the scene.",
        "Beat 'aged-receivables': 'accounting' asks 'odoo' over mcp, which is not a system of the scene.",
        "Beat 'largest-balance': 'accounting' asks 'odoo' over mcp, which is not a system of the scene.",
        "Beat 'payment-reminders': 'accounting' asks 'odoo' over mcp, which is not a system of the scene.",
        "The rehearsal of 'open-invoices' names 'Odoo', which is not on stage.",
        "The rehearsal of 'aged-receivables' names 'Odoo', which is not on stage.",
        "The rehearsal of 'largest-balance' names 'Odoo', which is not on stage.",
        "The rehearsal of 'payment-reminders' names 'Odoo', which is not on stage.",
    ]
    document = raw("sales-and-accounting")
    document["setting"]["systems"].append({"server": "earthdata:0.0.1"})
    assert scene_problems(parse_scene(document)) == [
        "The system 'earthdata' (earthdata) is on stage, and no member of the cast reaches it."
    ]
    document = raw("sales-and-accounting")
    document["setting"]["frames"] = ["no-such-frame"]
    assert scene_problems(parse_scene(document)) == ["There is no Frame named 'no-such-frame'."]


def test_a_move_is_by_a_cast_member_to_one_it_may_ask() -> None:
    def beat(*moves: Dict[str, Any]) -> list:
        document = raw("sales-and-accounting")
        document["script"] = [{"id": "x", "cue": {"say": "?"}, "expect": "y", "moves": list(moves)}]
        document["rehearsal"] = {}
        return scene_problems(parse_scene(document))

    front = {"who": "sales", "answers": "words"}
    assert beat({"who": "nobody", "answers": "words"}, front) == ["Beat 'x': 'nobody' moves, and is not in the cast."]
    assert beat({"who": "sales", "asks": "sales", "over": "mcp"}, front) == [
        "Beat 'x': 'sales' asks 'sales' over mcp, which is not a system of the scene."
    ]
    assert beat({"who": "sales", "asks": "odoo", "over": "a2a"}, front) == [
        "Beat 'x': 'sales' asks 'odoo' over a2a, a system: a system is asked over mcp."
    ]
    assert beat({"who": "sales", "asks": "odoo", "over": "mcp", "tool": "odoo_accounting_list_invoices"}, front) == [
        "Beat 'x': 'sales' asks 'odoo' (odoo-accounting), which it reaches through no connection."
    ]
    assert beat({"who": "sales", "asks": "marketing"}, front) == ["Beat 'x': 'sales' asks 'marketing', which is not in the cast."]
    assert beat({"who": "accounting", "asks": "sales", "over": "a2a"}, front) == [
        "Beat 'x': 'accounting' asks 'sales', which the team does not have it talk to."
    ]
    # A cue nobody answers: no move is the entry's.
    assert beat({"who": "accounting", "answers": "table"}) == [
        "Beat 'x': its cue is answered by nobody — no move is the entry's ('sales')."
    ]
    # A tool no connection offers, one the server does not have, and one asked to read that writes.
    assert beat({"who": "accounting", "asks": "Odoo", "over": "mcp", "tool": "odoo_accounting_nothing"}, front) == [
        "Beat 'x': 'accounting' asks 'Odoo' for 'odoo_accounting_nothing', which odoo-accounting does not offer."
    ]
    assert beat(
        {"who": "accounting", "asks": "odoo", "over": "mcp", "tool": "odoo_accounting_post_invoice", "does": "read"}, front
    ) == ["Beat 'x': 'accounting' asks 'odoo' for 'odoo_accounting_post_invoice' to read, and it writes."]
    assert beat({"who": "accounting", "asks": "odoo", "over": "mcp", "tool": "odoo_accounting_*", "does": "read"}, front) == []


def test_a_tool_a_connection_does_not_offer_is_refused() -> None:
    """A connection with `only` offers some tools: a move or a rehearsal naming another is refused."""
    from agentspecs.apps import AppConnection

    accounting = APP_CATALOGUE["accounting"]
    narrowed = accounting.model_copy(
        update={"connections": [AppConnection(server="odoo-accounting:0.0.1", only=["odoo_accounting_list_*"])]}
    )
    APP_CATALOGUE["accounting"] = narrowed
    try:
        found = problems()
    finally:
        APP_CATALOGUE["accounting"] = accounting
    assert found == [
        "Beat 'aged-receivables': 'accounting' asks 'odoo' for 'odoo_accounting_aged_balance', a tool no connection of Accounting offers.",
        "Beat 'payment-reminders': 'accounting' asks 'odoo' for 'odoo_accounting_aged_balance', a tool no connection of Accounting offers.",
        "The rehearsal of 'aged-receivables' expects 'odoo_accounting_aged_balance', a tool no connection of Accounting offers.",
        "The rehearsal of 'payment-reminders' expects 'odoo_accounting_aged_balance', a tool no connection of Accounting offers.",
    ]


def test_a_branch_goes_on_to_a_beat_of_the_script() -> None:
    document = raw("sales-and-accounting")
    document["script"][0]["branch"][0]["then"] = "curtain"
    assert scene_problems(parse_scene(document)) == ["Beat 'open-invoices': its branch goes on to 'curtain', which is no beat."]
    document["script"][0]["branch"][0]["then"] = "largest-balance"
    assert scene_problems(parse_scene(document)) == []


def test_the_stage_places_the_cast() -> None:
    assert problems(stage={"positions": {"ghost": {"x": 0, "y": 0}}, "opens_first": "ghost"}) == [
        "The stage places 'ghost', which is not in the cast.",
        "The balloon of 'ghost' opens first, and it is not in the cast.",
    ]


def test_visitors_need_every_runtime_member_at_an_address() -> None:
    assert problems(deployment={}) == [
        "Visitors may watch, and 'accounting' runs on a runtime with no address: deployment.addresses names none for it."
    ]
    assert problems(deployment={}, audience={"who": "signed-in"}) == []
    assert problems(deployment={"addresses": {"sales": "SALES_URL", "ghost": "GHOST_URL", "accounting": "A_URL"}}) == [
        "'sales' runs in the browser: it has no address.",
        "An address is read for 'ghost', which is not in the cast.",
    ]


def test_the_rehearsal_names_the_script_and_the_stage() -> None:
    assert problems(rehearsal={"beats": [{"beat": "curtain"}, {"beat": "open-invoices"}, {"beat": "open-invoices"}]}) == [
        "The rehearsal names the beat 'curtain', which is not in the script.",
        "The rehearsal names the beat 'open-invoices' twice.",
    ]
    assert problems(rehearsal={"beats": [{"beat": "open-invoices", "lines": ["Sales → Marketing", "Odoo: words"]}]}) == [
        "The rehearsal of 'open-invoices' names 'Marketing', which is not on stage.",
    ]
    assert problems(rehearsal={"beats": [{"beat": "open-invoices", "lines": ["Accounting → Odoo: odoo_accounting_nothing"]}]}) == [
        "The rehearsal of 'open-invoices' expects 'odoo_accounting_nothing', which odoo-accounting does not offer.",
    ]
    assert problems(rehearsal={"recording": {"path": "sales-and-accounting/recording.json"}}) == [
        "The recording 'sales-and-accounting/recording.json' is not beside the scenes."
    ]


def test_a_scene_of_the_catalogue_that_cannot_be_played_is_refused_when_loading() -> None:
    from agentspecs.scenes import load_scenes

    folder = SCENES_DIR
    assert set(load_scenes(folder)) == set(HOME_SCENES)
    with pytest.raises(SceneError, match="Visitors may watch"):
        load_scenes(_folder_with(problems_in={"deployment": {}}))


def _folder_with(problems_in: Dict[str, Any]) -> pathlib.Path:
    import tempfile

    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "sales-and-accounting.yaml").write_text(yaml.safe_dump({**raw("sales-and-accounting"), **problems_in}, allow_unicode=True))
    return folder


def test_the_rehearsal_that_was_played_is_kept_beside_the_specs(tmp_path: pathlib.Path) -> None:
    from agentspecs.scenes import ScenePlayed, played_path, scene_played, write_played

    # None was played: nothing, not a pass.
    assert scene_played("sales-and-accounting", tmp_path) is None
    assert played_path("sales-and-accounting:0.0.1", tmp_path) == tmp_path / "sales-and-accounting" / "rehearsal.json"
    played = ScenePlayed(
        at="2026-10-08T18:39:08+00:00",
        passed=False,
        says="Rehearsal: 0 of 4 beats passed. 4 not run. The scene is not Live.",
        beats=[{"beat": "open-invoices", "state": "not_run", "says": "Accounting is not set up."}],
        runtime="1.3.93",
    )
    path = write_played("sales-and-accounting", played, tmp_path)
    assert path == played_path("sales-and-accounting", tmp_path) and path.is_file()
    again = scene_played("sales-and-accounting", tmp_path)
    assert again == played and again.where == "on Datalayer" and again.beats[0].seconds == 0.0
    # The file is read back as it was written, in order, for a diff a person reads.
    assert json.loads(path.read_text())["beats"][0]["state"] == "not_run"
    # A beat's state is one of three; anything else is not a rehearsal's result.
    with pytest.raises(Exception, match="state"):
        ScenePlayed(at="now", passed=True, says="", beats=[{"beat": "b", "state": "done"}])
    path.write_text('{"passed": true}')
    with pytest.raises(SceneError, match="rehearsal.json of 'sales-and-accounting' is not a rehearsal's result"):
        scene_played("sales-and-accounting", tmp_path)
    path.write_text("not json")
    with pytest.raises(SceneError, match="is not a rehearsal's result"):
        scene_played("sales-and-accounting", tmp_path)
    # The catalogue's own scenes: a file beside the specs is read, none is a pass by default.
    for scene_id in SCENE_CATALOGUE:
        found = scene_played(scene_id)
        assert found is None or isinstance(found, ScenePlayed)


def test_a_scene_spec_is_a_pydantic_model_a_host_can_build() -> None:
    scene = SceneSpec(id="solo", name="Solo", emoji="\U0001f3ad", team="month-end-close:0.0.1")
    assert scene.team_of().id == "month-end-close" and scene.cues() == []
    assert dump_scene(scene) == {"schema": SCENE_SCHEMA, "id": "solo", "name": "Solo", "emoji": "\U0001f3ad", "team": "month-end-close:0.0.1"}
