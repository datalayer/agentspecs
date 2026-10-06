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
import re
from pathlib import Path

import pytest
import yaml

import agentspecs.apps
from agentspecs.actions import (
    ACTING,
    MAX_SAFE_INTEGER,
    ActionClass,
    ActionError,
    classes_from,
    forwards_outside,
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
    ASSISTANT_CHARACTER_ID,
    DEFAULT_BEHAVIOURS,
    SCHEMA_PATH,
    Access,
    ActsAs,
    AppError,
    AppKind,
    AppSpec,
    BalloonDisplay,
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
    problems = [
        problem for server in server_specs().values() for problem in server_actions_problems(server)
    ]
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
    assert split_ref("google-workspace:0.0.1.send_gmail_message") == (
        "google-workspace",
        "send_gmail_message",
    )
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
    assert classes_of(label, {"add_label_ids": ["STARRED", "trash"]}) == (
        ActionClass.WRITE,
        ActionClass.DELETE,
    )
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
                "manage": {
                    "class": "write",
                    "when": [
                        {"argument": "action", "equals": ["delete", "clear"], "class": "delete"}
                    ],
                }
            }
        },
    }
    assert server_tool_classes(server, "manage", {"action": "clear"}) == (
        ActionClass.WRITE,
        ActionClass.DELETE,
    )
    assert server_tool_classes(server, "manage", {"other": "delete"}) == (ActionClass.WRITE,)
    assert [condition.as_data() for condition in server_tool_conditions(server, "manage")] == [
        {"argument": "action", "classes": ["delete"], "equals": ["delete", "clear"]}
    ]
    for wrong in (
        {"class": "write", "when": [{"argument": "action", "class": "delete"}]},
        {
            "class": "write",
            "when": [{"argument": "action", "equals": "x", "includes": ["x"], "class": "delete"}],
        },
        {"class": "write", "when": [{"equals": "x", "class": "delete"}]},
        {"class": "write", "unless": []},
        # An argument is compared with a word, a number, true or false: not with a list or a mapping.
        {
            "class": "write",
            "when": [{"argument": "mode", "equals": [{"kind": "delete"}], "class": "delete"}],
        },
        {
            "class": "write",
            "when": [{"argument": "ids", "includes": [["TRASH"]], "class": "delete"}],
        },
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
    server = {
        "id": "s",
        "actions": {"default": "write", "tools": {"get_*": "read", "get_and_delete": "delete"}},
    }
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
    assert all(
        is_comparable(value)
        for value in ("word", True, 0, -3, 2.5, 1e-9, MAX_SAFE_INTEGER, -MAX_SAFE_INTEGER)
    )
    # 2**53 and 2**53 + 1 are one number to JavaScript and two to Python.
    for value in (
        MAX_SAFE_INTEGER + 1,
        MAX_SAFE_INTEGER + 2,
        -(MAX_SAFE_INTEGER + 1),
        1e20,
        1e300,
        float("inf"),
        float("nan"),
    ):
        assert not is_comparable(value), value
    assert not is_comparable(None) and not is_comparable(["x"])

    def server(value: object) -> dict:
        entry = {
            "class": "write",
            "when": [{"argument": "amount", "equals": value, "class": "buy"}],
        }
        return {"id": "s", "actions": {"tools": {"pay": entry}}}

    assert server_actions_problems(server(MAX_SAFE_INTEGER)) == []
    assert any(
        "holds exactly" in problem
        for problem in server_actions_problems(server(MAX_SAFE_INTEGER + 2))
    )
    assert any(
        "holds exactly" in problem for problem in server_actions_problems(server(float("inf")))
    )
    # An argument beyond the range equals nothing, as it would in JavaScript — and not its neighbour.
    exact = server(MAX_SAFE_INTEGER)
    assert server_tool_classes(exact, "pay", {"amount": MAX_SAFE_INTEGER}) == (
        ActionClass.WRITE,
        ActionClass.BUY,
    )
    assert server_tool_classes(exact, "pay", {"amount": MAX_SAFE_INTEGER + 1}) == (
        ActionClass.WRITE,
    )
    assert server_tool_classes(server(3), "pay", {"amount": 3.0}) == (
        ActionClass.WRITE,
        ActionClass.BUY,
    )


def test_a_word_that_is_not_a_class_is_refused() -> None:
    with pytest.raises(ActionError, match="not an action class"):
        classes_from("destroy")
    assert server_actions_problems({"id": "s"}) != []
    assert server_actions_problems({"id": "s", "actions": {"tools": {"x": "destroy"}}}) != []
    assert (
        server_actions_problems({"id": "s", "actions": {"checked": "2026-10-02", "tools": {}}})
        != []
    )


def test_the_mail_tools_are_classed_as_a_person_would() -> None:
    read = classes_of("google-workspace.search_gmail_messages")
    label = classes_of(
        "google-workspace.modify_gmail_message_labels", {"remove_label_ids": ["INBOX"]}
    )
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
    assert [found.id for found in list_apps(AppKind.WORKER)] == ["inbox-triage", "pipeline-report"]


def test_every_application_resolves_its_references() -> None:
    for identity, found in APP_CATALOGUE.items():
        assert app_problems(found) == [], identity
        assert found.schema_ == APP_SCHEMA


def test_every_example_says_what_was_verified_and_how() -> None:
    # LOOP E-14: what was tried live, what runs on recorded data, what is not
    # verified yet — each example says at least one, in sentences.
    for identity, found in APP_CATALOGUE.items():
        verified = found.tests.verified
        said = verified.live + verified.recorded + verified.unverified
        assert said, identity
        assert all(sentence.strip().endswith((".", ")")) for sentence in said), identity
    # An application that says nothing of it says nothing: lists, empty.
    blank = parse_app({"id": "x", "name": "X", "kind": "chat", "agent": "example-simple"})
    assert blank.tests.verified.live == blank.tests.verified.unverified == []


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
        {
            "id": "go",
            "component": "Button",
            "variant": "primary",
            "action": {"event": {"name": "run", "context": {"b": 1, "a": 2}}},
        },
    ]
    reversed_tree = [dict(reversed(list(component.items()))) for component in tree]
    reversed_tree[1]["action"] = {"event": {"context": {"a": 2, "b": 1}, "name": "run"}}
    one = dump_app(
        app(kind="decision", decision=forward, interface={"surface": {"components": tree}})
    )
    other = dump_app(
        app(
            kind="decision", decision=backward, interface={"surface": {"components": reversed_tree}}
        )
    )
    assert json.dumps(one) == json.dumps(other)
    assert list(one["decision"]["scenarios"][0]["weights"]) == ["Accuracy", "Cost"]
    assert list(one["interface"]["surface"]["components"][1]) == [
        "id",
        "component",
        "action",
        "variant",
    ]
    assert list(one["interface"]["surface"]["components"][1]["action"]["event"]) == [
        "context",
        "name",
    ]
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
        assert said(parse_app(yaml.safe_load(yaml.safe_dump(dump_app(found))))) == said(found), (
            identity
        )


def test_a_decision_application_carries_the_whole_decision() -> None:
    decision = APP_CATALOGUE["ship-or-fix"].decision
    assert decision is not None
    assert [criterion.name for criterion in decision.criteria][:2] == ["Pass rate", "Cost per task"]
    assert decision.criteria[3].options[0].startswith("Blocking:")
    assert decision.scenarios[0].weights["Pass rate"] == 4
    assert decision.min_confidence == 0.6


def test_the_four_decision_templates_are_in_the_catalogue() -> None:
    """LOOP E-01: the landing's four templates, each an Appspec of its own — the
    Jupyter data analyst, the decision's ten components, typed decisions."""
    ship = APP_CATALOGUE["ship-or-fix"]
    templates = ["ship-or-fix", "supplier-comparison", "data-quality", "model-choice"]
    for identity in templates:
        found = APP_CATALOGUE[identity]
        assert found.kind is AppKind.DECISION, identity
        assert found.agent == "jupyter-data-analyst:0.0.1", identity
        assert found.interface.components == ship.interface.components, identity
        assert (
            found.decision is not None
            and found.decision.decision_model == "cloudflare:gtw/typesafe/jev"
        )
        assert " For " in found.description, identity
        assert found.contents, identity
    supplier = APP_CATALOGUE["supplier-comparison"].decision
    assert supplier is not None
    assert [(c.name, c.kind.value, c.weight) for c in supplier.criteria] == [
        ("Price", "metric", 2),
        ("Delivery reliability", "metric", 2),
        ("Capacity", "metric", 1),
        ("Fit with requirements", "score", 2),
        ("Missing information", "choice", 0),
    ]
    assert supplier.criteria[0].direction == "lower"
    assert (supplier.min_confidence, supplier.scenarios) == (0, [])
    quality = APP_CATALOGUE["data-quality"].decision
    assert quality is not None
    assert [(c.name, c.kind.value, c.weight) for c in quality.criteria] == [
        ("Rows affected", "metric", 2),
        ("Effect on the result", "metric", 3),
        ("Kind of anomaly", "choice", 0),
        ("Safe to correct automatically", "noul", 1),
    ]
    assert [option.split(":")[0] for option in quality.criteria[2].options] == [
        "Genuine",
        "Outlier",
        "Unit",
        "Missing",
        "Duplicate",
    ]
    model = APP_CATALOGUE["model-choice"].decision
    assert model is not None
    assert [(c.name, c.weight, c.measure) for c in model.criteria if c.kind.value == "metric"] == [
        ("Pass rate", 3, "pass_rate"),
        ("Cost per task", 2, "cost_per_task"),
        ("Latency", 2, "seconds_per_task"),
    ]
    assert model.min_confidence == 0.6
    assert [scenario.name for scenario in model.scenarios] == [
        "Quality first",
        "Cheapest that works",
        "Fastest that works",
    ]
    assert model.scenarios[1].weights["Cost per task"] == 4


#: LOOP §9: the eleven examples, Decide, and the team of Sales and Accounting, each with its kind.
EXAMPLES = {
    "ship-or-fix": AppKind.DECISION,
    "supplier-comparison": AppKind.DECISION,
    "data-quality": AppKind.DECISION,
    "model-choice": AppKind.DECISION,
    "support-desk": AppKind.CHAT,
    "web-research": AppKind.CHAT,
    "decide": AppKind.CHAT,
    "sales": AppKind.CHAT,
    "accounting": AppKind.CHAT,
    "customer-interview": AppKind.CHAT,
    "quote-calculator": AppKind.WIDGET,
    "report-from-a-file": AppKind.WIDGET,
    "pipeline-report": AppKind.WORKER,
    "inbox-triage": AppKind.WORKER,
}


def test_the_examples_are_in_the_catalogue() -> None:
    """LOOP E-01: every example of §9, and Decide, of its kind, with its face its own."""
    assert {identity: found.kind for identity, found in APP_CATALOGUE.items()} == EXAMPLES
    faces = [found.emoji for found in APP_CATALOGUE.values()]
    assert len(set(faces)) == len(faces)
    for identity in ["support-desk", "customer-interview", "report-from-a-file", "pipeline-report"]:
        found = APP_CATALOGUE[identity]
        assert 3 <= len(found.tests.cases) <= 5, identity
        assert found.interface.assistant is not None, identity


def test_decide_answers_by_asking_typed_decisions_and_deciding_is_a_read() -> None:
    """Decide: its agent asks Jev typed decisions with ``decide``, done without asking."""
    found = APP_CATALOGUE["decide"]
    assert "decide:0.0.1" in found.backend_tools
    assert behaviour_for(found, "decide") is Behaviour.DO_IT
    assert classes_of("decide") == (ActionClass.READ,)
    assert "typed decision" in (found.instructions or "")
    assert len(found.interface.starters) == 3
    assert app_problems(found) == []


def test_sales_reports_what_accounting_answers_and_reaches_nothing() -> None:
    """Sales: a chat in the browser that asks Accounting, over A2A, and connects to nothing."""
    found = APP_CATALOGUE["sales"]
    assert found.connections == [] and found.rules == [] and found.backend_tools == []
    assert "ask_accounting" in found.instructions
    assert "Never invent" in found.instructions
    assert found.interface.assistant == "paperclip"
    assert len(found.interface.starters) == 3
    assert 3 <= len(found.tests.cases) <= 5
    assert app_problems(found) == []


def test_accounting_only_reads_the_books_and_asks_before_anything_that_would_change_them() -> None:
    """Accounting: Odoo's accounting toolset at *Can read*; writing waits for a person."""
    found = APP_CATALOGUE["accounting"]
    assert [(c.server, c.access, c.acts_as) for c in found.connections] == [
        ("odoo-accounting:0.0.1", Access.READ, ActsAs.OWNER)
    ]
    assert {rule.action: rule.behaviour for rule in found.rules} == {
        "Read the books": Behaviour.DO_IT,
        "Change the books": Behaviour.ASK_FIRST,
    }
    assert "Never write to Odoo" in found.instructions
    # Every tool that reads is done alone; none that writes is reached at all.
    behaviours = tool_behaviours(found)
    assert behaviours
    for ref, behaviour in behaviours.items():
        if is_read_only(classes_of(ref)):
            assert behaviour is Behaviour.DO_IT, ref
        else:
            assert behaviour is Behaviour.LEAVE_TO_ME, ref
    assert (
        behaviour_for(found, "odoo-accounting.odoo_accounting_post_invoice")
        is Behaviour.LEAVE_TO_ME
    )
    assert behaviour_for(found, "odoo-accounting.odoo_accounting_trial_balance") is Behaviour.DO_IT
    # Its face is another Office Assistant than the one at the sales desk.
    assert found.interface.assistant == "wizard"
    assert found.interface.assistant != APP_CATALOGUE["sales"].interface.assistant
    assert app_problems(found) == []
    assert app_setup(found) == [
        "The agent 'worker-accountant:0.0.1' is not enabled.",
        "The MCP server 'odoo-accounting:0.0.1' is not enabled.",
    ]


def test_the_python_examples_sit_beside_their_spec() -> None:
    """LOOP E-02: an example built in Python keeps its `app.py` in a folder named
    for it, and its spec is the one `loop apps build` wrote from it."""
    built = sorted(path.parent.name for path in APPS_DIR.glob("*/app.py"))
    assert built == ["customer-interview", "report-from-a-file"]
    for identity in built:
        text = (APPS_DIR / f"{identity}.yaml").read_text()
        assert text.startswith("# Built from app.py by `loop apps build`"), identity
        assert "# loop:code " in text, identity


def test_the_canvas_example_says_its_page_was_composed_on_the_canvas() -> None:
    """LOOP E-05: how an example was built is in the catalogue. An example built in
    Python has its `app.py`; one whose page was composed on the Canvas says
    `composed_by: canvas`; *Support desk* is the Canvas example."""
    on_canvas = sorted(
        identity
        for identity, found in APP_CATALOGUE.items()
        if found.interface.surface is not None and found.interface.surface.composed_by == "canvas"
    )
    assert on_canvas == ["support-desk"]
    in_python = {path.parent.name for path in APPS_DIR.glob("*/app.py")}
    assert not in_python & set(on_canvas)


def test_the_weekly_pipeline_report_runs_the_op_s_checks_and_asks_before_sending() -> None:
    """The rigorous worker: the Guards, Gates and Track of the Sales Pipeline Board
    Report Op, a weekly schedule, and nothing sent without a person."""
    report = APP_CATALOGUE["pipeline-report"]
    op = yaml.safe_load(
        (APPS_DIR.parent / "ops" / "op-sales-pipeline-board-report.yaml").read_text()
    )
    guards = {guard for stage in op["guards"].values() for guard in stage}
    assert set(report.checks.guards) == guards
    assert report.checks.gates == op["gates"]
    assert report.checks.track == op["track"]
    assert report.agent == op["cogs"][0]
    assert [trigger.cron for trigger in report.triggers] == ["0 7 * * 1"]
    assert behaviour_for(report, "runtime-send-mail") is Behaviour.ASK_FIRST


def test_an_application_embeds_in_four_modes() -> None:
    """LOOP D-07: inline, bubble, panel, and the assistant — a character that speaks in a balloon."""
    from agentspecs.apps import EmbedMode

    assert [mode.value for mode in EmbedMode] == ["inline", "bubble", "panel", "assistant"]
    embedded = app(
        deployment={"embedded": {"mode": "assistant", "origins": ["https://example.com"]}}
    )
    assert embedded.deployment.embedded is not None
    assert embedded.deployment.embedded.mode is EmbedMode.ASSISTANT
    assert json_schema()["$defs"]["EmbedMode"]["enum"] == ["inline", "bubble", "panel", "assistant"]
    with pytest.raises(AppError, match="deployment.embedded.mode"):
        app(deployment={"embedded": {"mode": "popup"}})


def test_an_application_names_the_character_of_its_assistant() -> None:
    """LOOP T-24: any character an enabled plugin contributes, by id, or none.

    Which ids exist is known where the plugins are, the runtime and the page:
    the spec takes any id of the right shape, a plugin's own as Datalayer's."""
    plain = app()
    assert plain.interface.assistant is None
    assert "interface" not in dump_app(plain)
    for character in ("wizard", "owl", "acme-owl-2"):
        named = app(interface={"assistant": character})
        assert named.interface.assistant == character
        assert dump_app(named)["interface"] == {"assistant": character}
        assert parse_app(dump_app(named)) == named
    assert "AssistantCharacter" not in json_schema()["$defs"]
    assistant = json_schema()["$defs"]["AppInterface"]["properties"]["assistant"]["anyOf"][0]
    assert assistant["pattern"] == f"^{ASSISTANT_CHARACTER_ID}$"
    assert assistant["maxLength"] == 64
    for wrong in ("Clippy", "acme owl", "-owl", "owl-", "acme--owl", "acme.owl", "o" * 65, ""):
        with pytest.raises(AppError, match="interface.assistant"):
            app(interface={"assistant": wrong})


def test_an_application_says_how_its_balloon_shows_the_conversation() -> None:
    """LOOP T-23: the whole history, or only what it says or does now; the page's own when unsaid."""
    plain = app()
    assert plain.interface.balloon is None
    assert "interface" not in dump_app(plain)
    assert [display.value for display in BalloonDisplay] == ["history", "current"]
    for display in ("history", "current"):
        said = app(interface={"balloon": display})
        assert said.interface.balloon == BalloonDisplay(display)
        assert dump_app(said)["interface"] == {"balloon": display}
        assert parse_app(dump_app(said)) == said
    schema = json_schema()
    assert schema["$defs"]["BalloonDisplay"]["enum"] == ["history", "current"]
    balloon = schema["$defs"]["AppInterface"]["properties"]["balloon"]
    assert balloon["anyOf"][0] == {"$ref": "#/$defs/BalloonDisplay"}
    for wrong in ("latest", "History", "", "both"):
        with pytest.raises(AppError, match="interface.balloon"):
            app(interface={"balloon": wrong})


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
        (
            {"interface": {"surface": {"components": [{"id": "a", "component": "Text"}]}}},
            "starts from the component",
        ),
        (
            {
                "rules": [
                    {"action": "Send", "applies_to": "send", "behaviour": "ask_first"},
                    {"action": "send", "applies_to": "delete", "behaviour": "ask_first"},
                ]
            },
            "same action",
        ),
        (
            {
                "rules": [
                    {"action": "Send", "applies_to": "send", "behaviour": "ask_first"},
                    {"action": "Mail", "applies_to": ["send"], "behaviour": "do_it"},
                ]
            },
            "both apply to 'send'",
        ),
        (
            {"rules": [{"action": "Send", "applies_to": [], "behaviour": "do_it"}]},
            "applies to a class",
        ),
        (
            {
                "rules": [
                    {
                        "action": "Send",
                        "applies_to": ["google-workspace.send_gmail_message"],
                        "behaviour": "ask_first",
                    },
                    {
                        "action": "Mail",
                        "applies_to": ["google-workspace:0.0.1.send_gmail_message"],
                        "behaviour": "do_it",
                    },
                ]
            },
            "both apply to 'google-workspace.send_gmail_message'",
        ),
        (
            {"rules": [{"action": "Send", "applies_to": "send", "behaviour": "maybe"}]},
            "rules.0.behaviour",
        ),
        ({"emoji": "mail"}, "is one emoji"),
        ({"emoji": ""}, "is one emoji"),
        ({"avatar": "an astronaut"}, "named as its drawing is"),
        ({"banner": "svg-terms-hero"}, "named as its drawing is"),
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
    assert app_problems(app(agent="no-such-agent")) == [
        "There is no agent or Cog named 'no-such-agent'."
    ]
    assert "There is no Frame named 'nope'." in app_problems(app(context=["nope"]))
    # An organization's own context resolves among its organization's (LOOP U-32).
    assert app_problems(app(context=["org-house-style"]), ["org-house-style"]) == []
    assert app_problems(app(context=["org-house-style"]), []) == [
        "Its organization has no context named 'org-house-style'."
    ]
    assert app_problems(app(context=["org-house-style"])) == [
        "'org-house-style' is a context of an organization's own: it is checked with the "
        "organization the application belongs to, which was not said."
    ]
    assert "There is no Frame named 'nope'." in app_problems(
        app(context=["nope"]), ["org-house-style"]
    )
    assert "There is no model named 'nope'." in app_problems(app(model="nope"))
    assert "There is no Guard named 'nope'." in app_problems(app(checks={"guards": ["nope"]}))
    problems = app_problems(
        app(
            rules=[
                {"action": "Search", "applies_to": ["tavily.tavily_search"], "behaviour": "do_it"}
            ]
        )
    )
    assert any("not connected to 'tavily'" in problem for problem in problems)


def test_a_component_is_one_a_ui_plugin_renders() -> None:
    """LOOP C-13: the UI plugins' catalogs — what a layout names resolves, or is refused."""
    from agentspecs.apps import component_named

    assert component_named("Table")["standard"] is False  # type: ignore[index]
    assert component_named("ChoicePicker")["standard"] is True  # type: ignore[index]
    assert component_named("Marquee") is None
    refused = app(interface={"components": ["Text", "Marquee"]})
    assert app_problems(refused) == ["There is no component named 'Marquee' in the catalog."]
    surface = app(
        interface={
            "layout": "page",
            "surface": {
                "components": [
                    {"id": "root", "component": "Column", "children": ["ticker"]},
                    {"id": "ticker", "component": "Marquee"},
                ]
            },
        }
    )
    assert app_problems(surface) == [
        "The surface's 'ticker' is a 'Marquee', which the catalog does not have."
    ]


def test_a_page_composed_for_the_conversation_alone_is_a_problem() -> None:
    """A `chat` layout draws the conversation alone: a surface composed for it is not shown,
    which is said as agent-runtimes' `surfaceUnshown` says it; no catalogue app does it."""
    page = {"surface": {"components": [{"id": "root", "component": "Text", "text": "Hello"}]}}
    unshown = "Its page is composed but its layout is chat, the conversation alone: choose page or split to show it."
    assert app_problems(app(interface=page)) == [unshown]
    assert app_problems(app(interface={**page, "layout": "page"})) == []
    assert app_problems(app(interface={**page, "layout": "split"})) == []
    assert app_problems(app(kind="widget", interface={**page, "layout": "chat"})) == [unshown]
    for identity, found in APP_CATALOGUE.items():
        if found.interface.surface is not None and found.interface.surface.components:
            assert found.layout is not Layout.CHAT, identity
    assert APP_CATALOGUE["support-desk"].layout is Layout.PAGE


def test_a_rule_on_one_class_of_action_is_written_alone() -> None:
    """As a person writes it, and as agent-runtimes' TypeScript writer does."""
    rules = [
        {"action": "Send", "applies_to": ["send"], "behaviour": "ask_first"},
        {"action": "Draft", "applies_to": ["google-workspace.draft"], "behaviour": "do_it"},
        {"action": "Write", "applies_to": ["write", "publish"], "behaviour": "ask_first"},
    ]
    written = dump_app(app(rules=rules))["rules"]
    assert [rule["applies_to"] for rule in written] == [
        "send",
        ["google-workspace.draft"],
        ["write", "publish"],
    ]


def test_a_gate_reads_a_guard_the_application_runs() -> None:
    alone = app_problems(app(checks={"gates": ["low-confidence-review:0.0.1"]}))
    assert any("reads the Guard 'confidence-guard:0.0.1'" in problem for problem in alone)
    together = app(checks={"gates": ["low-confidence-review"], "guards": ["confidence-guard"]})
    assert app_problems(together) == []


def test_a_decision_is_asked_of_a_model_that_answers_decisions() -> None:
    def deciding(model: str) -> AppSpec:
        return app(kind="decision", decision={"question": "Which?", "decision_model": model})

    assert app_problems(deciding("cloudflare:gtw/typesafe/jev")) == []
    assert any("to decide with" in problem for problem in app_problems(deciding("typesafe/jev")))
    chat_model = "bedrock:us.anthropic.claude-sonnet-4-6"
    assert any(
        "does not answer typed decisions" in problem
        for problem in app_problems(deciding(chat_model))
    )


def test_a_rule_names_a_tool_its_connection_reaches() -> None:
    scoped = app(
        connections=[{"server": "google-workspace", "access": "write", "only": ["*gmail*"]}],
        rules=[
            {
                "action": "Search the Drive",
                "applies_to": ["google-workspace.search_drive_files"],
                "behaviour": "do_it",
            }
        ],
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
    (tmp_path / "broken.yaml").write_text(
        yaml.safe_dump({"id": "other", "name": "X", "kind": "chat"})
    )
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
        permissions={
            "spaces": [{"space": "support", "access": "write"}],
            "computer": {"browse": True},
        },
    )
    assert granted.emoji == "\U0001f4ec"
    assert granted.permissions.spaces[0].access is Access.WRITE
    assert granted.permissions.computer.browse and not granted.permissions.computer.shell
    # Every application of the catalogue has a face of its own.
    faces = [found.emoji for found in APP_CATALOGUE.values()]
    assert len(set(faces)) == len(faces) and "\U0001f440" not in faces


def test_an_application_chooses_its_avatar_and_banner_as_a_person_does() -> None:
    plain = app()
    # Unchosen: the emoji stands for the avatar, the id seeds the banner —
    # and nothing is written for either.
    assert (plain.avatar, plain.banner) == ("", "")
    assert "avatar" not in dump_app(plain) and "banner" not in dump_app(plain)
    chosen = app(avatar=" AstronautIcon ", banner="SvgTutorialsHero")
    assert (chosen.avatar, chosen.banner) == ("AstronautIcon", "SvgTutorialsHero")
    written = list(dump_app(chosen))
    # Beside its emoji, in the order the spec declares them.
    assert written.index("avatar") == written.index("banner") - 1
    assert parse_app(dump_app(chosen)) == chosen
    # A validator outside Python checks the same shape.
    pattern = re.compile(json_schema()["properties"]["avatar"]["pattern"])
    assert pattern.match("AstronautIcon") and pattern.match("") and pattern.match(" AstronautIcon ")
    assert not pattern.match("an astronaut")
    assert json_schema()["properties"]["banner"]["pattern"] == pattern.pattern


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
def test_a_rule_on_a_class_decides_every_tool_of_that_class(
    action: ActionClass, behaviour: Behaviour
) -> None:
    ruled = app(
        rules=[{"action": "The rule", "applies_to": action.value, "behaviour": behaviour.value}]
    )
    assert behaviour_for(ruled, "google-workspace.some_tool", classes=[action]) is behaviour


def test_a_tool_of_several_classes_takes_the_most_restricted() -> None:
    assert (
        strictest([Behaviour.DO_IT, Behaviour.ASK_FIRST, Behaviour.IF_ASKED]) is Behaviour.ASK_FIRST
    )
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
            {
                "action": "Label",
                "applies_to": ["google-workspace:0.0.1.modify_gmail_message_labels"],
                "behaviour": "do_it",
            },
        ]
    )
    label = "google-workspace.modify_gmail_message_labels"
    assert behaviour_for(ruled, label, arguments={"remove_label_ids": ["INBOX"]}) is Behaviour.DO_IT
    assert behaviour_for(ruled, "google-workspace.draft_gmail_message") is Behaviour.ASK_FIRST


def test_a_rule_that_names_a_tool_does_not_cover_what_its_arguments_make_it_do_besides() -> None:
    label = "google-workspace.modify_gmail_message_labels"
    ruled = app(
        rules=[{"action": "Label and archive", "applies_to": [label], "behaviour": "do_it"}]
    )
    # Labelling is done. Trashing is a deletion, and no rule lets it: it waits for a person.
    assert behaviour_for(ruled, label, arguments={"add_label_ids": ["STARRED"]}) is Behaviour.DO_IT
    assert (
        behaviour_for(ruled, label, arguments={"add_label_ids": ["TRASH"]}) is Behaviour.ASK_FIRST
    )
    # Nobody said what it is asked: the worst it can do.
    assert behaviour_for(ruled, label) is Behaviour.ASK_FIRST
    forbidden = app(
        rules=[
            {"action": "Label and archive", "applies_to": [label], "behaviour": "do_it"},
            {"action": "Delete", "applies_to": "delete", "behaviour": "leave_to_me"},
        ]
    )
    assert (
        behaviour_for(forbidden, label, arguments={"add_label_ids": ["TRASH"]})
        is Behaviour.LEAVE_TO_ME
    )
    assert (
        behaviour_for(forbidden, label, arguments={"remove_label_ids": ["INBOX"]})
        is Behaviour.DO_IT
    )


def test_a_tool_nobody_classed_is_left_to_the_person_unless_a_rule_names_it() -> None:
    assert behaviour_for(app(), "google-workspace.a_tool_added_tomorrow") is Behaviour.LEAVE_TO_ME
    named = app(
        rules=[
            {
                "action": "New",
                "applies_to": ["google-workspace.a_tool_added_tomorrow"],
                "behaviour": "ask_first",
            }
        ]
    )
    assert behaviour_for(named, "google-workspace.a_tool_added_tomorrow") is Behaviour.ASK_FIRST


def test_an_application_reaches_nothing_it_does_not_name() -> None:
    # Not connected: even a search is left to the person.
    assert behaviour_for(app(), "tavily.tavily_search") is Behaviour.LEAVE_TO_ME
    # Connected, but the connection leaves the tool out.
    scoped = app(
        connections=[{"server": "google-workspace", "access": "write", "only": ["*gmail*"]}]
    )
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


def test_a_forward_outside_the_organization_publishes() -> None:
    send = "google-workspace.send_gmail_message"
    mailbox = {"user_google_email": "eric@datalayer.io"}
    # A reply, to anybody, is a send.
    assert classes_of(send, {**mailbox, "to": "client@acme.com", "thread_id": "t1"}) == (ActionClass.SEND,)
    # A forward inside the organization is a send.
    inside = {**mailbox, "to": "Ana <ana@datalayer.io>", "forward_message_id": "m1"}
    assert classes_of(send, inside) == (ActionClass.SEND,)
    # A forward with anybody outside, whichever field names them, also publishes.
    for outside in (
        {**inside, "to": "lawyer@firm.com"},
        {**inside, "cc": ["ana@datalayer.io", "lawyer@firm.com"]},
        {**inside, "bcc": "ana@datalayer.io, x@gmail.com"},
    ):
        assert classes_of(send, outside) == (ActionClass.SEND, ActionClass.PUBLISH), outside
    # Fails closed: a forward that does not say its mailbox is outside.
    assert forwards_outside("google-workspace", "send_gmail_message", {"to": "ana@datalayer.io", "forward_message_id": "m1"})
    # Another tool, or no call, is not told anything.
    assert not forwards_outside("google-workspace", "draft_gmail_message", {**inside, "to": "x@y.z"})
    assert classes_of(send) == (ActionClass.SEND,)


def test_inbox_triage_forwards_outside_nothing_and_leaves_it_to_me() -> None:
    triage = APP_CATALOGUE["inbox-triage"]
    send = "google-workspace.send_gmail_message"
    mailbox = {"user_google_email": "eric@datalayer.io"}
    assert behaviour_for(triage, send, arguments={**mailbox, "to": "client@acme.com", "thread_id": "t"}) is Behaviour.ASK_FIRST
    forward = {**mailbox, "forward_message_id": "m1"}
    assert behaviour_for(triage, send, arguments={**forward, "to": "ana@datalayer.io"}) is Behaviour.ASK_FIRST
    assert behaviour_for(triage, send, arguments={**forward, "to": "lawyer@firm.com"}) is Behaviour.LEAVE_TO_ME
    # Its rules say the four behaviours, with the defaults of the plan (LOOP W-04).
    said = {rule.action: rule.behaviour for rule in triage.rules}
    assert said["Label and archive a message"] is Behaviour.DO_IT
    assert said["Draft a reply"] is Behaviour.DO_IT
    assert said["Send a message"] is Behaviour.ASK_FIRST
    assert said["Delete anything"] is Behaviour.LEAVE_TO_ME
    assert said["Forward outside the organization, share or publish anything"] is Behaviour.LEAVE_TO_ME
    # When a message arrives, it is told what to do.
    [arrives] = [trigger for trigger in triage.triggers if trigger.event == "email_received"]
    assert "Send nothing yourself" in arrives.prompt


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
        assert (
            behaviour_for(triage, f"google-workspace.{tool}", arguments=arguments)
            is Behaviour.LEAVE_TO_ME
        ), tool
    # And it says so: where what a tool is asked changes what it does.
    escalations = tool_escalations(triage)
    assert escalations["google-workspace.modify_gmail_message_labels"] == [
        {
            "argument": "add_label_ids",
            "classes": ["delete"],
            "includes": ["TRASH", "SPAM"],
            "behaviour": "leave_to_me",
        }
    ]
    # Nothing outside the mailbox is reached, and nothing it reaches sends by itself.
    reached = {
        name for name, behaviour in decided.items() if behaviour is not Behaviour.LEAVE_TO_ME
    }
    assert reached and all("gmail" in name for name in reached)
    alone = {name for name, behaviour in decided.items() if behaviour is Behaviour.DO_IT}
    for name in alone:
        classes = set(classes_of(f"google-workspace.{name}", {}))
        assert classes <= {ActionClass.READ, ActionClass.WRITE}, name
    # No argument of any call makes it delete, publish or buy by itself.
    for ref in tool_behaviours(triage):
        for condition in server_tool_conditions(
            server_specs()["google-workspace"], ref.split(".")[1]
        ):
            values = condition.includes or condition.equals
            arguments = {condition.argument: [values[0]] if condition.includes else values[0]}
            assert behaviour_for(triage, ref, arguments=arguments) is not Behaviour.DO_IT, ref


def test_a_server_classed_by_a_pattern_is_reported_by_that_pattern(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agentspecs import apps as module

    servers = dict(module._catalogue("mcp-servers"))
    servers["drawer"] = {
        "id": "drawer",
        "actions": {"checked": "2026-10-02", "tools": {"generate_*": "read", "erase_*": "delete"}},
    }
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
    assert SCHEMA_PATH.read_text() == schema_text(), (
        "run `python -m agentspecs.apps` to write it again"
    )


def test_the_schema_names_the_fields_as_the_yaml_does() -> None:
    schema = json_schema()
    assert schema["title"] == "Appspec"
    assert {
        "schema",
        "id",
        "kind",
        "agent",
        "connections",
        "rules",
        "interface",
        "tests",
        "record",
    } <= set(schema["properties"])
    assert "as" in schema["$defs"]["AppConnection"]["properties"]
    assert schema["additionalProperties"] is False
    # A validator outside Python refuses another version too.
    assert schema["properties"]["schema"]["const"] == APP_SCHEMA
    assert json.loads(SCHEMA_PATH.read_text())["$id"].endswith(f"{APP_SCHEMA}.json")


def test_every_application_file_is_named_for_its_id() -> None:
    for path in APPS_DIR.glob("*.yaml"):
        assert yaml.safe_load(path.read_text())["id"] == path.stem


def test_the_reference_says_every_field_and_is_the_one_in_the_docs() -> None:
    from agentspecs.apps.reference import REFERENCE_PATH, reference_markdown

    page = reference_markdown()
    schema = json_schema()
    for name in schema["properties"]:
        assert f"| `{name}`" in page, name
    for name, spec in schema["$defs"].items():
        assert name in page, name
    # An example of every field…
    for name in schema["properties"]:
        assert f"### `{name}`" in page, f"no example of {name}"
    # …and the ones written for the reference are ones the spec accepts.
    from agentspecs.apps.reference import EXTRA_EXAMPLES

    base = yaml.safe_load((Path(agentspecs.apps.__file__).parent / "web-research.yaml").read_text())
    for key, value in EXTRA_EXAMPLES.items():
        document = {**base, key: value}
        if key == "team":
            document.pop("agent")
        parse_app(document)
    if REFERENCE_PATH.exists():
        assert REFERENCE_PATH.read_text() == page, "run `python -m agentspecs.apps`"


# --- whether its conversations may suggest tests (LOOP V-16) ----------------------------


def test_conversations_suggest_no_test_unless_said() -> None:
    assert app().record.suggest_tests is False
    assert "suggest_tests" not in dump_app(app()).get("record", {})
    allowed = app(record={"suggest_tests": True})
    assert allowed.record.suggest_tests is True
    assert dump_app(allowed)["record"]["suggest_tests"] is True
    with pytest.raises(AppError, match="record.suggest_tests"):
        app(record={"suggest_tests": "yes please"})


# --- outputs --------------------------------------------------------------------------


def test_outputs_are_plain_text_alone_unless_said() -> None:
    assert app().interface.outputs == []


def test_accounting_answers_in_markdown_and_a_notebook() -> None:
    accounting = get_app("accounting")
    assert accounting is not None
    assert accounting.interface.outputs == ["text/markdown", "application/x-ipynb+json"]
    assert app_problems(accounting) == []
    # Written back as it was read.
    assert dump_app(accounting)["interface"]["outputs"] == [
        "text/markdown",
        "application/x-ipynb+json",
    ]


@pytest.mark.parametrize(
    "outputs, refusal",
    [
        (["notebook"], "'notebook' is not a media type"),
        (["Text/Markdown"], "is not a media type"),
        (["text/markdown; charset=utf-8"], "is not a media type"),
        (["text/markdown", "text/markdown"], "an output is named twice"),
        (["application/x-ipynb+json"], "words first"),
        ("text/markdown", "valid list"),
    ],
)
def test_an_output_that_is_not_a_media_type_is_refused(outputs: object, refusal: str) -> None:
    with pytest.raises(AppError, match=re.escape(refusal)):
        app(interface={"outputs": outputs})


def test_an_output_the_catalogue_does_not_give_is_a_problem() -> None:
    from agentspecs.apps import output_media_types

    assert "application/x-ipynb+json" in output_media_types()
    found = app(interface={"outputs": ["text/plain", "application/x-unknown"]})
    assert any(
        "'application/x-unknown' is no format of the outputs catalogue" in p
        for p in app_problems(found)
    )


# --- what the record keeps, as its record or its Track says (LOOP R-07) ---------------


def test_the_record_keeps_what_it_says_for_as_long_as_it_says() -> None:
    from agentspecs.apps import kept_record

    kept = kept_record("90_days", ["conversations", "actions", "conversations"])
    assert (kept.days, kept.include, kept.track) == (90, ("conversations", "actions"), "")


def test_a_track_decides_the_retention_and_keeps_its_items_besides() -> None:
    from agentspecs.apps import TRACK_KEEPS, kept_record
    from agentspecs.tracks import TrackItem, get_track

    kept = kept_record("30_days", ["conversations"], "financial-reporting:0.0.1")
    assert kept.track == "financial-reporting"
    assert kept.days == get_track("financial-reporting").retention_days == 2555
    assert kept.include[0] == "conversations"
    assert {"actions", "approvals", "checks", "decisions", "outputs", "sources"} <= set(kept.include)
    # Every item a Track keeps is one a Track may include, kept as a record item.
    assert set(TRACK_KEEPS) <= {item.value for item in TrackItem}
    record_items = {item.value for item in agentspecs.apps.RecordItem}
    assert all(set(words) <= record_items for words in TRACK_KEEPS.values())


def test_the_pipeline_report_keeps_what_its_track_says() -> None:
    from agentspecs.apps import get_app, kept_record

    app = get_app("pipeline-report")
    kept = kept_record(app.record.keep_for, app.record.include, app.checks.track)
    assert kept.track == "financial-reporting" and kept.days == 2555


def test_a_track_the_catalogue_does_not_have_is_said() -> None:
    from agentspecs.apps import AppError, kept_record

    with pytest.raises(AppError, match="There is no Track named 'ghost'"):
        kept_record("1_years", [], "ghost")


def test_a_form_asks_named_fields() -> None:
    """LOOP C-16: a Form block is the JSON Schema of what it asks — an object
    whose fields are named, each required one among them."""

    def page(form: dict) -> AppSpec:
        return app(
            interface={
                "layout": "page",
                "surface": {
                    "components": [
                        {"id": "root", "component": "Column", "children": ["quote"]},
                        {"id": "quote", "component": "Form", **form},
                    ]
                },
            }
        )

    seats = {"type": "object", "required": ["seats"], "properties": {"seats": {"type": "integer", "minimum": 1}}}
    assert app_problems(page({"schema": seats})) == []
    assert app_problems(page({})) == ["The form 'quote' has no fields: its schema is the JSON Schema of what it asks."]
    assert app_problems(page({"schema": {"type": "string"}})) == [
        "The form 'quote' asks for no named field: its schema is an object with properties."
    ]
    assert app_problems(page({"schema": {**seats, "required": ["seats", "reason"]}})) == [
        "The form 'quote' requires 'reason', which it does not ask."
    ]

