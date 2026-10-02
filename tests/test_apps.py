# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Applications and action classes: the catalogue loads, and what each promises is checked.

A rule is written in a person's words and enforced on what a tool does. Every
sentence of that — the classes, the four behaviours, what an unknown tool is
taken for, what an application reaches — is a check here.
"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml

from agentspecs.actions import (
    ACTING,
    ActionClass,
    ActionError,
    classes_from,
    classes_of,
    is_read_only,
    server_actions_problems,
    server_specs,
    server_tool_classes,
    split_ref,
    tool_classes,
    tool_specs,
)
from agentspecs.apps import (
    APP_CATALOGUE,
    APP_SCHEMA,
    DEFAULT_BEHAVIOURS,
    SCHEMA_PATH,
    Access,
    AppError,
    AppKind,
    AppSpec,
    Behaviour,
    Layout,
    app_problems,
    app_setup,
    behaviour_for,
    dump_app,
    get_app,
    json_schema,
    list_apps,
    load_apps,
    parse_app,
    schema_text,
    strictest,
    tool_behaviours,
)

APPS_DIR = pathlib.Path(__file__).parent.parent / "agentspecs" / "apps"


def app(**changes: object) -> AppSpec:
    """A small chat application, with what a test changes."""
    data: dict = {
        "id": "desk",
        "name": "Desk",
        "kind": "chat",
        "agent": "cog-crawler:0.0.1",
        "connections": [{"server": "google-workspace:0.0.1", "access": "write"}],
    }
    data.update(changes)
    return parse_app(data)


# --- action classes ----------------------------------------------------------------------


def test_every_tool_of_the_catalogue_has_a_class() -> None:
    unclassed = [identity for identity, tool in tool_specs().items() if not tool_classes(tool)]
    assert unclassed == []


def test_every_server_says_what_its_tools_do_or_that_nobody_looked() -> None:
    problems = [problem for server in server_specs().values() for problem in server_actions_problems(server)]
    assert problems == []
    for identity, server in server_specs().items():
        actions = server["actions"]
        # A server that was not checked classes nothing: it does not guess.
        assert bool(actions.get("checked")) == bool(actions.get("tools")), identity


def test_a_server_that_was_checked_classes_every_tool_it_names() -> None:
    for identity, server in server_specs().items():
        for name in server["actions"].get("tools") or {}:
            assert server_tool_classes(server, name), f"{identity}.{name}"


def test_a_tool_reference_is_a_server_and_a_tool_or_a_tool_alone() -> None:
    assert split_ref("tavily.tavily_search") == ("tavily", "tavily_search")
    assert split_ref("google-workspace:0.0.1.send_gmail_message") == ("google-workspace", "send_gmail_message")
    assert split_ref("runtime-send-mail") == (None, "runtime-send-mail")
    assert split_ref("runtime-send-mail:0.0.1") == (None, "runtime-send-mail")


def test_classes_are_read_by_reference() -> None:
    assert classes_of("tavily.tavily_search") == (ActionClass.READ,)
    assert classes_of("google-workspace.send_gmail_message") == (ActionClass.SEND,)
    assert classes_of("runtime-send-mail:0.0.1") == (ActionClass.SEND,)
    # A pattern answers for the tools it matches.
    assert classes_of("chart.generate_pie_chart") == (ActionClass.READ,)


def test_a_tool_that_does_several_things_carries_each() -> None:
    assert set(classes_of("google-workspace.manage_event")) == {
        ActionClass.WRITE,
        ActionClass.SEND,
        ActionClass.DELETE,
    }


def test_an_unknown_tool_has_no_class_and_is_never_a_reader() -> None:
    assert classes_of("github.create_issue") == ()
    assert classes_of("google-workspace.a_tool_added_tomorrow") == ()
    assert classes_of("no-such-server.anything") == ()
    assert not is_read_only(())
    assert is_read_only((ActionClass.READ,))
    assert not is_read_only((ActionClass.READ, ActionClass.WRITE))


def test_an_exact_name_wins_over_a_pattern_and_a_default_answers_the_rest() -> None:
    server = {"id": "s", "actions": {"default": "write", "tools": {"get_*": "read", "get_and_delete": "delete"}}}
    assert server_tool_classes(server, "get_thing") == (ActionClass.READ,)
    assert server_tool_classes(server, "get_and_delete") == (ActionClass.DELETE,)
    assert server_tool_classes(server, "other") == (ActionClass.WRITE,)


def test_a_word_that_is_not_a_class_is_refused() -> None:
    with pytest.raises(ActionError, match="not an action class"):
        classes_from("destroy")
    assert server_actions_problems({"id": "s"}) != []
    assert server_actions_problems({"id": "s", "actions": {"tools": {"x": "destroy"}}}) != []
    assert server_actions_problems({"id": "s", "actions": {"checked": "2026-10-02", "tools": {}}}) != []


def test_the_mail_tools_are_classed_as_a_person_would() -> None:
    read = classes_of("google-workspace.search_gmail_messages")
    label = classes_of("google-workspace.modify_gmail_message_labels")
    draft = classes_of("google-workspace.draft_gmail_message")
    assert read == (ActionClass.READ,)
    assert label == draft == (ActionClass.WRITE,)
    # A filter can forward mail: it is not a plain write.
    assert ActionClass.SEND in classes_of("google-workspace.manage_gmail_filter")
    assert classes_of("google-workspace.set_drive_file_permissions") == (ActionClass.PUBLISH,)


# --- the catalogue ----------------------------------------------------------------------


def test_the_catalogue_has_one_application_of_each_kind() -> None:
    assert {found.kind for found in APP_CATALOGUE.values()} == set(AppKind)
    assert get_app("web-research") is APP_CATALOGUE["web-research"]
    assert get_app("web-research:0.0.1") is APP_CATALOGUE["web-research"]
    assert get_app("nope") is None
    assert [found.id for found in list_apps(AppKind.WORKER)] == ["inbox-triage"]


def test_every_application_resolves_its_references() -> None:
    for identity, found in APP_CATALOGUE.items():
        assert app_problems(found) == [], identity
        assert found.schema_ == APP_SCHEMA


def test_what_is_not_enabled_is_said_as_setup_and_not_as_a_mistake() -> None:
    # The chat that only searches the web runs on what is enabled today.
    assert app_setup(APP_CATALOGUE["web-research"]) == []
    # The worker names an agent and a server that are not: that is setup, said in words,
    # and not a problem of the spec.
    triage = APP_CATALOGUE["inbox-triage"]
    assert app_problems(triage) == []
    assert app_setup(triage) == [
        "The agent 'worker-mail-triage:0.0.1' is not enabled.",
        "The MCP server 'google-workspace:0.0.1' is not enabled.",
    ]


def test_each_kind_has_its_layout_unless_it_says_another() -> None:
    assert APP_CATALOGUE["web-research"].layout is Layout.CHAT
    assert APP_CATALOGUE["inbox-triage"].layout is Layout.SPLIT
    assert app().layout is Layout.CHAT
    assert app(interface={"layout": "split"}).layout is Layout.SPLIT


def test_an_application_survives_being_written_and_read_again() -> None:
    for identity, found in APP_CATALOGUE.items():
        assert parse_app(dump_app(found)) == found, identity
        assert parse_app(yaml.safe_load(yaml.safe_dump(dump_app(found)))) == found, identity


def test_a_decision_application_carries_the_whole_decision() -> None:
    decision = APP_CATALOGUE["ship-or-fix"].decision
    assert decision is not None
    assert [criterion.name for criterion in decision.criteria][:2] == ["Pass rate", "Cost per task"]
    assert decision.criteria[3].options[0].startswith("Blocking:")
    assert decision.scenarios[0].weights["Pass rate"] == 4
    assert decision.min_confidence == 0.6


# --- what the spec refuses ------------------------------------------------------------


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({"agent": ""}, "names who does the work"),
        ({"team": "jupyter"}, "not both"),
        ({"colour": "red"}, "colour is not a field of the spec"),
        ({"schema": "loop.app/v9"}, "written in 'loop.app/v9'"),
        ({"id": "Desk Top"}, "cannot use 'Desk Top' as an id"),
        ({"kind": "worker"}, "a worker says its `goal`"),
        ({"kind": "worker", "goal": "Sort the mail"}, "what starts its work"),
        ({"triggers": [{"type": "schedule", "cron": "0 8 * * *"}]}, "`triggers` are a worker's"),
        ({"kind": "decision"}, "says what it decides"),
        ({"decision": {"question": "Which?"}}, "decides nothing"),
        ({"connections": [{"server": "tavily"}, {"server": "tavily:0.0.1"}]}, "same server twice"),
        ({"connections": [{"server": "tavily", "as": "me"}]}, "connections.0.as"),
        ({"record": {"keep_for": "forever"}}, "cannot read the retention"),
        ({"tests": {"ready_at": 1.5}}, "tests.ready_at"),
        ({"deployment": {"embedded": {"origins": ["example.com/page"]}}}, "is not an origin"),
        ({"deployment": {"hosted": {"slug": "My App"}}}, "in an address"),
        ({"interface": {"accent": "red"}}, "interface.accent"),
        ({"interface": {"surface": {"components": [{"id": "a", "component": "Text"}]}}}, "starts from the component"),
        (
            {"rules": [{"action": "Send", "applies_to": "send", "behaviour": "ask_first"},
                       {"action": "send", "applies_to": "delete", "behaviour": "ask_first"}]},
            "same action",
        ),
        (
            {"rules": [{"action": "Send", "applies_to": "send", "behaviour": "ask_first"},
                       {"action": "Mail", "applies_to": ["send"], "behaviour": "do_it"}]},
            "both apply to 'send'",
        ),
        ({"rules": [{"action": "Send", "applies_to": [], "behaviour": "do_it"}]}, "applies to a class"),
        ({"rules": [{"action": "Send", "applies_to": "send", "behaviour": "maybe"}]}, "rules.0.behaviour"),
    ],
)
def test_what_is_wrong_is_refused_in_a_sentence(changes: dict, says: str) -> None:
    with pytest.raises(AppError, match=says):
        app(**changes)


def test_a_worker_trigger_says_when() -> None:
    worker = {"kind": "worker", "goal": "Sort the mail"}
    with pytest.raises(AppError, match="says its `cron`"):
        app(**worker, triggers=[{"type": "schedule"}])
    with pytest.raises(AppError, match="five fields"):
        app(**worker, triggers=[{"type": "schedule", "cron": "every day"}])
    with pytest.raises(AppError, match="says its `event`"):
        app(**worker, triggers=[{"type": "event"}])
    assert app(**worker, triggers=[{"type": "once", "at": "2026-11-01T08:00:00Z"}]).triggers[0].at


def test_a_reference_that_does_not_resolve_is_a_problem_said_in_words() -> None:
    assert app_problems(app(agent="no-such-agent")) == ["There is no agent or Cog named 'no-such-agent'."]
    assert "There is no Frame named 'nope'." in app_problems(app(context=["nope"]))
    assert "There is no model named 'nope'." in app_problems(app(model="nope"))
    assert "There is no Guard named 'nope'." in app_problems(app(checks={"guards": ["nope"]}))
    problems = app_problems(
        app(rules=[{"action": "Search", "applies_to": ["tavily.tavily_search"], "behaviour": "do_it"}])
    )
    assert any("not connected to 'tavily'" in problem for problem in problems)


def test_writing_through_a_server_nobody_classed_is_a_problem() -> None:
    problems = app_problems(app(connections=[{"server": "github", "access": "write"}]))
    assert any("nobody has classed" in problem for problem in problems)
    assert app_problems(app(connections=[{"server": "github", "access": "read"}])) == []


def test_a_directory_whose_application_does_not_resolve_is_refused(tmp_path: pathlib.Path) -> None:
    (tmp_path / "broken.yaml").write_text(
        yaml.safe_dump({"id": "broken", "name": "Broken", "kind": "chat", "agent": "no-such-agent"})
    )
    with pytest.raises(AppError, match="There is no agent or Cog named"):
        load_apps(tmp_path)
    (tmp_path / "broken.yaml").write_text(yaml.safe_dump({"id": "other", "name": "X", "kind": "chat"}))
    with pytest.raises(AppError, match="named for id 'broken'"):
        load_apps(tmp_path)


# --- what a rule decides ----------------------------------------------------------------


def test_reading_needs_no_rule_and_anything_that_acts_waits_for_a_person() -> None:
    assert DEFAULT_BEHAVIOURS[ActionClass.READ] is Behaviour.DO_IT
    for acting in ACTING:
        assert DEFAULT_BEHAVIOURS[acting] is Behaviour.ASK_FIRST
    plain = app()
    assert behaviour_for(plain, "google-workspace.search_gmail_messages") is Behaviour.DO_IT
    assert behaviour_for(plain, "google-workspace.draft_gmail_message") is Behaviour.ASK_FIRST
    assert behaviour_for(plain, "google-workspace.send_gmail_message") is Behaviour.ASK_FIRST


@pytest.mark.parametrize("action", list(ActionClass))
@pytest.mark.parametrize("behaviour", list(Behaviour))
def test_a_rule_on_a_class_decides_every_tool_of_that_class(action: ActionClass, behaviour: Behaviour) -> None:
    ruled = app(rules=[{"action": "The rule", "applies_to": action.value, "behaviour": behaviour.value}])
    assert behaviour_for(ruled, "google-workspace.some_tool", classes=[action]) is behaviour


def test_a_tool_of_several_classes_takes_the_most_restricted() -> None:
    assert strictest([Behaviour.DO_IT, Behaviour.ASK_FIRST, Behaviour.IF_ASKED]) is Behaviour.ASK_FIRST
    ruled = app(
        rules=[
            {"action": "Write", "applies_to": "write", "behaviour": "do_it"},
            {"action": "Delete", "applies_to": "delete", "behaviour": "leave_to_me"},
        ]
    )
    # manage_event writes, sends and deletes: the delete rule wins over the write rule.
    assert behaviour_for(ruled, "google-workspace.manage_event") is Behaviour.LEAVE_TO_ME
    assert behaviour_for(ruled, "google-workspace.draft_gmail_message") is Behaviour.DO_IT


def test_a_rule_that_names_a_tool_wins_over_the_rule_on_its_class() -> None:
    ruled = app(
        rules=[
            {"action": "Write", "applies_to": "write", "behaviour": "ask_first"},
            {"action": "Label", "applies_to": ["google-workspace:0.0.1.modify_gmail_message_labels"], "behaviour": "do_it"},
        ]
    )
    assert behaviour_for(ruled, "google-workspace.modify_gmail_message_labels") is Behaviour.DO_IT
    assert behaviour_for(ruled, "google-workspace.draft_gmail_message") is Behaviour.ASK_FIRST


def test_a_tool_nobody_classed_is_left_to_the_person_unless_a_rule_names_it() -> None:
    assert behaviour_for(app(), "google-workspace.a_tool_added_tomorrow") is Behaviour.LEAVE_TO_ME
    named = app(rules=[{"action": "New", "applies_to": ["google-workspace.a_tool_added_tomorrow"], "behaviour": "ask_first"}])
    assert behaviour_for(named, "google-workspace.a_tool_added_tomorrow") is Behaviour.ASK_FIRST


def test_an_application_reaches_nothing_it_does_not_name() -> None:
    # Not connected: even a search is left to the person.
    assert behaviour_for(app(), "tavily.tavily_search") is Behaviour.LEAVE_TO_ME
    # Connected, but the connection leaves the tool out.
    scoped = app(connections=[{"server": "google-workspace", "access": "write", "only": ["*gmail*"]}])
    assert behaviour_for(scoped, "google-workspace.search_gmail_messages") is Behaviour.DO_IT
    assert behaviour_for(scoped, "google-workspace.search_drive_files") is Behaviour.LEAVE_TO_ME


def test_a_connection_that_only_reads_carries_no_tool_that_acts() -> None:
    reader = app(
        connections=[{"server": "google-workspace", "access": "read"}],
        rules=[{"action": "Send", "applies_to": "send", "behaviour": "do_it"}],
    )
    assert reader.connections[0].access is Access.READ
    assert behaviour_for(reader, "google-workspace.search_gmail_messages") is Behaviour.DO_IT
    # The rule says do it; the connection says it cannot.
    assert behaviour_for(reader, "google-workspace.send_gmail_message") is Behaviour.LEAVE_TO_ME


def test_inbox_triage_reads_and_drafts_alone_sends_on_approval_and_deletes_nothing() -> None:
    triage = APP_CATALOGUE["inbox-triage"]
    decided = {ref.split(".")[1]: behaviour for ref, behaviour in tool_behaviours(triage).items()}
    assert decided["search_gmail_messages"] is Behaviour.DO_IT
    assert decided["modify_gmail_message_labels"] is Behaviour.DO_IT
    assert decided["draft_gmail_message"] is Behaviour.DO_IT
    assert decided["send_gmail_message"] is Behaviour.ASK_FIRST
    assert decided["manage_gmail_filter"] is Behaviour.LEAVE_TO_ME
    assert decided["manage_gmail_label"] is Behaviour.LEAVE_TO_ME
    # Nothing outside the mailbox is reached, and nothing it reaches sends by itself.
    reached = {name for name, behaviour in decided.items() if behaviour is not Behaviour.LEAVE_TO_ME}
    assert reached and all("gmail" in name for name in reached)
    alone = {name for name, behaviour in decided.items() if behaviour is Behaviour.DO_IT}
    for name in alone:
        classes = set(classes_of(f"google-workspace.{name}"))
        assert classes <= {ActionClass.READ, ActionClass.WRITE}, name


def test_web_research_only_reads() -> None:
    research = APP_CATALOGUE["web-research"]
    assert research.rules == []
    assert set(tool_behaviours(research).values()) == {Behaviour.DO_IT}
    assert all(is_read_only(classes_of(ref)) for ref in tool_behaviours(research))


# --- the schema -------------------------------------------------------------------------


def test_the_published_schema_is_the_one_the_code_writes() -> None:
    assert SCHEMA_PATH.read_text() == schema_text(), "run `python -m agentspecs.apps` to write it again"


def test_the_schema_names_the_fields_as_the_yaml_does() -> None:
    schema = json_schema()
    assert schema["title"] == "Appspec"
    assert {"schema", "id", "kind", "agent", "connections", "rules", "interface", "tests", "record"} <= set(
        schema["properties"]
    )
    assert "as" in schema["$defs"]["AppConnection"]["properties"]
    assert schema["additionalProperties"] is False
    assert json.loads(SCHEMA_PATH.read_text())["$id"].endswith(f"{APP_SCHEMA}.json")


def test_every_application_file_is_named_for_its_id() -> None:
    for path in APPS_DIR.glob("*.yaml"):
        assert yaml.safe_load(path.read_text())["id"] == path.stem
