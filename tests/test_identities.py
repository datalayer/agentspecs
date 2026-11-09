# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Identities: the catalogue loads, each provider reads, and every refusal is a sentence."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from agentspecs.identities import (
    IDENTITY_CATALOGUE,
    IdentityError,
    IdentityProvider,
    IdentitySpec,
    IdentitySubject,
    check_identity,
    get_identity,
    list_identities,
)

DISCOVERY = "https://prod1.datalayer.run/api/iam/v1/oauth/.well-known/openid-configuration"
AGENTS = Path(__file__).resolve().parents[1] / "agentspecs" / "agents"


def _agentcore(**changes):
    base = {
        "id": "an-agentcore-agent",
        "name": "An AgentCore agent",
        "subject": "agent",
        "provider": "aws-agentcore",
        "inbound": {"kind": "jwt", "discovery_url": DISCOVERY, "algorithms": ["RS256"], "clients": ["datalayer-platform"]},
        "workload": {"token": "agentcore-runtime"},
        "credentials": {"vault": "agentcore"},
    }
    base.update(changes)
    return base


class TestCatalogue:
    def test_twelve_identities_of_the_four_providers(self):
        assert sorted(IDENTITY_CATALOGUE) == [
            "aws-agentcore-gateway",
            "aws-agentcore-runtime",
            "aws-agentcore-vault",
            "datalayer-acting-agent",
            "datalayer-person",
            "datalayer-service-agent",
            "datalayer-visitor",
            "organization-oidc",
            "pap-company",
            "pap-person",
            "pap-personal-agent",
            "web-bot-auth-agent",
        ]
        assert {identity.provider for identity in IDENTITY_CATALOGUE.values()} == set(IdentityProvider)

    def test_found_by_id_and_by_version(self):
        assert get_identity("pap-company").name == "PAP company"
        assert get_identity("pap-company:0.0.1").id == "pap-company"
        assert get_identity("nobody") is None

    def test_listed_by_provider_and_subject(self):
        agentcore = list_identities(provider=IdentityProvider.AWS_AGENTCORE)
        assert {identity.id for identity in agentcore} == {
            "aws-agentcore-gateway",
            "aws-agentcore-runtime",
            "aws-agentcore-vault",
        }
        assert [identity.id for identity in list_identities(subject=IdentitySubject.VISITOR)] == ["datalayer-visitor"]

    def test_agentcore_trusts_datalayer_iam_asymmetrically(self):
        runtime = get_identity("aws-agentcore-runtime")
        assert runtime.inbound.discovery_url == DISCOVERY
        assert runtime.inbound.algorithms == ["RS256"]
        assert runtime.workload.token.value == "agentcore-runtime"
        assert runtime.credentials.vault.value == "agentcore"
        assert runtime.consent.binding and runtime.consent.hosted_by.value == "datalayer"

    def test_pap_binds_pairwise_dpop_and_a_client_per_application(self):
        agent = get_identity("pap-personal-agent")
        assert agent.pap.pairwise and agent.pap.dpop and agent.pap.client_id_per_application
        assert agent.custody.keys.value == "vault-transit" and agent.custody.algorithm == "ES256"
        assert get_identity("pap-person").pap.client_id_per_application is False

    def test_every_agent_naming_an_identity_names_one_of_the_catalogue(self):
        named = {}
        for path in AGENTS.glob("*.yaml"):
            spec = yaml.safe_load(path.read_text()) or {}
            if spec.get("identity"):
                named[spec["id"]] = spec["identity"]
        assert named, "some agent of the catalogue says who it acts as"
        for agent, identity in named.items():
            assert get_identity(identity) is not None, f"{agent} acts as {identity}, not in the catalogue"


class TestRefusals:
    def test_a_slug_for_an_id(self):
        with pytest.raises(ValidationError, match="slug"):
            IdentitySpec(**_agentcore(id="Not A Slug"))

    def test_a_pap_identity_says_its_roles_and_speaks_pap(self):
        with pytest.raises(ValidationError, match="says its `pap` roles"):
            IdentitySpec(id="p", name="P", subject="application", provider="pap", protocols=["pap"])
        with pytest.raises(ValidationError, match="speaks the `pap` protocol"):
            IdentitySpec(id="p", name="P", subject="application", provider="pap", pap={"roles": ["company"]})

    def test_a_pap_block_belongs_to_a_pap_identity(self):
        with pytest.raises(ValidationError, match="no `pap` block"):
            IdentitySpec(id="p", name="P", subject="person", provider="datalayer", pap={"roles": ["company"]})

    def test_agentcore_takes_a_discovery_url_of_its_form(self):
        with pytest.raises(ValidationError, match="openid-configuration"):
            IdentitySpec(**_agentcore(inbound={"kind": "jwt", "discovery_url": "https://x/jwks", "clients": ["c"]}))

    def test_agentcore_checks_at_least_one_claim(self):
        with pytest.raises(ValidationError, match="at least one of"):
            IdentitySpec(**_agentcore(inbound={"kind": "jwt", "discovery_url": DISCOVERY}))

    def test_no_shared_secret_outside_datalayer(self):
        with pytest.raises(ValidationError, match="shared-secret"):
            IdentitySpec(
                **_agentcore(inbound={"kind": "jwt", "discovery_url": DISCOVERY, "clients": ["c"], "algorithms": ["HS256"]})
            )
        with pytest.raises(ValidationError, match="shared-secret"):
            IdentitySpec(**_agentcore(custody={"keys": "shared-secret"}))

    def test_never_a_workload_token_by_user_id(self):
        with pytest.raises(ValidationError, match="never by user id"):
            IdentitySpec(**_agentcore(workload={"token": "agentcore-user-id"}))

    def test_the_agentcore_vault_answers_an_agentcore_workload_token(self):
        with pytest.raises(ValidationError, match="AgentCore workload token"):
            IdentitySpec(**_agentcore(workload={"token": "acting"}))

    def test_nothing_kept_for_a_visitor(self):
        with pytest.raises(ValidationError, match="nothing is kept for a visitor"):
            IdentitySpec(id="v", name="V", subject="visitor", provider="datalayer", credentials={"vault": "datalayer"})

    def test_an_oauth_provider_says_its_flow_and_api_keys_have_none(self):
        with pytest.raises(ValidationError, match="says its flow"):
            IdentitySpec(**_agentcore(credentials={"vault": "agentcore", "providers": [{"name": "github"}]}))
        with pytest.raises(ValidationError, match="no flow and no scopes"):
            IdentitySpec(
                **_agentcore(
                    credentials={"vault": "agentcore", "providers": [{"name": "k", "kind": "api-key", "flow": "m2m"}]}
                )
            )

    def test_providers_are_kept_somewhere_once_each(self):
        oauth = {"name": "github", "flow": "user-federation"}
        with pytest.raises(ValidationError, match="say the `vault`"):
            IdentitySpec(id="x", name="X", subject="person", provider="datalayer", credentials={"providers": [oauth]})
        with pytest.raises(ValidationError, match="named once"):
            IdentitySpec(**_agentcore(credentials={"vault": "agentcore", "providers": [oauth, oauth]}))

    def test_a_bound_consent_says_who_hosts_it(self):
        with pytest.raises(ValidationError, match="who hosts it"):
            IdentitySpec(**_agentcore(consent={"by": "person", "binding": True}))

    def test_a_protocol_of_the_catalogue(self):
        with pytest.raises(IdentityError, match="not a protocol of the catalogue"):
            check_identity(IdentitySpec(**_agentcore(protocols=["telepathy"])))

    def test_unknown_fields_are_refused(self):
        with pytest.raises(ValidationError):
            IdentitySpec(**_agentcore(secret="no"))
