# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The Appspec's `pact` block: businesses asked over PACT 1.0 (PI-01)."""

import pytest
from pydantic import ValidationError

from agentspecs.apps import APP_CATALOGUE, AppSpec, PairRole

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


# --- answering as a business (PR-13, PI-32; decided 2026-10-13) -------------

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


# --- a pair of examples (PR-13, E-02; decided 2026-10-13) ------------------


def test_one_of_a_pair_speaks_pact_as_the_side_it_says():
    business = {**BASE, "pact": {"business": {"scopes": {"profile:read": "See who you are"}}}}
    spec = AppSpec.model_validate({**business, "pair": {"id": "desk", "role": "business"}})
    assert spec.pair is not None and spec.pair.role is PairRole.BUSINESS
    assert AppSpec.model_validate({**BASE, "pair": {"id": "desk", "role": "personal_agent"}}).pair.id == "desk"
    assert AppSpec.model_validate(BASE).pair is None


@pytest.mark.parametrize(
    "spec,why",
    [
        ({**BASE, "protocols": [], "pair": {"id": "desk", "role": "personal_agent"}}, "speaks PACT"),
        ({**BASE, "pair": {"id": "desk", "role": "business"}}, "pact.business.scopes"),
        (
            {**BASE, "pact": {"business": BUSINESS}, "pair": {"id": "desk", "role": "personal_agent"}},
            "does not answer as a business",
        ),
        ({**BASE, "pair": {"id": "Desk Pair", "role": "personal_agent"}}, "pair's id"),
        ({**BASE, "pair": {"id": "desk", "role": "company"}}, "role"),
    ],
)
def test_what_a_pair_refuses(spec, why):
    with pytest.raises(ValidationError, match=why):
        AppSpec.model_validate(spec)


def test_each_pair_of_the_catalogue_is_a_business_and_the_personal_agent_that_asks_it():
    """Decided 2026-10-13: the Studio registers the personal agent's copy with the business's
    copy, so the business starts off and lists nobody, and the personal agent names no business."""
    pairs: dict[str, dict[PairRole, str]] = {}
    for identity, found in APP_CATALOGUE.items():
        if found.pair is not None:
            side = pairs.setdefault(found.pair.id, {})
            assert found.pair.role not in side, identity
            side[found.pair.role] = identity
    assert pairs == {"guest-desk": {PairRole.BUSINESS: "guest-desk", PairRole.PERSONAL_AGENT: "errand-runner"}}
    business = APP_CATALOGUE["guest-desk"].pact.business
    assert not business.enabled and business.registered_agents == [] and business.scopes
    assert APP_CATALOGUE["errand-runner"].pact.connections == []
