# Copyright (c) 2025-2026 Datalayer, Inc.
# Distributed under the terms of the Modified BSD License.

"""Personal Agent Protocol in the Appspec (PAP_DATALAYER S-01, S-02)."""

from pathlib import Path

import pytest
import yaml

import agentspecs.apps
from agentspecs.apps import AppPap, parse_app

BASE = yaml.safe_load((Path(agentspecs.apps.__file__).parent / "web-research.yaml").read_text())

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


def app(**pap: object):  # type: ignore[no-untyped-def]
    return parse_app({**BASE, "pap": pap})


def test_a_company_connection_and_the_company_role_parse() -> None:
    spec = app(connections=[CONNECTION], company={"enabled": True, "scopes": ["poppy:read"]})
    assert spec.pap.connections[0].company == "manzanita.example"
    assert spec.pap.connections[0].acts_as.value == "user"
    assert spec.pap.company.enabled


def test_an_application_without_pap_has_none() -> None:
    spec = parse_app(BASE)
    assert spec.pap == AppPap()


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
    spec = app(company={"enabled": True, "scopes": ["orders:write"], "extensions": ["operations"],
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
        app(company={"enabled": True, "scopes": ["orders:write"], "extensions": ["operations"],
                     "operations": [{**OPERATION, **change}]})


def test_operations_need_the_extension_and_each_action_and_tool_once() -> None:
    with pytest.raises(ValueError, match="`operations` extension"):
        app(company={"enabled": True, "scopes": ["orders:write"], "operations": [OPERATION]})
    with pytest.raises(ValueError, match="declared twice"):
        app(company={"enabled": True, "scopes": ["orders:write"], "extensions": ["operations"],
                     "operations": [OPERATION, {**OPERATION, "tool": "other"}]})
    with pytest.raises(ValueError, match="one action"):
        app(company={"enabled": True, "scopes": ["orders:write"], "extensions": ["operations"],
                     "operations": [OPERATION, {**OPERATION, "action": "orders.other"}]})
