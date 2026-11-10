# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Policy specifications (SH-50).

A *policy* is the Shield's document: the rules that decide an agent's actions
by class, kind, path and command, the stateful limits with their soft and hard
thresholds (tool calls, terminals, bytes written, the model budget and the
spend limit), the hosts a fetch may reach, the MCP servers lent, and the
harnesses admitted with their credentials rule. One schema decides it
everywhere — the standalone proxy's ``agent-shield.yaml``, IAM's stored
documents per scope, the Appspec's Rules read into one — and that schema is
the ``agent-shield`` package's, carried here **verbatim** as
``policies/shield-policy.schema.json`` (:data:`SHIELD_SCHEMA_PATH`), never
forked: a test holds the copy to the package's own when it is installed.

The catalogue under ``policies/`` holds one YAML per document the platform
ships or shows: ``default`` (the session document, the one every
Shield decides with under the organization's and the application's) and
``organization-baseline`` (an example of what an administrator writes in
IAM). Each entry wraps the document as ``policy`` under the catalogue's
usual ``id``, ``version``, ``name``, ``description``, ``enabled`` and
``tags``; the wrapper's JSON Schema is ``policies/policy.schema.json``, whose
``policy`` property points at the Shield's schema.

A document may carry ``dogwood``: a Dogwood policy set (Cedar, and ``when
temporal`` conditions over the session's events — AgentCore Policy's
language) the Shield decides every classed action with. It is validated as
it is read: the temporal clauses by agent-shield's own parser, carried here
verbatim as ``policies/dogwood.py`` (:data:`DOGWOOD_PARSER_PATH`), AgentCore's
quotas (20 temporal policies, 3 temporal operators in one, a 24-hour window
at most), and the Cedar by ``cedarpy`` when it is installed — when it is not,
the spec's :attr:`PolicySpec.dogwood_notes` says the Cedar was not checked.

``python -m agentspecs.policies`` writes both schemas beside the specs and the
reference page of the documentation.
"""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from . import dogwood

_ROOT = Path(__file__).resolve().parent.parent

#: The policy specs.
POLICIES_DIR = _ROOT / "policies"

#: The Shield's own schema, verbatim (``agent_shield.policy.policy_json_schema()``).
SHIELD_SCHEMA_PATH = POLICIES_DIR / "shield-policy.schema.json"
#: The agent-shield release the carried schema was copied from: the test holding the copy
#: verbatim compares against an installed agent-shield at least this new, and skips an
#: older one (the two packages release in turn, each pinning the other's last).
SHIELD_SCHEMA_SOURCE_VERSION = "0.2.19"

#: agent-shield's Dogwood parser (``agent_shield.policy.dogwood``), verbatim.
DOGWOOD_PARSER_PATH = POLICIES_DIR / "dogwood.py"

#: The catalogue entry's schema, beside the specs.
SCHEMA_PATH = POLICIES_DIR / "policy.schema.json"

#: The Shield's firewall rules, an agent's ``policy.shield``, verbatim
#: (``agent_shield.firewall.firewall_json_schema()``).
SHIELD_FIREWALL_SCHEMA_PATH = POLICIES_DIR / "shield-firewall.schema.json"
#: The agent-shield release the carried firewall schema was copied from.
SHIELD_FIREWALL_SCHEMA_SOURCE_VERSION = "0.2.14"
#: The keys an agent's ``policy`` takes.
AGENT_POLICY_KEYS = ("shield",)
#: The ranges an egress entry may not name: the platform's own, the base layer's
#: (``agent_shield.firewall.model.NON_PUBLIC``).
NON_PUBLIC = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
    "224.0.0.0/4",
    "240.0.0.0/4",
)

#: Where the reference page is kept in the documentation site, when the checkout has one.
REFERENCE_PATH = _ROOT.parent / "docs" / "docs" / "policies" / "index.md"

_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")

#: The Shield's scopes, strictest first.
SCOPES = ("organization", "team", "session")


class PolicyError(ValueError):
    """A policy spec that cannot be loaded, said in a sentence."""


def shield_schema() -> dict[str, Any]:
    """The Shield's JSON Schema, as carried here."""
    return json.loads(SHIELD_SCHEMA_PATH.read_text(encoding="utf-8"))


_SHIELD_VALIDATOR = jsonschema.Draft202012Validator(shield_schema())


def document_problems(document: Any) -> list[str]:
    """Why ``document`` is not a Shield policy, in sentences; empty when it is one."""
    if not isinstance(document, dict):
        return [f"a policy document is a mapping with a scope, not {type(document).__name__}"]
    problems: list[str] = []
    for error in sorted(
        _SHIELD_VALIDATOR.iter_errors(document), key=lambda e: list(e.absolute_path)
    ):
        where = ".".join(str(part) for part in error.absolute_path) or "the document"
        problems.append(f"{where}: {error.message}")
    section = document.get("dogwood")
    if not problems and isinstance(section, dict):
        problems.extend(f"dogwood: {said}" for said in dogwood_problems(section)[0])
    return problems


def dogwood_problems(section: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Why a document's ``dogwood`` set cannot hold, and what could not be checked.

    The temporal clauses are parsed and AgentCore's quotas held by
    agent-shield's parser; the Cedar is parsed by ``cedarpy`` when it is
    installed, and the notes say so when it is not.
    """
    text = section.get("policies")
    if not isinstance(text, str):
        return ["'policies' is the policy set's text"], []
    return dogwood.validate(text)


def shield_firewall_schema() -> dict[str, Any]:
    """The Shield's firewall rules' JSON Schema, as carried here."""
    return json.loads(SHIELD_FIREWALL_SCHEMA_PATH.read_text(encoding="utf-8"))


_FIREWALL_VALIDATOR = jsonschema.Draft202012Validator(shield_firewall_schema())


def _entry_problem(entry: str, direction: str) -> str | None:
    """Why one egress or ingress entry cannot hold, beyond the schema's pattern; None when it can."""
    if entry in ("*", "platform"):
        if entry == "platform" and direction == "egress":
            return "'platform' is an ingress source; the platform's own egress is the base layer's"
        return None
    target, _, port = entry.partition(":")
    if port and not 1 <= int(port) <= 65535:
        return f"{entry!r}: port {port} is not between 1 and 65535"
    if re.match(r"^[0-9./]+$", target):
        try:
            network = ipaddress.IPv4Network(target, strict=True)
        except ValueError as error:
            return f"{entry!r} is not an IPv4 address or CIDR: {error}"
        if direction == "egress" and any(
            network.overlaps(ipaddress.IPv4Network(item)) for item in NON_PUBLIC
        ):
            return (
                f"{entry!r} is a private or reserved address: the platform's own addresses are the "
                "base layer's, and an agent cannot ask for them"
            )
        return None
    if direction == "ingress":
        return f"{entry!r}: an ingress source is 'platform', '*', an address or a CIDR, not a host name"
    if "." not in target:
        return f"{entry!r} is not an exact, fully qualified host name"
    return None


def agent_policy_problems(policy: Any) -> list[str]:
    """Why an agent's ``policy`` cannot hold, in sentences; empty when it can.

    An agent's ``policy`` is its own ask of the Shield, beside the catalogue's
    documents (which decide at a scope): today one section, ``shield``, the
    firewall's rules in agent-shield's schema (carried verbatim as
    ``policies/shield-firewall.schema.json``), held to what the firewall takes —
    ``*`` alone, no private or reserved address in egress, no wildcard host, each
    entry once.
    """
    if not isinstance(policy, dict):
        return [f"an agent's policy is a mapping, not {type(policy).__name__}"]
    problems = [
        f"policy.{key}: an agent's policy takes {', '.join(AGENT_POLICY_KEYS)} only"
        for key in policy
        if key not in AGENT_POLICY_KEYS
    ]
    shield = policy.get("shield")
    if shield is None:
        return problems
    for error in sorted(_FIREWALL_VALIDATOR.iter_errors(shield), key=lambda e: list(e.absolute_path)):
        where = ".".join(str(part) for part in error.absolute_path)
        if "pattern" == error.validator and isinstance(error.instance, str) and "*" in error.instance:
            problems.append(
                f"policy.shield.{where}: {error.instance!r}: a firewall sees addresses, not names, so a wildcard "
                "host cannot hold; name each host"
            )
            continue
        problems.append(f"policy.shield{'.' + where if where else ''}: {error.message}")
    if problems or not isinstance(shield, dict):
        return problems
    for direction in ("egress", "ingress"):
        entries = shield.get(direction) or []
        if "*" in entries and len(entries) > 1:
            problems.append(f"policy.shield.{direction}: '*' stands alone")
        if len(set(entries)) != len(entries):
            problems.append(f"policy.shield.{direction}: an entry is named twice")
        for entry in entries:
            said = _entry_problem(entry, direction)
            if said:
                problems.append(f"policy.shield.{direction}: {said}")
    return problems


class PolicySpec(BaseModel):
    """One catalogue entry: a Shield policy document under the catalogue's fields."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="The entry's id, the file's name.")
    version: str = Field(description="The entry's version (semver).")
    name: str
    description: str
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(
        description="The Shield's policy document (shield-policy.schema.json)."
    )

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        if not _ID.match(value):
            raise ValueError(f"{value!r} is not a policy id (lowercase letters, digits and dashes)")
        return value

    @field_validator("version")
    @classmethod
    def _version(cls, value: str) -> str:
        if not _VERSION.match(value):
            raise ValueError(f"{value!r} is not a version (major.minor.patch)")
        return value

    @field_validator("policy")
    @classmethod
    def _policy(cls, value: dict[str, Any]) -> dict[str, Any]:
        problems = document_problems(value)
        if problems:
            raise ValueError("; ".join(problems))
        return value

    @property
    def scope(self) -> str:
        return str(self.policy.get("scope"))

    @property
    def dogwood_notes(self) -> list[str]:
        """What could not be checked of the ``dogwood`` set (the Cedar, without cedarpy)."""
        section = self.policy.get("dogwood")
        return dogwood_problems(section)[1] if isinstance(section, dict) else []


def load_policies(directory: Path = POLICIES_DIR) -> dict[str, PolicySpec]:
    """Every policy spec of a directory, by id; a file not named for its id is refused."""
    found: dict[str, PolicySpec] = {}
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise PolicyError(f"{path.name}: a policy spec is a mapping")
        try:
            spec = PolicySpec.model_validate(data)
        except ValidationError as error:
            first = error.errors()[0]
            where = ".".join(str(part) for part in first["loc"]) or "the spec"
            said = str(first["msg"]).removeprefix("Value error, ")
            raise PolicyError(f"{path.name}: {where}: {said}") from None
        if spec.id != path.stem:
            raise PolicyError(
                f"{path.name}: the file is named for {path.stem!r}, the spec says {spec.id!r}"
            )
        found[spec.id] = spec
    return found


POLICY_CATALOGUE: dict[str, PolicySpec] = load_policies()


def get_policy(policy_id: str) -> PolicySpec:
    try:
        return POLICY_CATALOGUE[policy_id]
    except KeyError:
        raise PolicyError(
            f"There is no policy named {policy_id!r}: one of {', '.join(sorted(POLICY_CATALOGUE))}"
        ) from None


def json_schema() -> dict[str, Any]:
    """The catalogue entry's JSON Schema, its ``policy`` the Shield's own."""
    schema = PolicySpec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://agentspecs.datalayer.tech/policies/policy.schema.json"
    schema["title"] = "Policy spec"
    schema["properties"]["policy"] = {
        "$ref": "shield-policy.schema.json",
        "description": "The Shield's policy document (agent_shield.policy).",
    }
    return schema


def schema_text() -> str:
    return json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"


def _cell(text: object) -> str:
    words = " ".join(str(text if text is not None else "").split())
    return words.replace("|", "\\|").replace("<", "&lt;").replace("{", "\\{").replace("}", "\\}")


def _threshold(value: Any) -> str:
    if not isinstance(value, dict):
        return "—"
    return f"{value.get('soft')} then {value.get('hard')}"


def _dogwood_cell(section: Any) -> str:
    if not isinstance(section, dict):
        return "—"
    try:
        parsed = dogwood.parse_set(str(section.get("policies", "")))
    except dogwood.DogwoodRefused:
        return "refused"
    temporal = len(parsed.temporal_policies)
    return f"{len(parsed.policies)} policies, {temporal} temporal ({section.get('mode', 'enforce')})"


def reference_text() -> str:
    """The reference page: every policy with what it says."""
    lines = [
        "<!-- Generated by `python -m agentspecs.policies` from policies/*.yaml. Do not edit. -->",
        "",
        "# Policies",
        "",
        "The Shield's policy document: one schema, the",
        "`agent-shield` package's, carried here verbatim as `policies/shield-policy.schema.json`.",
        "One document per scope — the organization's in IAM, the application's Rules read",
        "into the team's, the session's — the strictest scope deciding first, the first",
        "decision winning, a lower scope only tightening. The catalogue holds the documents",
        "the platform ships or shows, each wrapped under the catalogue's fields.",
        "",
        "| Policy | Id | Scope | Enabled | Rules | Tool calls | Model tokens | Spend (credits) "
        "| Harnesses | Dogwood |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for spec in sorted(POLICY_CATALOGUE.values(), key=lambda s: s.id):
        limits = spec.policy.get("limits") or {}
        harnesses = spec.policy.get("harnesses") or {}
        admitted = ", ".join(harnesses.get("admit") or []) or "every registered one"
        lines.append(
            f"| {_cell(spec.name)} | `{spec.id}` | {spec.scope} | {'yes' if spec.enabled else 'no'} | "
            f"{len(spec.policy.get('rules') or [])} | "
            f"{_threshold(limits.get('tool_calls'))} | {_threshold(limits.get('model_tokens'))} | "
            f"{_threshold(limits.get('spend'))} | {_cell(admitted)} ({harnesses.get('credentials', 'account')}) | "
            f"{_dogwood_cell(spec.policy.get('dogwood'))} |"
        )
    lines += ["", "## Each policy", ""]
    for spec in sorted(POLICY_CATALOGUE.values(), key=lambda s: s.id):
        lines += [f"### {spec.name} (`{spec.id}`)", "", spec.description, ""]
        for rule in spec.policy.get("rules") or []:
            what = ", ".join(rule.get("classes") or rule.get("kinds") or ["every class"])
            where = (
                f" {rule['where']} the workspace"
                if rule.get("where") in ("inside", "outside")
                else ""
            )
            lines.append(f"- **{rule['name']}**: {rule['decision']} — {what}{where}")
        section = spec.policy.get("dogwood")
        if isinstance(section, dict):
            lines += [
                "",
                f"Its Dogwood set, in {section.get('mode', 'enforce')} mode:",
                "",
                "```cedar",
                str(section.get("policies", "")).rstrip(),
                "```",
            ]
        lines.append("")
    lines += [
        "## An organization's firewall ceiling",
        "",
        "An organization's document may carry `firewall: {egress, ingress}`, the most any agent of",
        "the organization may be granted by its own `policy.shield` (agent-shield 0.2.16 and later).",
        "When a runtime's rule is applied, an agent's entry holds only if the ceiling allows it: `*`",
        "in the ceiling allows anything public; an exact host must match exactly; an address or CIDR",
        "must be covered by a ceiling CIDR; a port must match. An agent's `*` becomes the ceiling's",
        "own entries, and `platform` always stays in ingress. A direction the ceiling leaves out",
        "bounds nothing. Only an organization document carries `firewall`.",
        "",
        "## Dogwood: temporal policies",
        "",
        "A document may carry `dogwood: {policies, mode}`: a Dogwood policy set, the language",
        "AgentCore Policy writes its temporal policies in (agent-shield 0.2.18 and later). It is",
        "Cedar — `permit` and `forbid` over a principal (`Datalayer::User`, with `org_uid`, `app_uid`",
        'and `agent_uid`), an action (`Datalayer::Action::"<server>___<tool>"`, the Shield\'s own',
        "`shield___<kind>`) and a resource (`Datalayer::Runtime`), with the tool's arguments under",
        "`context.input` — plus `when temporal { … }` conditions over the session's earlier events:",
        "`formerly within`, `since within`, `count` and `sum` (a distinct count leaves the timepoint",
        "out of its domain). An event is a `request`, a `response` (a permitted call that completed)",
        "or an `error` (a refused or failed one); the request being decided counts. Deny by default,",
        "a `forbid` overriding any `permit`. The Shield decides every classed action with it: a deny",
        "wins over any rule; in `log_only` mode it is recorded and the action goes on.",
        "",
        "A set is validated as it is read: the temporal clauses by agent-shield's parser, carried",
        "verbatim as `policies/dogwood.py`; AgentCore's quotas — at most 20 temporal policies, 3",
        "temporal operators in one, a 24-hour window; and the Cedar by `cedarpy` when it is installed",
        "(without it, the Cedar is not checked, and the spec's `dogwood_notes` says so). The catalogue's",
        "Dogwood examples are off (`enabled: false`).",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    SCHEMA_PATH.write_text(schema_text())
    if REFERENCE_PATH.parent.parent.is_dir():
        REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        REFERENCE_PATH.write_text(reference_text())


if __name__ == "__main__":
    main()


__all__ = [
    "DOGWOOD_PARSER_PATH",
    "POLICIES_DIR",
    "POLICY_CATALOGUE",
    "REFERENCE_PATH",
    "SCHEMA_PATH",
    "AGENT_POLICY_KEYS",
    "SCOPES",
    "SHIELD_FIREWALL_SCHEMA_PATH",
    "SHIELD_SCHEMA_PATH",
    "PolicyError",
    "PolicySpec",
    "agent_policy_problems",
    "document_problems",
    "dogwood_problems",
    "get_policy",
    "json_schema",
    "load_policies",
    "main",
    "reference_text",
    "schema_text",
    "shield_firewall_schema",
    "shield_schema",
]
