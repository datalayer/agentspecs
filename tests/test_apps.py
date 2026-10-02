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
    MAX_SAFE_INTEGER,
    classes_of,
    is_comparable,
    is_pattern,
    is_read_only,
    matches,
    server_actions_problems,
    server_specs,
    server_tool_classes,
    server_tool_conditions,
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
    tool_escalations,
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
    # An event is created, and its guests are invited: both, at once.
    assert set(classes_of("google-workspace.manage_event", {"action": "create"})) == {
        ActionClass.WRITE,
        ActionClass.SEND,
    }
    assert set(classes_of("google-workspace.manage_drive_access")) == {
        ActionClass.PUBLISH,
        ActionClass.SEND,
        ActionClass.DELETE,
    }


def test_what_a_tool_does_can_depend_on_what_it_is_asked() -> None:
    label = "google-workspace.modify_gmail_message_labels"
    # Archiving is a write; the same tool trashes when the label is TRASH.
    assert classes_of(label, {"remove_label_ids": ["INBOX"]}) == (ActionClass.WRITE,)
    assert classes_of(label, {"add_label_ids": ["STARRED"]}) == (ActionClass.WRITE,)
    assert classes_of(label, {"add_label_ids": ["STARRED", "trash"]}) == (ActionClass.WRITE, ActionClass.DELETE)
    # Nobody said what it is asked: everything it can do.
    assert classes_of(label) == (ActionClass.WRITE, ActionClass.DELETE)
    assert classes_of(label, {}) == (ActionClass.WRITE,)
    manage = "google-workspace.manage_gmail_label"
    assert classes_of(manage, {"action": "create"}) == (ActionClass.WRITE,)
    assert classes_of(manage, {"action": "delete"}) == (ActionClass.WRITE, ActionClass.DELETE)
    drive = "google-workspace.update_drive_file"
    assert classes_of(drive, {"trashed": True}) == (ActionClass.WRITE, ActionClass.DELETE)
    assert classes_of(drive, {"trashed": False}) == (ActionClass.WRITE,)
    # True is not 1: an argument is compared as what it is.
    assert classes_of(drive, {"trashed": 1}) == (ActionClass.WRITE,)


def test_a_condition_is_read_or_refused() -> None:
    server = {
        "id": "s",
        "actions": {
            "tools": {
                "manage": {"class": "write", "when": [{"argument": "action", "equals": ["delete", "clear"], "class": "delete"}]}
            }
        },
    }
    assert server_tool_classes(server, "manage", {"action": "clear"}) == (ActionClass.WRITE, ActionClass.DELETE)
    assert server_tool_classes(server, "manage", {"other": "delete"}) == (ActionClass.WRITE,)
    assert [condition.as_data() for condition in server_tool_conditions(server, "manage")] == [
        {"argument": "action", "classes": ["delete"], "equals": ["delete", "clear"]}
    ]
    for wrong in (
        {"class": "write", "when": [{"argument": "action", "class": "delete"}]},
        {"class": "write", "when": [{"argument": "action", "equals": "x", "includes": ["x"], "class": "delete"}]},
        {"class": "write", "when": [{"equals": "x", "class": "delete"}]},
        {"class": "write", "unless": []},
        # An argument is compared with a word, a number, true or false: not with a list or a mapping.
        {"class": "write", "when": [{"argument": "mode", "equals": [{"kind": "delete"}], "class": "delete"}]},
        {"class": "write", "when": [{"argument": "ids", "includes": [["TRASH"]], "class": "delete"}]},
    ):
        assert server_actions_problems({"id": "s", "actions": {"tools": {"manage": wrong}}}) != []


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


def test_a_pattern_means_the_same_wherever_it_is_read() -> None:
    assert matches("search_gmail_messages", "*gmail*")
    assert not matches("search_drive_files", "*gmail*")
    assert matches("get_a", "get_?") and not matches("get_ab", "get_?")
    # Nothing but `*` and `?` is special: a dot, a bracket and a brace are themselves.
    assert matches("a.b", "a.b") and not matches("axb", "a.b")
    assert matches("a[1]", "a[1]") and not matches("a1", "a[1]")
    assert matches("a[!b]c", "a[!b]c") and not matches("axc", "a[!b]c")
    assert matches("[", "[") and matches("a{b}", "a{b}")
    # Case counts.
    assert not matches("Search", "search")
    assert is_pattern("generate_*") and is_pattern("get_?")
    assert not is_pattern("a[1]") and not is_pattern("plain_name")
    server = {"id": "s", "actions": {"tools": {"get[1]": "read", "make_*": "write"}}}
    assert server_tool_classes(server, "get[1]") == (ActionClass.READ,)
    assert server_tool_classes(server, "get1") == ()
    assert server_tool_classes(server, "make_it") == (ActionClass.WRITE,)


def test_a_number_is_compared_only_where_every_reader_holds_it_exactly() -> None:
    assert MAX_SAFE_INTEGER == 2**53 - 1
    assert all(is_comparable(value) for value in ("word", True, 0, -3, 2.5, 1e-9, MAX_SAFE_INTEGER, -MAX_SAFE_INTEGER))
    # 2**53 and 2**53 + 1 are one number to JavaScript and two to Python.
    for value in (MAX_SAFE_INTEGER + 1, MAX_SAFE_INTEGER + 2, -(MAX_SAFE_INTEGER + 1), 1e20, 1e300, float("inf"), float("nan")):
        assert not is_comparable(value), value
    assert not is_comparable(None) and not is_comparable(["x"])

    def server(value: object) -> dict:
        entry = {"class": "write", "when": [{"argument": "amount", "equals": value, "class": "buy"}]}
        return {"id": "s", "actions": {"tools": {"pay": entry}}}

    assert server_actions_problems(server(MAX_SAFE_INTEGER)) == []
    assert any("holds exactly" in problem for problem in server_actions_problems(server(MAX_SAFE_INTEGER + 2)))
    assert any("holds exactly" in problem for problem in server_actions_problems(server(float("inf"))))
    # An argument beyond the range equals nothing, as it would in JavaScript — and not its neighbour.
    exact = server(MAX_SAFE_INTEGER)
    assert server_tool_classes(exact, "pay", {"amount": MAX_SAFE_INTEGER}) == (ActionClass.WRITE, ActionClass.BUY)
    assert server_tool_classes(exact, "pay", {"amount": MAX_SAFE_INTEGER + 1}) == (ActionClass.WRITE,)
    assert server_tool_classes(server(3), "pay", {"amount": 3.0}) == (ActionClass.WRITE, ActionClass.BUY)


def test_a_word_that_is_not_a_class_is_refused() -> None:
    with pytest.raises(ActionError, match="not an action class"):
        classes_from("destroy")
    assert server_actions_problems({"id": "s"}) != []
    assert server_actions_problems({"id": "s", "actions": {"tools": {"x": "destroy"}}}) != []
    assert server_actions_problems({"id": "s", "actions": {"checked": "2026-10-02", "tools": {}}}) != []


def test_the_mail_tools_are_classed_as_a_person_would() -> None:
    read = classes_of("google-workspace.search_gmail_messages")
    label = classes_of("google-workspace.modify_gmail_message_labels", {"remove_label_ids": ["INBOX"]})
    draft = classes_of("google-workspace.draft_gmail_message")
    assert read == (ActionClass.READ,)
    assert label == draft == (ActionClass.WRITE,)
    # A filter can forward mail: it is not a plain write.
    assert ActionClass.SEND in classes_of("google-workspace.manage_gmail_filter")
    assert ActionClass.PUBLISH in classes_of("google-workspace.set_drive_file_permissions")


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


def test_an_application_is_written_the_same_way_every_time() -> None:
    order = list(AppSpec.model_fields)
    for identity, found in APP_CATALOGUE.items():
        written = dump_app(found)
        keys = list(written)
        assert keys[0] == "schema", identity
        declared = [AppSpec.model_fields[name].alias or name for name in order]
        assert keys == [key for key in declared if key in keys], identity
        assert dump_app(parse_app(written)) == written, identity
    # What the spec does not declare the keys of is written in one order too.
    forward = {
        "question": "Which?",
        "scenarios": [{"name": "S", "weights": {"Cost": 1, "Accuracy": 2}}],
    }
    backward = {
        "question": "Which?",
        "scenarios": [{"weights": {"Accuracy": 2, "Cost": 1}, "name": "S"}],
    }
    tree = [
        {"id": "root", "component": "Column", "children": ["go"]},
        {"id": "go", "component": "Button", "variant": "primary", "action": {"event": {"name": "run", "context": {"b": 1, "a": 2}}}},
    ]
    reversed_tree = [dict(reversed(list(component.items()))) for component in tree]
    reversed_tree[1]["action"] = {"event": {"context": {"a": 2, "b": 1}, "name": "run"}}
    one = dump_app(app(kind="decision", decision=forward, interface={"surface": {"components": tree}}))
    other = dump_app(app(kind="decision", decision=backward, interface={"surface": {"components": reversed_tree}}))
    assert json.dumps(one) == json.dumps(other)
    assert list(one["decision"]["scenarios"][0]["weights"]) == ["Accuracy", "Cost"]
    assert list(one["interface"]["surface"]["components"][1]) == ["id", "component", "action", "variant"]
    assert list(one["interface"]["surface"]["components"][1]["action"]["event"]) == ["context", "name"]
    # The layout of its kind says nothing its kind does not: it is not written.
    triage = dump_app(APP_CATALOGUE["inbox-triage"])
    assert "layout" not in triage["interface"]
    assert dump_app(app(interface={"layout": "chat"})).get("interface") is None
    assert dump_app(app(interface={"layout": "split"}))["interface"] == {"layout": "split"}


def test_an_application_survives_being_written_and_read_again() -> None:
    def said(found: AppSpec) -> dict:
        """What an application says, its layout as it is laid out rather than as it was written."""
        data = found.model_dump()
        data["interface"]["layout"] = found.layout
        return data

    for identity, found in APP_CATALOGUE.items():
        assert said(parse_app(dump_app(found))) == said(found), identity
        assert said(parse_app(yaml.safe_load(yaml.safe_dump(dump_app(found))))) == said(found), identity


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
        (
            {"rules": [{"action": "Send", "applies_to": ["google-workspace.send_gmail_message"], "behaviour": "ask_first"},
                       {"action": "Mail", "applies_to": ["google-workspace:0.0.1.send_gmail_message"], "behaviour": "do_it"}]},
            "both apply to 'google-workspace.send_gmail_message'",
        ),
        ({"rules": [{"action": "Send", "applies_to": "send", "behaviour": "maybe"}]}, "rules.0.behaviour"),
        ({"emoji": "mail"}, "is one emoji"),
        ({"emoji": ""}, "is one emoji"),
        ({"permissions": {"spaces": [{"space": "a"}, {"space": "a"}]}}, "same Space twice"),
        ({"permissions": {"network": True}}, "permissions.network is not a field"),
        ({"permissions": {"computer": {"shell": "yes please"}}}, "permissions.computer.shell"),
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


def test_a_gate_reads_a_guard_the_application_runs() -> None:
    alone = app_problems(app(checks={"gates": ["low-confidence-review:0.0.1"]}))
    assert any("reads the Guard 'confidence-guard:0.0.1'" in problem for problem in alone)
    together = app(checks={"gates": ["low-confidence-review"], "guards": ["confidence-guard"]})
    assert app_problems(together) == []


def test_a_decision_is_judged_by_a_model_that_answers_judgments() -> None:
    def deciding(model: str) -> AppSpec:
        return app(kind="decision", decision={"question": "Which?", "judgment_model": model})

    assert app_problems(deciding("cloudflare:gtw/typesafe/jev")) == []
    assert any("to judge with" in problem for problem in app_problems(deciding("typesafe/jev")))
    chat_model = "bedrock:us.anthropic.claude-sonnet-4-6"
    assert any("does not answer typed judgments" in problem for problem in app_problems(deciding(chat_model)))


def test_a_rule_names_a_tool_its_connection_reaches() -> None:
    scoped = app(
        connections=[{"server": "google-workspace", "access": "write", "only": ["*gmail*"]}],
        rules=[{"action": "Search the Drive", "applies_to": ["google-workspace.search_drive_files"], "behaviour": "do_it"}],
    )
    assert any("leaves out" in problem for problem in app_problems(scoped))


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


def test_an_application_has_a_face_and_reaches_nothing_it_was_not_granted() -> None:
    plain = app()
    # Until its builder picks one, the eyes.
    assert plain.emoji == "\U0001f440"
    assert plain.permissions.spaces == []
    computer = plain.permissions.computer
    assert (computer.browse, computer.files, computer.shell) == (False, False, False)
    granted = app(
        emoji="\U0001f4ec",
        permissions={"spaces": [{"space": "support", "access": "write"}], "computer": {"browse": True}},
    )
    assert granted.emoji == "\U0001f4ec"
    assert granted.permissions.spaces[0].access is Access.WRITE
    assert granted.permissions.computer.browse and not granted.permissions.computer.shell
    # Every application of the catalogue has a face of its own.
    faces = [found.emoji for found in APP_CATALOGUE.values()]
    assert len(set(faces)) == len(faces) and "\U0001f440" not in faces


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
    label = "google-workspace.modify_gmail_message_labels"
    assert behaviour_for(ruled, label, arguments={"remove_label_ids": ["INBOX"]}) is Behaviour.DO_IT
    assert behaviour_for(ruled, "google-workspace.draft_gmail_message") is Behaviour.ASK_FIRST


def test_a_rule_that_names_a_tool_does_not_cover_what_its_arguments_make_it_do_besides() -> None:
    label = "google-workspace.modify_gmail_message_labels"
    ruled = app(rules=[{"action": "Label and archive", "applies_to": [label], "behaviour": "do_it"}])
    # Labelling is done. Trashing is a deletion, and no rule lets it: it waits for a person.
    assert behaviour_for(ruled, label, arguments={"add_label_ids": ["STARRED"]}) is Behaviour.DO_IT
    assert behaviour_for(ruled, label, arguments={"add_label_ids": ["TRASH"]}) is Behaviour.ASK_FIRST
    # Nobody said what it is asked: the worst it can do.
    assert behaviour_for(ruled, label) is Behaviour.ASK_FIRST
    forbidden = app(
        rules=[
            {"action": "Label and archive", "applies_to": [label], "behaviour": "do_it"},
            {"action": "Delete", "applies_to": "delete", "behaviour": "leave_to_me"},
        ]
    )
    assert behaviour_for(forbidden, label, arguments={"add_label_ids": ["TRASH"]}) is Behaviour.LEAVE_TO_ME
    assert behaviour_for(forbidden, label, arguments={"remove_label_ids": ["INBOX"]}) is Behaviour.DO_IT


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
    # Creating a filter or a label is asked; deleting one is never done.
    assert decided["manage_gmail_filter"] is Behaviour.ASK_FIRST
    assert decided["manage_gmail_label"] is Behaviour.ASK_FIRST
    for tool, arguments in (
        ("manage_gmail_label", {"action": "delete"}),
        ("manage_gmail_filter", {"action": "delete"}),
        ("modify_gmail_message_labels", {"add_label_ids": ["TRASH"]}),
        ("batch_modify_gmail_message_labels", {"add_label_ids": ["SPAM"]}),
    ):
        assert behaviour_for(triage, f"google-workspace.{tool}", arguments=arguments) is Behaviour.LEAVE_TO_ME, tool
    # And it says so: where what a tool is asked changes what it does.
    escalations = tool_escalations(triage)
    assert escalations["google-workspace.modify_gmail_message_labels"] == [
        {"argument": "add_label_ids", "classes": ["delete"], "includes": ["TRASH", "SPAM"], "behaviour": "leave_to_me"}
    ]
    # Nothing outside the mailbox is reached, and nothing it reaches sends by itself.
    reached = {name for name, behaviour in decided.items() if behaviour is not Behaviour.LEAVE_TO_ME}
    assert reached and all("gmail" in name for name in reached)
    alone = {name for name, behaviour in decided.items() if behaviour is Behaviour.DO_IT}
    for name in alone:
        classes = set(classes_of(f"google-workspace.{name}", {}))
        assert classes <= {ActionClass.READ, ActionClass.WRITE}, name
    # No argument of any call makes it delete, publish or buy by itself.
    for ref in tool_behaviours(triage):
        for condition in server_tool_conditions(server_specs()["google-workspace"], ref.split(".")[1]):
            values = condition.includes or condition.equals
            arguments = {condition.argument: [values[0]] if condition.includes else values[0]}
            assert behaviour_for(triage, ref, arguments=arguments) is not Behaviour.DO_IT, ref


def test_a_server_classed_by_a_pattern_is_reported_by_that_pattern(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentspecs import apps as module

    servers = dict(module._catalogue("mcp-servers"))
    servers["drawer"] = {"id": "drawer", "actions": {"checked": "2026-10-02", "tools": {"generate_*": "read", "erase_*": "delete"}}}
    monkeypatch.setitem(module._CATALOGUES, "mcp-servers", servers)
    reader = app(connections=[{"server": "drawer", "access": "read"}])
    assert tool_behaviours(reader) == {
        "drawer.generate_*": Behaviour.DO_IT,
        "drawer.erase_*": Behaviour.LEAVE_TO_ME,
    }
    writer = app(connections=[{"server": "drawer", "access": "write"}])
    assert tool_behaviours(writer)["drawer.erase_*"] is Behaviour.ASK_FIRST


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
    # A validator outside Python refuses another version too.
    assert schema["properties"]["schema"]["const"] == APP_SCHEMA
    assert json.loads(SCHEMA_PATH.read_text())["$id"].endswith(f"{APP_SCHEMA}.json")


def test_every_application_file_is_named_for_its_id() -> None:
    for path in APPS_DIR.glob("*.yaml"):
        assert yaml.safe_load(path.read_text())["id"] == path.stem
