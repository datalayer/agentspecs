# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Identity specifications.

An *Identity* says who is acting when an agent acts, and how each party
proves it. Three identities meet at every tool call: the **person** an agent
works for, the **agent** itself (a workload), and the **third party** it
reaches. An Identity spec describes one of them as a provider holds it:

- `subject`: whose identity it is — a person, an agent, an application, an
  organization, a visitor or a service;
- `provider`: who issues and verifies it — Datalayer IAM, the Personal Agent
  Protocol (PAP), Amazon Bedrock AgentCore Identity, or an organization's own
  OpenID Connect provider;
- `inbound`: how a caller proves it on the way in (a session, a JWT checked
  against a discovery URL, SigV4, an API key, a DPoP-bound token, an HTTP
  message signature);
- `workload`: the token the agent itself holds while it acts;
- `credentials`: where third-party credentials are kept (Datalayer's vault,
  AgentCore's token vault, or nowhere) and the credential providers it may
  use, OAuth 2.0 (user federation or machine to machine) or API keys;
- `custody`: who keeps the signing keys, and the algorithm;
- `consent`: who consents, and who hosts the consent;
- `pap`: for a PAP identity, its roles and what the protocol binds (a client
  id per application, pairwise user ids, DPoP).

An Identity refuses, as it is read: a PAP identity without its `pap` block
or without the `pap` protocol, and a `pap` block on another provider; an
AgentCore JWT authorizer without a discovery URL of the form AgentCore takes,
or with none of audiences, clients, scopes and claims; a shared-secret
algorithm (HS256) for anything verified outside Datalayer; a workload token
by user id on AgentCore (`GetWorkloadAccessTokenForUserId` — the JWT variant
is used, always); a vault kept for a visitor; AgentCore's vault without an
AgentCore workload token; a protocol the catalogue does not hold.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..guards import id_of, load_raw


class IdentityError(ValueError):
    """An Identity that cannot be used — named plainly."""


class IdentitySubject(str, Enum):
    """Whose identity it is."""

    PERSON = "person"
    AGENT = "agent"
    APPLICATION = "application"
    ORGANIZATION = "organization"
    VISITOR = "visitor"
    SERVICE = "service"


class IdentityProvider(str, Enum):
    """Who issues and verifies it."""

    #: Datalayer IAM.
    DATALAYER = "datalayer"
    #: The Personal Agent Protocol.
    PAP = "pap"
    #: Amazon Bedrock AgentCore Identity.
    AWS_AGENTCORE = "aws-agentcore"
    #: An organization's own OpenID Connect provider.
    OIDC = "oidc"


class InboundKind(str, Enum):
    """How a caller proves the identity on the way in."""

    NONE = "none"
    SESSION = "session"
    JWT = "jwt"
    SIGV4 = "sigv4"
    API_KEY = "api-key"
    DPOP = "dpop"
    HTTP_SIGNATURE = "http-signature"


class WorkloadToken(str, Enum):
    """The token the agent itself holds while it acts."""

    NONE = "none"
    #: Datalayer's acting token: the person as `sub`, the app and agent beside it.
    ACTING = "acting"
    #: OAuth 2.0 client credentials of a service principal.
    CLIENT_CREDENTIALS = "client-credentials"
    #: Injected by AgentCore Runtime with the invocation.
    AGENTCORE_RUNTIME = "agentcore-runtime"
    #: `GetWorkloadAccessTokenForJWT`, outside AgentCore Runtime.
    AGENTCORE_JWT = "agentcore-jwt"


class Vault(str, Enum):
    """Where third-party credentials are kept."""

    NONE = "none"
    DATALAYER = "datalayer"
    AGENTCORE = "agentcore"


class CredentialKind(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api-key"


class CredentialFlow(str, Enum):
    NONE = ""
    #: Three-legged: the person consents (`USER_FEDERATION`).
    USER_FEDERATION = "user-federation"
    #: Two-legged, machine to machine (`M2M`).
    M2M = "m2m"


class KeyCustody(str, Enum):
    NONE = "none"
    SHARED_SECRET = "shared-secret"
    VAULT_TRANSIT = "vault-transit"
    AWS_MANAGED = "aws-managed"
    PROVIDER = "provider"


class ConsentBy(str, Enum):
    NONE = "none"
    PERSON = "person"
    ORGANIZATION = "organization"


class ConsentHost(str, Enum):
    NONE = "none"
    DATALAYER = "datalayer"
    PROVIDER = "provider"


class PapRole(str, Enum):
    PERSONAL_AGENT = "personal-agent"
    COMPANY = "company"


_ID = re.compile(r"^[a-z][a-z0-9-]*$")
#: The discovery URL AgentCore's JWT authorizer takes (its own pattern).
AGENTCORE_DISCOVERY_URL = re.compile(
    r"^[^\s?#]+/\.well-known/(openid-configuration|oauth-authorization-server)(/[^\s?#]+)?$"
)
#: Algorithms only the issuer can verify.
SHARED_SECRET_ALGORITHMS = {"HS256", "HS384", "HS512"}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InboundSpec(_Strict):
    """How a caller proves the identity on the way in."""

    kind: InboundKind = Field(default=InboundKind.NONE)
    issuer: str = Field(default="", description="Who issues what is presented")
    discovery_url: str = Field(default="", description="OIDC or RFC 8414 discovery URL")
    algorithms: List[str] = Field(default_factory=list, description="Signing algorithms accepted")
    audiences: List[str] = Field(default_factory=list, description="Accepted `aud` values")
    clients: List[str] = Field(default_factory=list, description="Accepted `client_id` values")
    scopes: List[str] = Field(default_factory=list, description="At least one of these scopes")
    claims: Dict[str, str] = Field(default_factory=dict, description="Required custom claims, by name")
    lifetime_seconds: int = Field(default=0, ge=0, description="How long what is presented lives; 0 unsaid")


class WorkloadSpec(_Strict):
    """The token the agent holds while it acts."""

    token: WorkloadToken = Field(default=WorkloadToken.NONE)
    lifetime_seconds: int = Field(default=0, ge=0)

    @field_validator("token", mode="before")
    @classmethod
    def _never_by_user_id(cls, token: Any) -> Any:
        if token in ("agentcore-user-id", "for-user-id"):
            raise ValueError(
                "a workload token is obtained with the person's verified JWT "
                "(`agentcore-jwt`), never by user id (`GetWorkloadAccessTokenForUserId`)"
            )
        return token


class CredentialProviderSpec(_Strict):
    """A third party the identity may obtain credentials for."""

    name: str = Field(..., description="The provider's name, as agentspecs and the vault call it")
    kind: CredentialKind = Field(default=CredentialKind.OAUTH2)
    flow: CredentialFlow = Field(default=CredentialFlow.NONE)
    scopes: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _flow_of_kind(self) -> "CredentialProviderSpec":
        if self.kind is CredentialKind.OAUTH2 and self.flow is CredentialFlow.NONE:
            raise ValueError(f"OAuth 2.0 provider {self.name!r} says its flow: `user-federation` or `m2m`")
        if self.kind is CredentialKind.API_KEY and (self.flow is not CredentialFlow.NONE or self.scopes):
            raise ValueError(f"API-key provider {self.name!r} has no flow and no scopes")
        return self


class CredentialsSpec(_Strict):
    """Where third-party credentials are kept, and for whom."""

    vault: Vault = Field(default=Vault.NONE)
    providers: List[CredentialProviderSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _providers_need_a_vault(self) -> "CredentialsSpec":
        if self.providers and self.vault is Vault.NONE:
            raise ValueError("credential providers are kept somewhere: say the `vault`")
        names = [provider.name for provider in self.providers]
        if len(names) != len(set(names)):
            raise ValueError("each credential provider is named once")
        return self


class CustodySpec(_Strict):
    """Who keeps the signing keys."""

    keys: KeyCustody = Field(default=KeyCustody.NONE)
    algorithm: str = Field(default="")


class ConsentSpec(_Strict):
    """Who consents, and who hosts it."""

    by: ConsentBy = Field(default=ConsentBy.NONE)
    hosted_by: ConsentHost = Field(default=ConsentHost.NONE)
    #: The consent is bound to the session that asked (`CompleteResourceTokenAuth`, PAP's sign-in).
    binding: bool = Field(default=False)


class PapSpec(_Strict):
    """What the Personal Agent Protocol binds for this identity."""

    roles: List[PapRole] = Field(..., min_length=1)
    #: One PAP `client_id` per application, stable across its versions and deployments.
    client_id_per_application: bool = Field(default=True)
    #: One random user id per (application, person, company issuer), unlinkable.
    pairwise: bool = Field(default=True)
    #: Tokens bound to a proof-of-possession key (DPoP).
    dpop: bool = Field(default=True)


class IdentitySpec(_Strict):
    """Specification for an Identity: whose, issued by whom, proven how, holding what."""

    id: str = Field(..., description="Unique Identity identifier")
    version: str = Field(default="0.0.1", description="Identity spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What it is, in a sentence or two")
    subject: IdentitySubject = Field(..., description="Whose identity it is")
    provider: IdentityProvider = Field(..., description="Who issues and verifies it")
    protocols: List[str] = Field(default_factory=list, description="Protocols of the catalogue it speaks, by id")
    inbound: InboundSpec = Field(default_factory=InboundSpec)
    workload: WorkloadSpec = Field(default_factory=WorkloadSpec)
    credentials: CredentialsSpec = Field(default_factory=CredentialsSpec)
    custody: CustodySpec = Field(default_factory=CustodySpec)
    consent: ConsentSpec = Field(default_factory=ConsentSpec)
    pap: Optional[PapSpec] = Field(default=None, description="For a PAP identity: what the protocol binds")
    enabled: bool = Field(default=True)
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="person")
    emoji: str = Field(default="\U0001faaa")

    @field_validator("id")
    @classmethod
    def _a_slug(cls, identity: str) -> str:
        if not _ID.match(identity):
            raise ValueError(f"an Identity's id is a slug, `aws-agentcore-runtime`, not {identity!r}")
        return identity

    @model_validator(mode="after")
    def _coherent(self) -> "IdentitySpec":
        name = self.id
        if self.provider is IdentityProvider.PAP:
            if self.pap is None:
                raise ValueError(f"identity {name!r} is a PAP identity: it says its `pap` roles")
            if "pap" not in self.protocols:
                raise ValueError(f"identity {name!r} is a PAP identity: it speaks the `pap` protocol")
        elif self.pap is not None:
            raise ValueError(f"identity {name!r} is issued by {self.provider.value}, not PAP: it has no `pap` block")
        if self.provider is not IdentityProvider.DATALAYER:
            shared = SHARED_SECRET_ALGORITHMS.intersection(self.inbound.algorithms)
            if shared or self.custody.keys is KeyCustody.SHARED_SECRET:
                raise ValueError(
                    f"identity {name!r} is verified outside Datalayer: no shared-secret algorithm "
                    f"({', '.join(sorted(shared)) or 'shared-secret custody'}); sign asymmetrically"
                )
        if self.provider is IdentityProvider.AWS_AGENTCORE and self.inbound.kind is InboundKind.JWT:
            if not AGENTCORE_DISCOVERY_URL.match(self.inbound.discovery_url):
                raise ValueError(
                    f"identity {name!r}: AgentCore's JWT authorizer takes a discovery URL ending in "
                    f"`/.well-known/openid-configuration`, not {self.inbound.discovery_url!r}"
                )
            if not (self.inbound.audiences or self.inbound.clients or self.inbound.scopes or self.inbound.claims):
                raise ValueError(
                    f"identity {name!r}: AgentCore's JWT authorizer checks at least one of "
                    "audiences, clients, scopes and claims"
                )
        if self.subject is IdentitySubject.VISITOR and self.credentials.vault is not Vault.NONE:
            raise ValueError(f"identity {name!r} is a visitor's: nothing is kept for a visitor, no vault")
        if self.credentials.vault is Vault.AGENTCORE and self.workload.token not in (
            WorkloadToken.AGENTCORE_RUNTIME,
            WorkloadToken.AGENTCORE_JWT,
        ):
            raise ValueError(
                f"identity {name!r} keeps credentials in AgentCore's vault, which answers only an "
                "AgentCore workload token (`agentcore-runtime` or `agentcore-jwt`)"
            )
        if self.consent.binding and self.consent.hosted_by is ConsentHost.NONE:
            raise ValueError(f"identity {name!r} binds a consent: say who hosts it")
        return self


def check_identity(identity: IdentitySpec) -> IdentitySpec:
    """An Identity whose protocols are all in the catalogue; raised otherwise."""
    from ..protocols import get_protocol  # noqa: PLC0415 — the catalogue is loaded on demand

    for protocol in identity.protocols:
        if get_protocol(protocol) is None:
            raise IdentityError(f"identity {identity.id!r} speaks {protocol!r}, which is not a protocol of the catalogue")
    return identity


def load_raw_identities(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Identity YAML of a directory as plain data, by id."""
    return load_raw(directory or Path(__file__).parent)


def load_identities(directory: Optional[Path] = None, check: bool = True) -> Dict[str, IdentitySpec]:
    """Every Identity of a directory, validated; with `check`, its protocols too."""
    identities = {key: IdentitySpec(**data) for key, data in load_raw_identities(directory).items()}
    if check:
        identities = {key: check_identity(identity) for key, identity in identities.items()}
    return identities


#: Every Identity, by id.
IDENTITY_CATALOGUE: Dict[str, IdentitySpec] = load_identities()


def get_identity(identity_id: str) -> Optional[IdentitySpec]:
    """An Identity, by `id` or `id:version`, or None."""
    return IDENTITY_CATALOGUE.get(id_of(identity_id))


def list_identities(
    provider: Optional[IdentityProvider] = None, subject: Optional[IdentitySubject] = None
) -> List[IdentitySpec]:
    """Every Identity, or those of one provider, or of one subject."""
    return [
        identity
        for identity in IDENTITY_CATALOGUE.values()
        if (provider is None or identity.provider is provider) and (subject is None or identity.subject is subject)
    ]


__all__ = [
    "AGENTCORE_DISCOVERY_URL",
    "IDENTITY_CATALOGUE",
    "IdentityError",
    "IdentityProvider",
    "IdentitySpec",
    "IdentitySubject",
    "check_identity",
    "get_identity",
    "list_identities",
    "load_identities",
    "load_raw_identities",
]
