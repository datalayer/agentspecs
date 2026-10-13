# Copyright (c) 2025-2026 Datalayer, Inc.
# Distributed under the terms of the Modified BSD License.

"""The Appspec's `commerce` block (AGENT_PROTOCOLS PI-01): merchants over UCP or ACP,
test merchants only, each purchase asked of the person (decided 2026-10-13)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentspecs.apps import APP_CATALOGUE, AppCommerceMerchant, AppSpec

BASE = {"id": "shop", "name": "Shop", "kind": "chat", "agent": "a"}
STORE = {"id": "store", "protocol": "ucp", "merchant": "store.example", "access": "write",
         "limit": {"amount": "12.50", "currency": "USD"}}


def test_a_merchant_is_a_domain_a_protocol_a_level_and_a_limit_to_buy():
    spec = AppSpec.model_validate({**BASE, "protocols": ["ucp"], "commerce": {"merchants": [STORE]}})
    [merchant] = spec.commerce.merchants
    assert (merchant.protocol.value, merchant.merchant, merchant.access.value) == ("ucp", "store.example", "write")
    assert merchant.limit.minor_units == 1250
    browse = AppCommerceMerchant.model_validate({"id": "s", "protocol": "acp", "merchant": "outfitters.example"})
    assert browse.access.value == "read" and browse.limit is None


@pytest.mark.parametrize(
    "change,why",
    [
        ({"merchant": "https://store.example"}, "only the domain"),
        ({"protocol": "paypal"}, "protocol"),
        ({"limit": None}, "say the most one purchase may cost"),
        ({"access": "read"}, "a spending limit says nothing"),
        ({"limit": {"amount": "0", "currency": "USD"}}, "not an amount"),
        ({"limit": {"amount": "12.505", "currency": "USD"}}, "not an amount"),
        ({"limit": {"amount": "12", "currency": "usd"}}, "not a currency"),
        ({"token": "tok_x"}, "Extra inputs"),
        ({"id": "Store"}, "not a merchant id"),
    ],
)
def test_a_merchant_is_refused(change, why):
    with pytest.raises(ValidationError, match=why):
        AppCommerceMerchant.model_validate({**STORE, **change})


@pytest.mark.parametrize(
    "commerce,protocols,why",
    [
        ({"merchants": [STORE, {**STORE, "merchant": "other.example"}]}, ["ucp"], "same id"),
        ({"merchants": [STORE, {**STORE, "id": "again", "protocol": "acp"}]}, ["ucp", "acp"], "same merchant twice"),
        ({"merchants": [STORE]}, [], "add 'ucp' to `protocols`"),
        ({"merchants": [{**STORE, "protocol": "acp"}]}, ["ucp"], "add 'acp' to `protocols`"),
    ],
)
def test_an_application_shopping_is_refused(commerce, protocols, why):
    with pytest.raises(ValidationError, match=why):
        AppSpec.model_validate({**BASE, "protocols": protocols, "commerce": commerce})


def test_the_shopping_assistant_buys_at_a_test_store_asking_first():
    app = APP_CATALOGUE["shopping-assistant"]
    assert app.protocols == ["ucp"] and not app.enabled
    [merchant] = app.commerce.merchants
    assert (merchant.merchant, merchant.limit.amount, merchant.limit.currency) == ("store.example", "50", "USD")
    assert {rule.behaviour.value for rule in app.rules if "buy" in [str(getattr(t, "value", t)) for t in rule.targets]} <= {"ask_first"}
