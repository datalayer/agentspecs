# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The Appspec's `pact` block: businesses asked over PACT 1.0 (AGENT_PROTOCOLS PI-01)."""

import pytest
from pydantic import ValidationError

from agentspecs.apps import AppSpec

BASE = {"id": "support", "name": "Support", "kind": "chat", "agent": "a", "protocols": ["pact"]}
AIR = {
    "id": "air",
    "brand": "air.example",
    "audience": "https://provider.example/a2a",
    "scopes": ["bookings:read"],
}


def test_a_business_is_its_domain_and_its_providers_audience():
    spec = AppSpec.model_validate({**BASE, "pact": {"connections": [AIR]}})
    [connection] = spec.pact.connections
    assert (connection.brand, connection.access.value) == ("air.example", "read")
    assert AppSpec.model_validate(BASE).pact.connections == []


@pytest.mark.parametrize(
    "change,why",
    [
        ({"brand": "https://air.example/"}, "only the domain"),
        ({"audience": ""}, "audience"),
        ({"scopes": ["bookings"]}, "resource:verb"),
        ({"scopes": ["bookings:read", "bookings:read"]}, "twice"),
        ({"token": "x"}, "Extra inputs"),
    ],
)
def test_what_a_connection_refuses(change, why):
    with pytest.raises(ValidationError, match=why):
        AppSpec.model_validate({**BASE, "pact": {"connections": [{**AIR, **change}]}})


def test_one_connection_per_business():
    with pytest.raises(ValidationError, match="same business twice"):
        AppSpec.model_validate({**BASE, "pact": {"connections": [AIR, {**AIR, "id": "again"}]}})


# --- answering as a business (AGENT_PROTOCOLS PR-13, PI-32; decided 2026-10-13) -------------

AGENT = {
    "issuer": "https://iam.example/api/iam/v1/pap/agents/app-1",
    "jwks_uri": "https://iam.example/api/iam/v1/pap/agents/app-1/jwks.json",
}
BUSINESS = {
    "enabled": True,
    "scopes": {"bookings:read": "See your bookings", "bookings:change": "Change a booking"},
    "registered_agents": [AGENT],
}


def test_a_business_names_its_scopes_and_the_personal_agents_it_accepts():
    spec = AppSpec.model_validate({**BASE, "pact": {"business": BUSINESS}})
    business = spec.pact.business
    assert business.enabled and business.brand == ""
    assert business.scopes == {"bookings:read": "See your bookings", "bookings:change": "Change a booking"}
    assert [agent.issuer for agent in business.registered_agents] == [AGENT["issuer"]]
    # Off by default, and an application without the block is no business.
    assert not AppSpec.model_validate(BASE).pact.business.enabled
    # Its protocol is listed, as for the connections.
    with pytest.raises(ValidationError, match="add 'pact' to `protocols`"):
        AppSpec.model_validate({**BASE, "protocols": [], "pact": {"business": BUSINESS}})


@pytest.mark.parametrize(
    "change,why",
    [
        ({"registered_agents": []}, "name at least one"),
        ({"registered_agents": [AGENT, AGENT]}, "registered twice"),
        ({"registered_agents": [{**AGENT, "issuer": "http://iam.example/a"}]}, "an HTTPS URL"),
        ({"registered_agents": [{**AGENT, "jwks_uri": "https://iam.example/k?x=1"}]}, "an HTTPS URL"),
        ({"registered_agents": [{"issuer": AGENT["issuer"]}]}, "jwks_uri"),
        ({"scopes": {"bookings": "See"}}, "resource:verb"),
        ({"scopes": {"bookings:read": " "}}, "says what the person lets it do"),
        ({"brand": "Air\nLines"}, "one line"),
        ({"keys": {}}, "Extra inputs"),
    ],
)
def test_what_a_business_refuses(change, why):
    with pytest.raises(ValidationError, match=why):
        AppSpec.model_validate({**BASE, "pact": {"business": {**BUSINESS, **change}}})


def test_a_business_switched_off_may_keep_its_list_empty():
    spec = AppSpec.model_validate({**BASE, "pact": {"business": {"scopes": {"bookings:read": "See"}}}})
    assert not spec.pact.business.enabled and spec.pact.business.registered_agents == []
