# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The Appspec's `pact` block: businesses asked over PACT 1.0 (AGENT_PROTOCOLS PI-01)."""

import pytest
from pydantic import ValidationError

from agentspecs.apps import AppSpec

BASE = {"id": "support", "name": "Support", "kind": "chat", "agent": "a"}
AIR = {"id": "air", "brand": "air.example", "audience": "https://provider.example/a2a", "scopes": ["bookings:read"]}


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
