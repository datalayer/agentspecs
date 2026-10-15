# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Policy specifications (SHIELD.md SH-50, §6.7, decision 10).

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
ships or shows: ``default`` (decision 5's session document, the one every
Shield decides with under the organization's and the application's) and
``organization-baseline`` (an example of what an administrator writes in
IAM). Each entry wraps the document as ``policy`` under the catalogue's
usual ``id``, ``version``, ``name``, ``description``, ``enabled`` and
``tags``; the wrapper's JSON Schema is ``policies/policy.schema.json``, whose
``policy`` property points at the Shield's schema.

``python -m agentspecs.policies`` writes both schemas beside the specs and the
reference page of the documentation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

_ROOT = Path(__file__).resolve().parent.parent

#: The policy specs.
POLICIES_DIR = _ROOT / "policies"

#: The Shield's own schema, verbatim (``agent_shield.policy.policy_json_schema()``).
SHIELD_SCHEMA_PATH = POLICIES_DIR / "shield-policy.schema.json"
#: The agent-shield release the carried schema was copied from: the test holding the copy
#: verbatim compares against an installed agent-shield at least this new, and skips an
#: older one (the two packages release in turn, each pinning the other's last).
SHIELD_SCHEMA_SOURCE_VERSION = "0.2.0"

#: The catalogue entry's schema, beside the specs.
SCHEMA_PATH = POLICIES_DIR / "policy.schema.json"

#: Where the reference page is kept in the documentation site, when the checkout has one.
REFERENCE_PATH = _ROOT.parent / "docs" / "docs" / "policies" / "index.md"

_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")

#: The Shield's scopes, strictest first (SHIELD.md §6.3).
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
        "description": "The Shield's policy document (agent_shield.policy, SHIELD.md §6.7).",
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


def reference_text() -> str:
    """The reference page: every policy with what it says."""
    lines = [
        "<!-- Generated by `python -m agentspecs.policies` from policies/*.yaml. Do not edit. -->",
        "",
        "# Policies",
        "",
        "The Shield's policy document (SHIELD.md §6.2, §6.3, §6.7): one schema, the",
        "`agent-shield` package's, carried here verbatim as `policies/shield-policy.schema.json`.",
        "One document per scope — the organization's in IAM, the application's Rules read",
        "into the team's, the session's — the strictest scope deciding first, the first",
        "decision winning, a lower scope only tightening. The catalogue holds the documents",
        "the platform ships or shows, each wrapped under the catalogue's fields.",
        "",
        "| Policy | Id | Scope | Rules | Tool calls | Model tokens | Spend (credits) | Harnesses |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for spec in sorted(POLICY_CATALOGUE.values(), key=lambda s: s.id):
        limits = spec.policy.get("limits") or {}
        harnesses = spec.policy.get("harnesses") or {}
        admitted = ", ".join(harnesses.get("admit") or []) or "every registered one"
        lines.append(
            f"| {_cell(spec.name)} | `{spec.id}` | {spec.scope} | {len(spec.policy.get('rules') or [])} | "
            f"{_threshold(limits.get('tool_calls'))} | {_threshold(limits.get('model_tokens'))} | "
            f"{_threshold(limits.get('spend'))} | {_cell(admitted)} ({harnesses.get('credentials', 'account')}) |"
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
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    SCHEMA_PATH.write_text(schema_text())
    if REFERENCE_PATH.parent.parent.is_dir():
        REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        REFERENCE_PATH.write_text(reference_text())


if __name__ == "__main__":
    main()


__all__ = [
    "POLICIES_DIR",
    "POLICY_CATALOGUE",
    "REFERENCE_PATH",
    "SCHEMA_PATH",
    "SCOPES",
    "SHIELD_SCHEMA_PATH",
    "PolicyError",
    "PolicySpec",
    "document_problems",
    "get_policy",
    "json_schema",
    "load_policies",
    "main",
    "reference_text",
    "schema_text",
    "shield_schema",
]
