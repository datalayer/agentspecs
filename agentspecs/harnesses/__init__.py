# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Harness specifications (SHIELD.md SH-01, §3.1).

A *harness* is an agent program driven over the Agent Client Protocol (ACP):
a coding agent such as Claude Code, Codex, Gemini CLI, Goose, OpenCode or
OpenHands, or any agent a framework exposes over ACP (fast-agent, LangChain's
Deep Agents, …). One YAML per harness under ``harnesses/``: how it is
launched (``acp``), what it needs (``requires``), what it can honour of an
agent spec (``honours``, ``skills``), the file it reads its instructions from
(``instructions_file``), and the terms it is served under (``terms``).

An agent spec names one with ``harness: claude-code`` where it says
``harness: pydantic-ai`` today; what the harness cannot honour — a ``model:``
when it takes none, ``subagents:`` when it has its own, ``skills:`` in a
format it cannot read — is refused at load, in a sentence
(:func:`agent_harness_problems`).

**The register** (SHIELD.md SH-04, §3.3) is ``harnesses/register.yaml``:
every harness of the catalogue with its adapter, the version pinned, its
licence and where that was read, the agent's terms and where they were read,
the credential it takes, whether serving it to third parties is permitted,
its tier restrictions and the binaries it needs. A harness without an entry,
or whose entry disagrees with its spec, does not load. A harness whose terms
are unknown is not in the catalogue.

``custom`` is the one harness with no ``acp`` block: an organization's own
spec names its command; in the shared catalogue it is refused to any agent.

``python -m agentspecs.harnesses`` writes the JSON Schema beside the specs and
the reference page of the documentation.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ROOT = Path(__file__).resolve().parent.parent

#: The harness specs.
HARNESSES_DIR = _ROOT / "harnesses"

#: The register (SH-04).
REGISTER_PATH = HARNESSES_DIR / "register.yaml"

#: The env-vars catalogue a harness's secrets are declared in.
ENV_VARS_DIR = _ROOT / "env-vars"

#: Where the JSON Schema is kept, beside the specs.
SCHEMA_PATH = HARNESSES_DIR / "harness.schema.json"

#: Where the reference page is kept in the documentation site, when the checkout has one.
REFERENCE_PATH = _ROOT.parent / "docs" / "docs" / "harnesses" / "index.md"

#: The harnesses agent-runtimes runs itself, named by `harness:` before this kind existed.
BUILTIN_HARNESSES = ("pydantic-ai", "vercel-ai")

#: The one harness whose command an organization's own spec supplies.
CUSTOM_HARNESS = "custom"

_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")


class HarnessError(ValueError):
    """A harness the catalogue refuses, said in a sentence."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class McpLending(str, Enum):
    """How the harness gets its MCP servers."""

    LEND = "lend"
    """The Shield lends them through the gateway in `session/new` (SHIELD §4.4)."""

    OWN = "own"
    """The harness brings its own MCP servers, which the Shield cannot see."""

    NONE = "none"
    """The harness takes no MCP server."""


class ThirdPartyServing(str, Enum):
    """Whether serving the harness to third parties is permitted by its terms (§3.3)."""

    API_KEY_ONLY = "api_key_only"
    """Permitted with each person's own API key; subscription credentials refused."""

    PERMITTED = "permitted"
    """Permitted with any credential the harness takes."""

    REFUSED = "refused"
    """Not permitted: the harness is listed and never served."""

    ORGANIZATIONS_OWN = "organizations_own"
    """The organization that writes the spec answers for it (`custom`)."""


class SkillsFormat(str, Enum):
    """The format a harness reads skills in (SHIELD §4.10)."""

    SKILL_MD = "skill-md"
    """Folders with a `SKILL.md`, the agentskills.io specification."""

    NONE = "none"
    """It reads no skills."""


class HarnessAcp(_Strict):
    """How the harness is launched and driven over ACP."""

    command: str = Field(min_length=1, description="The executable, as the runtime image has it")
    args: List[str] = Field(default_factory=list, description="Its arguments, the adapter's version pinned among them")
    protocol_version: int = Field(default=1, ge=1, description="The ACP protocol version it speaks")
    load_session: bool = Field(
        default=False, description="Whether it answers `session/load`; read from `initialize`, refused if it lies"
    )
    mcp: McpLending = Field(description="lend, own or none")
    modes: List[str] = Field(default_factory=list, description="The session modes it advertises, as it names them")
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Plain variables the launch needs, never a secret: a secret is declared under `requires.secrets`",
    )


class HarnessRequires(_Strict):
    """What the harness needs in the pod."""

    secrets: List[str] = Field(
        default_factory=list, description="The secrets it reads, each an id of the env-vars catalogue"
    )
    binaries: List[str] = Field(
        default_factory=list,
        description="The executables it needs on the path; one the image installs for it is pinned as name@version",
    )

    @field_validator("secrets")
    @classmethod
    def _declared(cls, values: List[str]) -> List[str]:
        for secret in values:
            if not (ENV_VARS_DIR / f"{secret}.yaml").is_file():
                raise ValueError(f"the secret {secret!r} is not declared in env-vars/: declare it before a harness names it")
        return values


class HarnessTerms(_Strict):
    """The terms it is served under, as the register says them."""

    served_to_third_parties: ThirdPartyServing = Field(description="Whether serving it to third parties is permitted")
    licence: str = Field(min_length=1, description="The adapter's licence, SPDX; and the agent's terms when they are not the same")
    tier_restrictions: Optional[str] = Field(default=None, description="The plans or tiers it may be served under, when its terms restrict them")


class HarnessSkills(_Strict):
    """Where the Shield writes an application's skills for it (§4.10)."""

    format: SkillsFormat = Field(description="skill-md, or none")
    dir: str = Field(default="", description="The directory of the workspace it reads skills from")

    @model_validator(mode="after")
    def _a_dir_when_read(self) -> "HarnessSkills":
        if self.format is SkillsFormat.SKILL_MD and not self.dir:
            raise ValueError("a harness that reads skills says the directory it reads them from")
        if self.format is SkillsFormat.NONE and self.dir:
            raise ValueError("a harness that reads no skills names no directory for them")
        return self


class HarnessHonours(_Strict):
    """What of an agent spec the harness can honour; the rest is refused at load."""

    model: bool = Field(description="Whether it takes the agent's `model:`")
    subagents: bool = Field(description="Whether it takes the agent's `subagents:`; false when it has its own")


class HarnessSpec(_Strict):
    """One harness."""

    id: str = Field(description="Its id, the file's name: what an agent's `harness:` names")
    version: str = Field(description="The version of this spec")
    name: str = Field(min_length=1, description="Its name")
    description: str = Field(min_length=1, description="What it is, in a sentence or two")
    enabled: bool = Field(default=True, description="Whether the shared catalogue offers it")
    tags: List[str] = Field(default_factory=list)
    docs: str = Field(default="", description="Where its ACP use is documented, https")
    acp: Optional[HarnessAcp] = Field(default=None, description="How it is launched; absent only on `custom`")
    requires: HarnessRequires = Field(default_factory=HarnessRequires)
    terms: HarnessTerms
    skills: HarnessSkills
    honours: HarnessHonours
    instructions_file: str = Field(default="", description="The file of the workspace it reads its instructions from")

    @field_validator("id")
    @classmethod
    def _an_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError(f"{value!r} is not a harness id: lower-case letters, digits and hyphens")
        return value

    @field_validator("docs")
    @classmethod
    def _https(cls, value: str) -> str:
        if value and not value.startswith("https://"):
            raise ValueError("documentation is read at an https address")
        return value

    @model_validator(mode="after")
    def _launchable_unless_custom(self) -> "HarnessSpec":
        if self.id == CUSTOM_HARNESS:
            if self.acp is not None:
                raise ValueError("`custom` names no command: an organization's own harness spec names it")
            if self.enabled:
                raise ValueError("`custom` is not offered by the shared catalogue")
            if self.terms.served_to_third_parties is not ThirdPartyServing.ORGANIZATIONS_OWN:
                raise ValueError("`custom` is served under the organization's own terms")
        elif self.acp is None:
            raise ValueError(f"the harness {self.id!r} says how it is launched: an `acp` block with its command")
        return self


class RegisterEntry(_Strict):
    """One line of the register (§3.3): what was checked, and where."""

    harness: str = Field(description="The harness id")
    adapter: str = Field(min_length=1, description="The adapter or binary: an npm or PyPI package, or the program itself")
    version: str = Field(min_length=1, description="The version pinned; it is in the spec's command or args")
    licence: str = Field(min_length=1, description="As the spec's `terms.licence`")
    licence_source: str = Field(description="Where the licence was read, https")
    terms_source: str = Field(description="Where the agent's terms were read, https")
    credential: str = Field(min_length=1, description="The credential it takes")
    served_to_third_parties: ThirdPartyServing
    tier_restrictions: Optional[str] = None
    binaries: str = Field(default="", description="What it needs on the path, with versions")
    note: str = Field(default="")

    @field_validator("licence_source", "terms_source")
    @classmethod
    def _https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("a source is read at an https address")
        return value


class Register(_Strict):
    """The register, as written."""

    checked_on: str = Field(description="The day the entries were checked, ISO")
    reviewed_by_counsel: bool = False
    entries: List[RegisterEntry]


def load_register(path: Path = REGISTER_PATH) -> Dict[str, RegisterEntry]:
    """The register, by harness id; an id registered twice is refused."""
    register = Register.model_validate(yaml.safe_load(path.read_text()) or {})
    found: Dict[str, RegisterEntry] = {}
    for entry in register.entries:
        if entry.harness in found:
            raise HarnessError(f"{path.name}: {entry.harness!r} is registered twice")
        found[entry.harness] = entry
    return found


def _check_against_register(spec: HarnessSpec, entry: Optional[RegisterEntry], name: str) -> None:
    if entry is None:
        raise HarnessError(f"{name}: the harness {spec.id!r} has no entry in the register: a harness whose terms are unknown is not in the catalogue")
    if entry.licence != spec.terms.licence:
        raise HarnessError(f"{name}: the register says licence {entry.licence!r}, the spec says {spec.terms.licence!r}")
    if entry.served_to_third_parties is not spec.terms.served_to_third_parties:
        raise HarnessError(
            f"{name}: the register says third parties {entry.served_to_third_parties.value!r}, "
            f"the spec says {spec.terms.served_to_third_parties.value!r}"
        )
    if (entry.tier_restrictions or None) != (spec.terms.tier_restrictions or None):
        raise HarnessError(f"{name}: the register and the spec disagree on tier restrictions")
    if spec.acp is not None:
        pinned = " ".join([spec.acp.command, *spec.acp.args, *spec.requires.binaries])
        if entry.version not in pinned:
            raise HarnessError(
                f"{name}: the register pins {entry.adapter} {entry.version}, "
                "which neither the launch command nor the binaries name"
            )


def load_harnesses(directory: Path = HARNESSES_DIR, register_path: Path = REGISTER_PATH) -> Dict[str, HarnessSpec]:
    """Every harness of a directory, validated and registered, by id; each file named for its id."""
    register = load_register(register_path)
    found: Dict[str, HarnessSpec] = {}
    for path in sorted(directory.glob("*.yaml")):
        if path.name == register_path.name:
            continue
        spec = HarnessSpec.model_validate(yaml.safe_load(path.read_text()) or {})
        if spec.id != path.stem:
            raise HarnessError(f"{path.name}: the file is named for {path.stem!r}, the spec says {spec.id!r}")
        _check_against_register(spec, register.get(spec.id), path.name)
        found[spec.id] = spec
    unknown = sorted(set(register) - set(found))
    if unknown:
        raise HarnessError(f"{register_path.name}: registered but not in the catalogue: {', '.join(unknown)}")
    return found


#: Every harness of the catalogue, by id.
HARNESS_CATALOGUE: Dict[str, HarnessSpec] = load_harnesses()

#: The register, by harness id.
HARNESS_REGISTER: Dict[str, RegisterEntry] = load_register()


def get_harness(harness_id: str) -> Optional[HarnessSpec]:
    """A harness by id, or None."""
    return HARNESS_CATALOGUE.get(harness_id)


def harness_problems(
    harness_id: str,
    *,
    model: Optional[str] = None,
    subagents: Any = None,
    skills: Any = None,
    catalogue: Optional[Dict[str, HarnessSpec]] = None,
) -> List[str]:
    """What is wrong with an agent spec that names this harness, in sentences.

    Nothing for a builtin harness (`pydantic-ai`, `vercel-ai`). Otherwise: a
    harness the catalogue does not know, `custom` in the shared catalogue, a
    `model:` the harness does not take, `subagents:` when it has its own, and
    `skills:` when it reads none.
    """
    if harness_id in BUILTIN_HARNESSES:
        return []
    catalogue = HARNESS_CATALOGUE if catalogue is None else catalogue
    spec = catalogue.get(harness_id)
    if spec is None:
        return [f"There is no harness named {harness_id!r}: one of {', '.join([*BUILTIN_HARNESSES, *sorted(catalogue)])}."]
    if harness_id == CUSTOM_HARNESS:
        return ["The harness 'custom' names no command: an organization's own harness spec names it, and is never typed into a form."]
    problems: List[str] = []
    if model and not spec.honours.model:
        problems.append(f"The harness {harness_id!r} does not take a model: drop `model:`.")
    if subagents and not spec.honours.subagents:
        problems.append(f"The harness {harness_id!r} has its own subagents: drop `subagents:`.")
    if skills and spec.skills.format is SkillsFormat.NONE:
        problems.append(f"The harness {harness_id!r} reads no skills: drop `skills:`.")
    return problems


def agent_harness_problems(agent: Dict[str, Any], catalogue: Optional[Dict[str, HarnessSpec]] = None) -> List[str]:
    """:func:`harness_problems` for an agent spec as written in YAML."""
    return harness_problems(
        str(agent.get("harness") or BUILTIN_HARNESSES[0]),
        model=agent.get("model"),
        subagents=agent.get("subagents"),
        skills=agent.get("skills"),
        catalogue=catalogue,
    )


def json_schema() -> Dict[str, object]:
    """The JSON Schema of a harness spec."""
    schema = HarnessSpec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://agentspecs.datalayer.tech/schemas/harness.json"
    schema["title"] = "Harness"
    return schema


def schema_text() -> str:
    """The JSON Schema as it is written to :data:`SCHEMA_PATH`."""
    return json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"


def _cell(text: object) -> str:
    words = " ".join(str(text if text is not None else "").split())
    return words.replace("|", "\\|").replace("<", "&lt;").replace("{", "\\{").replace("}", "\\}")


def reference_text() -> str:
    """The reference page: every harness with its launch and its register entry."""
    lines = [
        "<!-- Generated by `python -m agentspecs.harnesses` from harnesses/*.yaml. Do not edit. -->",
        "",
        "# Harnesses",
        "",
        "An agent program driven over the Agent Client Protocol, one spec each under",
        "`agentspecs/harnesses/` (SHIELD.md §3.1). An agent spec names one with `harness:`",
        "where it says `pydantic-ai` or `vercel-ai`; what the harness cannot honour of the",
        "spec is refused at load. The register (`harnesses/register.yaml`, §3.3) says the",
        "terms each is served under and where they were read; a harness without an entry",
        "does not load. None is served by a runtime yet (SHIELD SH-10).",
        "",
        "| Harness | Id | Launch | MCP | Skills | Instructions | Third parties | Licence | Pinned |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for spec in sorted(HARNESS_CATALOGUE.values(), key=lambda s: s.id):
        entry = HARNESS_REGISTER[spec.id]
        launch = " ".join([spec.acp.command, *spec.acp.args]) if spec.acp else "the organization's own"
        skills = f"`{spec.skills.dir}`" if spec.skills.format is SkillsFormat.SKILL_MD else "none"
        title = f"[{_cell(spec.name)}]({spec.docs})" if spec.docs else _cell(spec.name)
        lines.append(
            f"| {title} | `{spec.id}` | `{_cell(launch)}` | {spec.acp.mcp.value if spec.acp else ''} "
            f"| {skills} | {'`' + spec.instructions_file + '`' if spec.instructions_file else ''} "
            f"| {spec.terms.served_to_third_parties.value} | {_cell(spec.terms.licence)} | {_cell(entry.adapter)} {_cell(entry.version)} |"
        )
    lines += ["", "## Each harness", ""]
    for spec in sorted(HARNESS_CATALOGUE.values(), key=lambda s: s.id):
        entry = HARNESS_REGISTER[spec.id]
        lines += [f"### {spec.name} (`{spec.id}`)", "", " ".join(spec.description.split()), ""]
        lines.append(f"- Credential: {_cell(entry.credential)}; secrets declared: {', '.join(f'`{s}`' for s in spec.requires.secrets) or 'none'}")
        lines.append(f"- Needs: {_cell(entry.binaries) or ', '.join(spec.requires.binaries) or 'nothing'}")
        if spec.acp:
            lines.append(
                f"- ACP {spec.acp.protocol_version}: `session/load` {'yes' if spec.acp.load_session else 'no'}; "
                f"modes {', '.join(f'`{m}`' for m in spec.acp.modes) or 'none advertised'}"
            )
        lines.append(f"- Honours `model:` {'yes' if spec.honours.model else 'no'}, `subagents:` {'yes' if spec.honours.subagents else 'no'}")
        if spec.terms.tier_restrictions:
            lines.append(f"- Tiers: {_cell(spec.terms.tier_restrictions)}")
        lines.append(f"- Licence read at {entry.licence_source}; terms read at {entry.terms_source}")
        if entry.note:
            lines.append(f"- {_cell(entry.note)}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    SCHEMA_PATH.write_text(schema_text())
    if REFERENCE_PATH.parent.parent.is_dir():
        REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        REFERENCE_PATH.write_text(reference_text())


if __name__ == "__main__":
    main()


__all__ = [
    "BUILTIN_HARNESSES",
    "CUSTOM_HARNESS",
    "HARNESS_CATALOGUE",
    "HARNESS_REGISTER",
    "HarnessAcp",
    "HarnessError",
    "HarnessHonours",
    "HarnessRequires",
    "HarnessSkills",
    "HarnessSpec",
    "HarnessTerms",
    "McpLending",
    "Register",
    "RegisterEntry",
    "SkillsFormat",
    "ThirdPartyServing",
    "agent_harness_problems",
    "get_harness",
    "harness_problems",
    "json_schema",
    "load_harnesses",
    "load_register",
    "reference_text",
    "schema_text",
]
