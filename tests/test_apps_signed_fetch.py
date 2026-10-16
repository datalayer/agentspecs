# Copyright (c) 2025-2026 Datalayer, Inc.
# Distributed under the terms of the Modified BSD License.

"""The Appspec's `signed_fetch` block (EX-11, decided 2026-10-13): exact sites,
read with GET only through the gateway, every request signed with the application's key."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentspecs.apps import APP_CATALOGUE, AppSignedFetchSite, AppSpec

BASE = {"id": "reader", "name": "Reader", "kind": "chat", "agent": "a"}
VERIFIER = {"id": "verifier", "site": "verify.example"}


def test_a_site_is_an_id_and_a_domain():
    spec = AppSpec.model_validate(
        {**BASE, "protocols": ["web-bot-auth"], "signed_fetch": {"sites": [VERIFIER]}}
    )
    [site] = spec.signed_fetch.sites
    assert (site.id, site.site) == ("verifier", "verify.example")
    assert AppSpec.model_validate(BASE).signed_fetch.sites == []


@pytest.mark.parametrize(
    "change,why",
    [
        ({"site": "https://verify.example"}, "only the domain"),
        ({"site": "verify.example/page"}, "only the domain"),
        ({"site": "localhost"}, "only the domain"),
        ({"id": "Verifier"}, "not a site id"),
        ({"access": "write"}, "Extra inputs"),
        ({"headers": {"authorization": "x"}}, "Extra inputs"),
    ],
)
def test_a_site_is_refused(change, why):
    with pytest.raises(ValidationError, match=why):
        AppSignedFetchSite.model_validate({**VERIFIER, **change})


@pytest.mark.parametrize(
    "sites,protocols,why",
    [
        ([VERIFIER, {**VERIFIER, "site": "other.example"}], ["web-bot-auth"], "same id"),
        ([VERIFIER, {**VERIFIER, "id": "again"}], ["web-bot-auth"], "same site twice"),
        ([VERIFIER], [], "add 'web-bot-auth' to `protocols`"),
    ],
)
def test_an_application_reading_sites_is_refused(sites, protocols, why):
    with pytest.raises(ValidationError, match=why):
        AppSpec.model_validate({**BASE, "protocols": protocols, "signed_fetch": {"sites": sites}})


def test_the_signed_reader_reads_the_hosted_verifier_only():
    app = APP_CATALOGUE["signed-reader"]
    assert app.protocols == ["web-bot-auth"]
    assert [(site.id, site.site) for site in app.signed_fetch.sites] == [
        ("example-verifier", "verify.examples.datalayer.run")
    ]
    # Reading is a read under its Rules; on since drilled live at the hosted verifier (13 October 2026).
    assert [rule.behaviour.value for rule in app.rules] == ["do_it"]
    assert app.enabled and app.tests.verified.live
