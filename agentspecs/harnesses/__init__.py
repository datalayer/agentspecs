# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Harness specifications.

A *harness* is an agent program driven over the Agent Client Protocol (ACP):
a coding agent such as Claude Code, Codex, OpenCode, pi, Gemini CLI, Goose or
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

**The register** is ``harnesses/register.yaml``:
every harness of the catalogue with its adapter, the version pinned, its
licence and where that was read, the agent's terms and where they were read,
the credential it takes, whether serving it to third parties is permitted,
its tier restrictions and the binaries it needs. A harness without an entry,
or whose entry disagrees with its spec, does not load. A harness whose terms
are unknown is not in the catalogue.

``custom`` is the one harness with no ``acp`` block: an organization's own
spec names its command; in the shared catalogue it is refused to any agent.

**The capabilities table** (``capabilities:``) says what a session
may rely on of the harness — how its own session comes back (``resume``:
none, load or native), what a clone carries of its history
(``fork_history``: none, replay or rebuild), whether a turn can be
interrupted, whether it takes input mid-turn, whether a prompt may carry an
image, who compacts the context, and the modes a swap or a clone may set.
``auto_run`` lists the commands the harness runs without asking its client
(Claude Code's read-only allowlist: ``cat``, ``wc``, ``git status``…), one
regular expression per family read from the harness's own source for the
pinned version: the platform's *ask me first* on a command knowingly
excludes them, and a run of one is never an action against the rules.
A harness without the table is refused; a table that contradicts the ``acp``
block (``resume`` without ``load_session``, ``modes`` that disagree) is
refused in a sentence. ``acp.native_session`` says whether the adapter
exposes the vendor's own session id (``meta``) or not (``none``); the
session's operations read the table, never ``if harness == …``.

**Two tiers**. An entry of the register is in the ``catalogue`` tier
(the default) when a spec beside it launches the harness, drilled on Datalayer;
it is ``listed`` when the agent is known to speak ACP — its launch
command as its project documents it (or none, when undocumented), its
licence, its terms and the credential it takes, each read and cited — and
not drilled yet. A listed harness has no spec: it is offered by nothing,
and naming it is refused in the sentence *listed, not drilled yet*
(:func:`listed_refusal`). It moves to the catalogue with a spec once drilled.

**An organization's own harness** is ``custom`` made concrete: a
spec whose id starts with ``org-``, kept in that organization's catalogue
(IAM's organization document, as its own Frames are), with its register
entry beside it — the terms, the licence and the credential, required as
for any harness. It is refused in the shared catalogue.
:func:`organization_harness` validates the two together, and
:func:`admission_id` names what an administrator admits on the
organization's policy (``harnesses.admit``): the id *and* the digest of the
command reviewed, so a changed command is not admitted until reviewed again.

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

#: The register.
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

#: What an organization's own harness id starts with, as its own Frames' ids do.
ORGANIZATION_HARNESS_PREFIX = "org-"

#: The sentence a listed harness is refused in.
LISTED_NOT_DRILLED = "listed, not drilled yet"

_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")


class HarnessError(ValueError):
    """A harness the catalogue refuses, said in a sentence."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class McpLending(str, Enum):
    """How the harness gets its MCP servers."""

    LEND = "lend"
    """The Shield lends them through the gateway in `session/new`."""

    OWN = "own"
    """The harness brings its own MCP servers, which the Shield cannot see."""

    NONE = "none"
    """The harness takes no MCP server."""


class ThirdPartyServing(str, Enum):
    """Whether serving the harness to third parties is permitted by its terms."""

    API_KEY_ONLY = "api_key_only"
    """Permitted with each person's own API key; subscription credentials refused."""

    PERMITTED = "permitted"
    """Permitted with any credential the harness takes."""

    REFUSED = "refused"
    """Not permitted: the harness is listed and never served."""

    ORGANIZATIONS_OWN = "organizations_own"
    """The organization that writes the spec answers for it (`custom`)."""

    UNKNOWN = "unknown"
    """Not determined from what was read: only in the listed tier."""


class RegisterTier(str, Enum):
    """Whether a registered harness is offered."""

    CATALOGUE = "catalogue"
    """A spec launches it; drilled; offered by `setup`, the Studio and the runtime."""

    LISTED = "listed"
    """Known to speak ACP, its terms read; not drilled, offered by nothing."""


class SkillsFormat(str, Enum):
    """The format a harness reads skills in."""

    SKILL_MD = "skill-md"
    """Folders with a `SKILL.md`, the agentskills.io specification."""

    NONE = "none"
    """It reads no skills."""


class ResumeCapability(str, Enum):
    """How a harness's own session comes back after its process ended."""

    NONE = "none"
    """It cannot: a swap back to it, or a runtime restarted, starts it over (said in a sentence)."""

    LOAD = "load"
    """ACP's `session/load`: the adapter replays the session's history, compared with the record."""

    NATIVE = "native"
    """The vendor's own resume (`claude --resume`, `codex resume`) through the adapter, by the vendor's id."""


class ForkHistory(str, Enum):
    """What a clone of a session carries of the harness's own history."""

    NONE = "none"
    """Nothing: a clone starts the harness over, and is told so."""

    REPLAY = "replay"
    """The conversation up to the turn replayed as text — the harness reads it as history, not as its own turns."""

    REBUILD = "rebuild"
    """The vendor's resumable session file rebuilt from the copied entries, so the clone resumes the harness's own history."""


class Compaction(str, Enum):
    """Who compacts the context window."""

    OWN = "own"
    """The harness compacts its own context; the record is never compacted."""

    NONE = "none"
    """Nothing compacts: the context grows until the harness refuses."""


class NativeSession(str, Enum):
    """Whether the adapter exposes the vendor's own session id."""

    META = "meta"
    """In `session/new`'s `_meta`, or the first `session/update`'s: kept beside the ACP session id."""

    NONE = "none"
    """It does not: the ACP session id is all there is, and `session/load` the only way back."""


class HarnessCapabilities(_Strict):
    """What a session may rely on of the harness: declared here, verified by the drill, read by the session's operations instead of `if harness == …`."""

    resume: ResumeCapability = Field(description="none, load or native: how its own session comes back")
    fork_history: ForkHistory = Field(description="none, replay or rebuild: what a clone carries of its history")
    interrupt: bool = Field(description="Whether a running turn can be cancelled (`session/cancel`)")
    steering: bool = Field(description="Whether it takes input mid-turn; ACP has none, so false for every catalogue harness")
    images: bool = Field(description="Whether a prompt may carry an image (`promptCapabilities.image`)")
    compaction: Compaction = Field(description="own or none: who compacts the context")
    modes: List[str] = Field(default_factory=list, description="The session modes a swap or a clone may set, as `acp.modes` names them")
    auto_run: List[str] = Field(
        default_factory=list,
        description=(
            "The commands the harness runs without asking its client, as it ships them: one regular expression per "
            "family, anchored at the start of a pipeline segment; empty when it asks about every command. Read from the "
            "harness's own source for the version the register pins, never guessed, so the platform's rule on commands "
            "knowingly excludes them and a run of one is never an action against the rules"
        ),
    )

    @field_validator("auto_run")
    @classmethod
    def _patterns_compile(cls, value: List[str]) -> List[str]:
        for pattern in value:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(f"capabilities.auto_run: {pattern!r} is not a regular expression: {error}") from None
            if not pattern.startswith("^"):
                raise ValueError(f"capabilities.auto_run: {pattern!r} is anchored at the segment's start with ^")
        return value


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
    native_session: NativeSession = Field(
        default=NativeSession.NONE,
        description="meta when the adapter exposes the vendor's own session id, none when it does not: found by the drill, never guessed",
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
    """Where the Shield writes an application's skills for it."""

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
    unavailable_because: str = Field(
        default="",
        description=(
            "Why it is not offered today, in a sentence the runtime, `loop` and the Studio say "
            "when it is named: said when `enabled` is false, and only then (`custom` needs none)"
        ),
    )
    tags: List[str] = Field(default_factory=list)
    docs: str = Field(default="", description="Where its ACP use is documented, https")
    acp: Optional[HarnessAcp] = Field(default=None, description="How it is launched; absent only on `custom`")
    requires: HarnessRequires = Field(default_factory=HarnessRequires)
    terms: HarnessTerms
    skills: HarnessSkills
    honours: HarnessHonours
    capabilities: HarnessCapabilities = Field(description="What a session may rely on of it: resume, fork_history, interrupt, steering, images, compaction, modes")
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

    @model_validator(mode="after")
    def _not_offered_says_why(self) -> "HarnessSpec":
        """A harness the catalogue does not offer says why, and an offered one says nothing."""
        if self.id == CUSTOM_HARNESS:
            return self
        if not self.enabled and not self.unavailable_because.strip():
            raise ValueError(
                f"the harness {self.id!r} is not offered: say why, under `unavailable_because`"
            )
        if self.enabled and self.unavailable_because.strip():
            raise ValueError(
                f"the harness {self.id!r} is offered: remove `unavailable_because`, or set `enabled: false`"
            )
        return self

    @model_validator(mode="after")
    def _capabilities_agree_with_acp(self) -> "HarnessSpec":
        """The table says nothing the `acp` block contradicts: one truth, said twice, must agree."""
        if self.acp is None:
            return self
        loads = self.capabilities.resume is not ResumeCapability.NONE
        if loads and not self.acp.load_session:
            raise ValueError(
                f"the harness {self.id!r} says capabilities.resume {self.capabilities.resume.value!r} "
                "but acp.load_session false: a session that comes back is one the adapter loads"
            )
        if self.acp.load_session and not loads:
            raise ValueError(
                f"the harness {self.id!r} says acp.load_session true but capabilities.resume none: "
                "say load (or native) or drop load_session"
            )
        if list(self.capabilities.modes) != list(self.acp.modes):
            raise ValueError(
                f"the harness {self.id!r}: capabilities.modes {self.capabilities.modes!r} and "
                f"acp.modes {self.acp.modes!r} disagree; they name the same modes"
            )
        return self


class RegisterEntry(_Strict):
    """One line of the register: what was checked, and where."""

    harness: str = Field(description="The harness id")
    tier: RegisterTier = Field(default=RegisterTier.CATALOGUE, description="catalogue (drilled, offered) or listed (not yet)")
    name: str = Field(default="", description="Its name, for a listed harness, which has no spec to say it")
    docs: str = Field(default="", description="Where its ACP use is documented, for a listed harness, https")
    command: Optional[str] = Field(
        default=None,
        description="A listed harness's launch command as its project documents it; null when undocumented",
    )
    adapter: str = Field(default="", description="The adapter or binary: an npm or PyPI package, or the program itself")
    version: str = Field(default="", description="The version pinned; it is in the spec's command or args")
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

    @field_validator("docs")
    @classmethod
    def _docs_https(cls, value: str) -> str:
        if value and not value.startswith("https://"):
            raise ValueError("documentation is read at an https address")
        return value

    @model_validator(mode="after")
    def _by_tier(self) -> "RegisterEntry":
        if self.tier is RegisterTier.CATALOGUE:
            if not self.adapter or not self.version:
                raise ValueError(f"{self.harness}: a catalogue harness names its adapter and the version pinned")
            if self.served_to_third_parties is ThirdPartyServing.UNKNOWN:
                raise ValueError(
                    f"{self.harness}: a harness whose terms are unknown is not in the catalogue (listed at most)"
                )
            if self.command is not None or self.name or self.docs:
                raise ValueError(
                    f"{self.harness}: a catalogue harness's spec says its name, docs and command, not the register"
                )
        else:
            if not self.name:
                raise ValueError(f"{self.harness}: a listed harness says its name")
            if not self.docs:
                raise ValueError(f"{self.harness}: a listed harness cites where its ACP use is documented")
            if self.command is not None and not self.command.strip():
                raise ValueError(f"{self.harness}: a listed harness's command is the documented one, or null")
        return self

    @property
    def is_listed(self) -> bool:
        return self.tier is RegisterTier.LISTED


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
        if spec.id.startswith(ORGANIZATION_HARNESS_PREFIX):
            raise HarnessError(
                f"{path.name}: {spec.id!r} is an organization's own harness id: it is kept in its "
                "organization's catalogue, never the shared one"
            )
        entry = register.get(spec.id)
        if entry is not None and entry.is_listed:
            raise HarnessError(
                f"{path.name}: {spec.id!r} is {LISTED_NOT_DRILLED} in the register: move its entry to the "
                "catalogue tier once drilled, with its adapter and the version pinned"
            )
        _check_against_register(spec, entry, path.name)
        found[spec.id] = spec
    unknown = sorted(set(register) - set(found) - {key for key, entry in register.items() if entry.is_listed})
    if unknown:
        raise HarnessError(f"{register_path.name}: registered but not in the catalogue: {', '.join(unknown)}")
    return found


#: Every harness of the catalogue, by id.
HARNESS_CATALOGUE: Dict[str, HarnessSpec] = load_harnesses()

#: The register, by harness id: the catalogue's entries and the listed ones.
HARNESS_REGISTER: Dict[str, RegisterEntry] = load_register()

#: The listed tier: known to speak ACP, not drilled, offered by nothing.
LISTED_HARNESSES: Dict[str, RegisterEntry] = {
    harness_id: entry for harness_id, entry in HARNESS_REGISTER.items() if entry.is_listed
}


def get_harness(harness_id: str) -> Optional[HarnessSpec]:
    """A harness by id, or None."""
    return HARNESS_CATALOGUE.get(harness_id)


def offered_refusal(harness_id: str) -> Optional[str]:
    """The sentence that refuses a catalogue harness the catalogue does not offer, or None.

    A harness with a spec and `enabled: false` is described, never launched:
    the sentence is its `unavailable_because`, said wherever it is named — the
    runtime, `loop --harness`, the Studio. `custom` is refused by its own
    sentence (it names no command), not this one; a harness the catalogue
    does not know is none of this (see `listed_refusal`).
    """
    spec = HARNESS_CATALOGUE.get(harness_id)
    if spec is None or spec.enabled or spec.id == CUSTOM_HARNESS:
        return None
    return f"The harness {harness_id!r} ({spec.name}) is not offered: {spec.unavailable_because.strip()}"


def listed_refusal(harness_id: str) -> Optional[str]:
    """The sentence that refuses a listed harness, or None when it is not listed."""
    entry = LISTED_HARNESSES.get(harness_id)
    if entry is None:
        return None
    command = f"`{entry.command}`" if entry.command else "no documented command"
    return (
        f"The harness {harness_id!r} ({entry.name}) is {LISTED_NOT_DRILLED}: it is registered with "
        f"{command} and its terms, and is offered once drilled and moved to the catalogue."
    )


# --- an organization's own harness ---------------------------------------------


def is_organization_harness(harness_id: str) -> bool:
    """Whether the id names an organization's own harness (``org-…``)."""
    return harness_id.startswith(ORGANIZATION_HARNESS_PREFIX)


def command_digest(spec: HarnessSpec) -> str:
    """The digest of what a harness launches — its command, arguments and plain variables.

    What an administrator reviews: a changed command has another digest, and
    is not admitted until reviewed again.
    """
    import hashlib

    if spec.acp is None:
        raise HarnessError(f"the harness {spec.id!r} launches nothing to review")
    reviewed = {"command": spec.acp.command, "args": list(spec.acp.args), "env": dict(sorted(spec.acp.env.items()))}
    canonical = json.dumps(reviewed, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def admission_id(spec: HarnessSpec) -> str:
    """What an organization's policy admits for its own harness: ``<id>@<the reviewed command's digest, 12>``."""
    return f"{spec.id}@{command_digest(spec)[:12]}"


def organization_harness(spec: Dict[str, Any], entry: Dict[str, Any]) -> tuple:
    """An organization's own harness and its register entry, validated together.

    The spec is a harness spec whose id starts with ``org-``, with an ``acp``
    block naming its command; the entry is its line of the register, in the
    catalogue tier, with its licence, its terms, the credential it takes and
    whether serving it to third parties is permitted — required, as for any
    harness: a harness whose terms are unknown is served nowhere.

    Returns
    -------
    tuple[HarnessSpec, RegisterEntry]

    Raises
    ------
    HarnessError
        In a sentence.
    """
    if not isinstance(spec, dict) or not isinstance(entry, dict):
        raise HarnessError("an organization's own harness is a spec and its register entry, each an object")
    harness_id = str(spec.get("id") or "")
    if not is_organization_harness(harness_id):
        raise HarnessError(
            f"{harness_id!r} is not an organization's own harness id: it starts with {ORGANIZATION_HARNESS_PREFIX!r}"
        )
    try:
        parsed = HarnessSpec.model_validate(spec)
        registered = RegisterEntry.model_validate({"harness": harness_id, **entry})
    except ValueError as invalid:
        raise HarnessError(f"the organization's harness {harness_id!r} is refused: {invalid}") from None
    if registered.harness != harness_id:
        raise HarnessError(f"the register entry names {registered.harness!r}, the spec {harness_id!r}")
    if registered.is_listed:
        raise HarnessError(f"an organization's own harness is in the catalogue tier: {harness_id!r} says listed")
    if registered.served_to_third_parties is ThirdPartyServing.REFUSED:
        raise HarnessError(f"the organization's harness {harness_id!r}: its terms refuse serving it to third parties")
    _check_against_register(parsed, registered, harness_id)
    return parsed, registered


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
        listed = listed_refusal(harness_id)
        if listed is not None:
            return [listed]
        if is_organization_harness(harness_id):
            return [
                f"The harness {harness_id!r} is an organization's own: it is read from its organization's "
                "catalogue on Datalayer, admitted by its policy, and served nowhere else."
            ]
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
        "`agentspecs/harnesses/`. An agent spec names one with `harness:`",
        "where it says `pydantic-ai` or `vercel-ai`; what the harness cannot honour of the",
        "spec is refused at load. The register (`harnesses/register.yaml`) says the",
        "terms each is served under and where they were read; a harness without an entry",
        "does not load. The Datalayer runtime serves the offered ones; a harness",
        "described here and not offered is refused in its own sentence wherever it is named.",
        "",
        "| Harness | Id | Launch | MCP | Skills | Instructions | Third parties | Licence | Pinned |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    offered = [spec for spec in HARNESS_CATALOGUE.values() if spec.enabled]
    not_offered = [spec for spec in HARNESS_CATALOGUE.values() if not spec.enabled and spec.id != CUSTOM_HARNESS]
    for spec in sorted(offered, key=lambda s: s.id):
        entry = HARNESS_REGISTER[spec.id]
        launch = " ".join([spec.acp.command, *spec.acp.args]) if spec.acp else "the organization's own"
        skills = f"`{spec.skills.dir}`" if spec.skills.format is SkillsFormat.SKILL_MD else "none"
        title = f"[{_cell(spec.name)}]({spec.docs})" if spec.docs else _cell(spec.name)
        lines.append(
            f"| {title} | `{spec.id}` | `{_cell(launch)}` | {spec.acp.mcp.value if spec.acp else ''} "
            f"| {skills} | {'`' + spec.instructions_file + '`' if spec.instructions_file else ''} "
            f"| {spec.terms.served_to_third_parties.value} | {_cell(spec.terms.licence)} | {_cell(entry.adapter)} {_cell(entry.version)} |"
        )
    lines += [
        "",
        "## Not offered today",
        "",
        "Described — a spec, a register entry, a capabilities table — and not offered: naming one",
        "is refused with the sentence below, by the runtime, by `loop --harness` and by the Studio.",
        "",
        "| Harness | Id | Why not |",
        "| --- | --- | --- |",
    ]
    for spec in sorted(not_offered, key=lambda s: s.id):
        title = f"[{_cell(spec.name)}]({spec.docs})" if spec.docs else _cell(spec.name)
        lines.append(f"| {title} | `{spec.id}` | {_cell(spec.unavailable_because)} |")
    lines += [
        "",
        "## Listed, not drilled yet",
        "",
        "Agents known to speak ACP, registered with their launch command as their projects",
        "document it, their licence, their terms and the credential they take. None is",
        "offered: naming one is refused, *listed, not drilled yet*, until it is drilled and moved",
        "to the catalogue with a spec.",
        "",
        "| Agent | Id | Documented command | Licence | Third parties | Credential |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in sorted(LISTED_HARNESSES.values(), key=lambda e: e.harness):
        command = f"`{_cell(entry.command)}`" if entry.command else "undocumented"
        lines.append(
            f"| [{_cell(entry.name)}]({entry.docs}) | `{entry.harness}` | {command} | {_cell(entry.licence)} "
            f"| {entry.served_to_third_parties.value} | {_cell(entry.credential)} |"
        )
    lines += ["", "## Each harness", ""]
    for spec in sorted(HARNESS_CATALOGUE.values(), key=lambda s: s.id):
        entry = HARNESS_REGISTER[spec.id]
        lines += [f"### {spec.name} (`{spec.id}`)", "", " ".join(spec.description.split()), ""]
        if not spec.enabled and spec.id != CUSTOM_HARNESS:
            lines.append(f"- Not offered: {_cell(spec.unavailable_because)}")
        lines.append(f"- Credential: {_cell(entry.credential)}; secrets declared: {', '.join(f'`{s}`' for s in spec.requires.secrets) or 'none'}")
        lines.append(f"- Needs: {_cell(entry.binaries) or ', '.join(spec.requires.binaries) or 'nothing'}")
        if spec.acp:
            lines.append(
                f"- ACP {spec.acp.protocol_version}: `session/load` {'yes' if spec.acp.load_session else 'no'}; "
                f"modes {', '.join(f'`{m}`' for m in spec.acp.modes) or 'none advertised'}"
            )
        lines.append(f"- Honours `model:` {'yes' if spec.honours.model else 'no'}, `subagents:` {'yes' if spec.honours.subagents else 'no'}")
        caps = spec.capabilities
        lines.append(
            f"- Capabilities: resume `{caps.resume.value}`, fork history `{caps.fork_history.value}`, "
            f"interrupt {'yes' if caps.interrupt else 'no'}, steering {'yes' if caps.steering else 'no'}, "
            f"images {'yes' if caps.images else 'no'}, compaction `{caps.compaction.value}`"
            + (f"; vendor session id `{spec.acp.native_session.value}`" if spec.acp else "")
            + (
                f"; runs unasked {len(caps.auto_run)} command families (its own read-only allowlist)"
                if caps.auto_run
                else "; asks about every command"
            )
        )
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
    "LISTED_HARNESSES",
    "LISTED_NOT_DRILLED",
    "ORGANIZATION_HARNESS_PREFIX",
    "RegisterTier",
    "admission_id",
    "command_digest",
    "is_organization_harness",
    "listed_refusal",
    "offered_refusal",
    "organization_harness",
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
