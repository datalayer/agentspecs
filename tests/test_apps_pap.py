# Copyright (c) 2025-2026 Datalayer, Inc.
# Distributed under the terms of the Modified BSD License.

"""Personal Agent Protocol in the Appspec (S-01, S-02, S-03)."""

from pathlib import Path

import pytest
import yaml

import agentspecs.apps
from agentspecs.apps import PAP_PROFILES, AppPap, parse_app

BASE = {**yaml.safe_load((Path(agentspecs.apps.__file__).parent / "web-research.yaml").read_text()), "protocols": ["pap"]}

CONNECTION = {
    "id": "orders",
    "company": "manzanita.example",
    "access": "write",
    "as": "user",
    "scopes": ["orders:read", "orders:write"],
    "interfaces": ["agent", "openapi"],
    "sign_in": ["direct", "device"],
    "extensions": ["operations"],
}


#: A company's scopes (PAP draft 0.3 §4.4): each with what it allows, and its hints when the Maker gives them.
READ = {"name": "orders:read", "description": "Read your orders", "changes": "none", "personal_data": True}
WRITE = {"name": "orders:write", "description": "Exchange an order you approved"}


def app(**pap: object):  # type: ignore[no-untyped-def]
    return parse_app({**BASE, "pap": {"profile": "draft-01", **pap}})


def test_a_company_connection_and_the_company_role_parse() -> None:
    spec = app(connections=[CONNECTION], company={"enabled": True, "scopes": [READ]})
    assert spec.pap.connections[0].company == "manzanita.example"
    assert spec.pap.connections[0].acts_as.value == "user"
    assert spec.pap.company.enabled


def test_an_application_without_pap_has_none() -> None:
    spec = parse_app(BASE)
    assert spec.pap == AppPap()
    assert spec.pap.profile is None


def test_a_pap_block_names_a_profile_datalayer_speaks() -> None:
    assert app(connections=[CONNECTION]).pap.profile == "draft-01"
    assert PAP_PROFILES == ("draft-01",)
    with pytest.raises(ValueError, match="names no Personal Agent Protocol profile: add `profile: draft-01`"):
        parse_app({**BASE, "pap": {"connections": [CONNECTION]}})
    with pytest.raises(ValueError, match="names no Personal Agent Protocol profile"):
        parse_app({**BASE, "pap": {"company": {"enabled": True}}})
    with pytest.raises(
        ValueError,
        match="This application asks for Personal Agent Protocol profile “draft-02”; Datalayer speaks draft-01.",
    ):
        app(profile="draft-02", connections=[CONNECTION])


def test_the_profile_is_written_back_with_the_block() -> None:
    import json

    spec = app(connections=[CONNECTION])
    dumped = json.loads(spec.model_dump_json(by_alias=True, exclude_defaults=True))
    assert dumped["pap"]["profile"] == "draft-01"
    assert "pap" not in json.loads(parse_app(BASE).model_dump_json(by_alias=True, exclude_defaults=True))


@pytest.mark.parametrize(
    "company",
    [
        "https://manzanita.example",
        "manzanita.example/poppy",
        "manzanita.example:443",
        "127.0.0.1",
        "MANZANITA",
    ],
)
def test_the_company_is_a_domain_and_nothing_else(company: str) -> None:
    with pytest.raises(ValueError, match="not a company domain"):
        app(connections=[{**CONNECTION, "company": company}])


@pytest.mark.parametrize(
    "key", ["token", "access_token", "client_secret", "endpoint", "issuer", "private_key"]
)
def test_no_credential_or_endpoint_is_accepted(key: str) -> None:
    with pytest.raises(ValueError):
        app(connections=[{**CONNECTION, key: "anything"}])


def test_scopes_extensions_and_sign_in_are_checked() -> None:
    with pytest.raises(ValueError, match="OAuth scope"):
        app(connections=[{**CONNECTION, "scopes": ["has space"]}])
    with pytest.raises(ValueError, match="extension name"):
        app(connections=[{**CONNECTION, "extensions": ["Gift Wrap"]}])
    app(connections=[{**CONNECTION, "extensions": ["operations", "example.com/gift-wrap"]}])
    with pytest.raises(ValueError, match="sign-in mode"):
        app(connections=[{**CONNECTION, "sign_in": []}])


def test_web_waits_for_an_isolated_browser() -> None:
    with pytest.raises(ValueError, match="isolated browser"):
        app(connections=[{**CONNECTION, "interfaces": ["web"]}])


def test_the_same_company_twice_is_refused() -> None:
    with pytest.raises(ValueError, match="same company twice"):
        app(connections=[CONNECTION, {**CONNECTION, "id": "orders-2"}])
    # Even in another name: the application's grant names a company once.
    with pytest.raises(ValueError, match="same company twice"):
        app(connections=[CONNECTION, {**CONNECTION, "id": "orders-owner", "as": "owner"}])


OPERATION = {
    "action": "orders.exchange",
    "tool": "exchange_order",
    "summary": "Exchange order {order_id} for size {size}",
}


def test_a_company_declares_what_it_does_once_the_person_confirms() -> None:
    spec = app(company={"enabled": True, "scopes": [WRITE], "extensions": ["operations"],
                        "operations": [OPERATION]})
    operation = spec.pap.company.operations[0]
    assert (operation.action, operation.tool) == ("orders.exchange", "exchange_order")
    # Only the person confirms it unless the Maker says otherwise.
    assert operation.user_approval_required is True


@pytest.mark.parametrize(
    ("change", "says"),
    [
        ({"action": "Orders Exchange"}, "action name"),
        ({"summary": "Exchange {order.id}"}, "names no term"),
        ({"summary": "Exchange {order_id"}, "not a template"),
        ({"summary": "  "}, "says what it does"),
    ],
)
def test_an_operation_is_checked(change: dict, says: str) -> None:
    with pytest.raises(ValueError, match=says):
        app(company={"enabled": True, "scopes": [WRITE], "extensions": ["operations"],
                     "operations": [{**OPERATION, **change}]})


def test_operations_need_the_extension_and_each_action_and_tool_once() -> None:
    with pytest.raises(ValueError, match="`operations` extension"):
        app(company={"enabled": True, "scopes": [WRITE], "operations": [OPERATION]})
    with pytest.raises(ValueError, match="declared twice"):
        app(company={"enabled": True, "scopes": [WRITE], "extensions": ["operations"],
                     "operations": [OPERATION, {**OPERATION, "tool": "other"}]})
    with pytest.raises(ValueError, match="one action"):
        app(company={"enabled": True, "scopes": [WRITE], "extensions": ["operations"],
                     "operations": [OPERATION, {**OPERATION, "action": "orders.other"}]})


def test_a_company_reached_over_mcp_and_by_registered_agents_only() -> None:
    agent = "https://agents.example/agent.json"
    company = {"enabled": True, "scopes": [READ]}
    registered = {**company, "personal_agents": "registered"}
    spec = app(company={**registered, "interfaces": ["agent", "mcp"], "registered_agents": [agent]})
    assert spec.pap.company.registered_agents == [agent]
    with pytest.raises(ValueError, match="names at least one"):
        app(company=registered)
    with pytest.raises(ValueError, match="accepts them alone"):
        app(company={**company, "registered_agents": [agent]})
    for wrong in ("http://agents.example/a.json", "agents.example", "https://u@agents.example/a.json"):
        with pytest.raises(ValueError, match="client_id"):
            app(company={**registered, "registered_agents": [wrong]})
    with pytest.raises(ValueError, match="twice"):
        app(company={**registered, "registered_agents": [agent, agent]})
    # Its pages too: a browser joins the person's Session through the one-time-code form (draft 0.3).
    assert [i.value for i in app(company={**company, "interfaces": ["agent", "web"]}).pap.company.interfaces] == [
        "agent",
        "web",
    ]
    with pytest.raises(ValueError, match="each once"):
        app(company={**company, "interfaces": ["web", "web"]})
    with pytest.raises(ValueError, match="at least one way"):
        app(company={**company, "interfaces": []})


#: The Ledgerly pattern (R-07): confirming it lets the application pay at its bank without asking.
STANDING = {
    "action": "payments.allow",
    "summary": "Let it pay {payee} from your bank account without asking, up to {currency} {maximum} each, "
    "at most {uses} payments, for {days} days",
    "allows": {
        "connection": "orders",
        "action": "buy",
        "limits": [
            {"path": "payee", "allowed": "payee"},
            {"path": "amount.amount", "maximum": "maximum"},
            {"path": "amount.currency", "allowed": "currency"},
        ],
        "uses": "uses",
        "days": "days",
    },
}


def test_a_standing_permission_is_an_operation_the_person_confirms() -> None:
    """R-07, decided 2026-10-13: given through a company's Operation, recorded as the approval in advance
    the person would give in Datalayer — at one of its own companies, in the person's account there."""
    company = {"enabled": True, "scopes": [{"name": "books:write", "description": "Give a standing permission"}], "extensions": ["operations"], "operations": [STANDING]}
    spec = app(connections=[CONNECTION], company=company)
    [operation] = spec.pap.company.operations
    assert operation.tool is None and operation.allows is not None
    assert operation.allows.terms() == ["payee", "maximum", "currency", "uses", "days"]
    assert operation.user_approval_required is True
    for change, says in (
        ({"tool": "allow_payments"}, "calls a tool or allows a standing permission, one of them"),
        ({"user_approval_required": False}, "only the person confirms it"),
        ({"summary": "Let it pay {payee} up to {currency} {maximum}"}, r"`\{uses\}` is not in it"),
        ({"allows": {**STANDING["allows"], "connection": "bank"}}, "not one of its company connections"),
        ({"allows": {**STANDING["allows"], "action": "delete"}}, "allows"),
        ({"allows": {**STANDING["allows"], "limits": []}}, "between 1 and 20"),
        ({"allows": {**STANDING["allows"], "limits": [{"path": "payee", "allowed": "payee", "maximum": "m"}]}},
         "one of them"),
    ):
        with pytest.raises(ValueError, match=says):
            app(connections=[CONNECTION], company={**company, "operations": [{**STANDING, **change}]})
    for connection, says in (({**CONNECTION, "as": "owner"}, "each person's own account"),
                             ({**CONNECTION, "access": "read", "scopes": ["orders:read"]}, "reads and changes")):
        with pytest.raises(ValueError, match=says):
            app(connections=[connection], company=company)
    with pytest.raises(ValueError, match="calls a tool or allows"):
        app(company={**company, "operations": [{key: value for key, value in STANDING.items() if key != "allows"}]})


def test_a_company_scope_says_what_it_allows_with_its_hints() -> None:
    spec = app(company={"enabled": True, "scopes": [READ, WRITE]})
    read, write = spec.pap.company.scopes
    assert (read.name, read.description, read.changes.value, read.personal_data) == (
        "orders:read",
        "Read your orders",
        "none",
        True,
    )
    # Hints left out are derived from the tools behind the scope.
    assert (write.changes, write.personal_data) == (None, None)
    assert spec.pap.company.scope_names() == ["orders:read", "orders:write"]


@pytest.mark.parametrize(
    ("scope", "says"),
    [
        ("orders:read", "valid dictionary"),
        ({"name": "orders:read"}, "description"),
        ({"name": "orders:read", "description": " "}, "says what it allows"),
        ({"name": "poppy:read", "description": "Read"}, "reserved `poppy:` prefix"),
        ({"name": "orders read", "description": "Read"}, "not an OAuth scope"),
        ({"name": "orders:read", "description": "Read", "changes": "some"}, "changes"),
    ],
)
def test_a_company_scope_is_checked(scope: object, says: str) -> None:
    with pytest.raises(ValueError, match=says):
        app(company={"enabled": True, "scopes": [scope]})


def test_a_scope_is_offered_once_and_a_connection_never_asks_for_poppy() -> None:
    with pytest.raises(ValueError, match="named twice"):
        app(company={"enabled": True, "scopes": [READ, {**READ, "description": "Again"}]})
    with pytest.raises(ValueError, match="reserved `poppy:` prefix"):
        app(connections=[{**CONNECTION, "scopes": ["poppy:read"]}])


def test_a_company_lists_the_tasks_it_does_not_offer_with_another_way() -> None:
    change = {
        "references": [
            {"type": "web", "url": "https://manzanita.example/account"},
            {"type": "mcp", "url": "https://manzanita.example/mcp", "tool": "change_address"},
            {"type": "openapi", "url": "https://manzanita.example/openapi.json", "operation_id": "changeAddress"},
        ]
    }
    spec = app(
        company={
            "enabled": True,
            "scopes": [READ],
            "excluded_tasks": [
                {"task": "Cancel an order", "alternative": {"instructions": "Cancel it on the website."}},
                {"task": "Change the delivery address", "alternative": change},
                {"task": "Talk to the warehouse"},
            ],
        }
    )
    cancel, address, warehouse = spec.pap.company.excluded_tasks
    assert cancel.alternative is not None and cancel.alternative.instructions == "Cancel it on the website."
    assert address.alternative is not None
    assert [ref.type.value for ref in address.alternative.references] == ["web", "mcp", "openapi"]
    assert warehouse.alternative is None


def _refer(**reference: str) -> dict:
    return {"task": "Cancel", "alternative": {"references": [reference]}}


@pytest.mark.parametrize(
    ("task", "says"),
    [
        ({"task": ""}, "1 to 200 characters"),
        ({"task": "x" * 201}, "1 to 200 characters"),
        ({"task": "Cancel", "alternative": {}}, "instructions or references"),
        ({"task": "Cancel", "alternative": {"instructions": "x" * 2001}}, "1 to 2000"),
        (_refer(type="mcp", url="https://a.example/mcp"), "`tool`"),
        (_refer(type="openapi", url="https://a.example/o.json"), "`operation_id`"),
        (_refer(type="web", url="http://a.example/"), "HTTPS"),
        (_refer(type="web", url="https://a.example/", tool="t"), "only an `mcp` reference"),
        (_refer(type="email", url="https://a.example/"), "type"),
    ],
)
def test_an_excluded_task_is_checked(task: dict, says: str) -> None:
    with pytest.raises(ValueError, match=says):
        app(company={"enabled": True, "scopes": [READ], "excluded_tasks": [task]})


def test_an_excluded_task_is_listed_once() -> None:
    with pytest.raises(ValueError, match="listed twice"):
        app(company={"enabled": True, "excluded_tasks": [{"task": "Cancel"}, {"task": "cancel "}]})
