# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The agent protocols Datalayer targets, as specs (AGENT_PROTOCOLS PS-01).

One YAML per protocol under ``protocols/``: what it is, who publishes it, its
layer (transport, consent, identity, commerce, ui), the specification and the
version implemented, whether it is ``shipped`` or ``planned``, what it connects
an agent to, the packages implementing it, the ``protocol-tools`` tables of its
tools, and the Appspec block that configures it, if any.

An agent spec or an application says the protocols it speaks in ``protocols``
(PS-02): ids of this catalogue, a planned one refused for an application.

``python -m agentspecs.protocols`` writes the JSON Schema beside the specs and
the reference page of the documentation.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

#: The protocol specs.
PROTOCOLS_DIR = Path(__file__).resolve().parent / "protocols"

#: The protocol-tools tables a protocol may name.
PROTOCOL_TOOLS_DIR = Path(__file__).resolve().parent / "protocol-tools"

#: Where the JSON Schema is kept, beside the specs.
SCHEMA_PATH = PROTOCOLS_DIR / "protocol.schema.json"

#: Where the reference page is kept in the documentation site, when the checkout has one.
REFERENCE_PATH = Path(__file__).resolve().parents[1] / "docs" / "docs" / "agents" / "protocols" / "index.md"

_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")


class ProtocolLayer(str, Enum):
    """The layer of an agent's visit a protocol answers (AGENT_PROTOCOLS §1, after poppy.md)."""

    TRANSPORT = "transport"
    CONSENT = "consent"
    IDENTITY = "identity"
    COMMERCE = "commerce"
    UI = "ui"


class ProtocolStatus(str, Enum):
    """Where a protocol stands: implemented by agent-runtimes today, or only planned."""

    SHIPPED = "shipped"
    PLANNED = "planned"


class AppspecBlock(str, Enum):
    """The Appspec blocks a protocol configures."""

    PAP = "pap"
    PACT = "pact"
    A2A = "a2a"


class ProtocolPackages(BaseModel):
    """The packages implementing it, by language."""

    model_config = ConfigDict(extra="forbid")

    python: List[str] = Field(default_factory=list, description="Python distributions")
    typescript: List[str] = Field(default_factory=list, description="npm packages")


class ProtocolSpec(BaseModel):
    """One agent protocol."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Its id, the file's name: what `protocols` lists")
    version: str = Field(description="The version of this spec")
    name: str = Field(min_length=1, description="Its name")
    description: str = Field(min_length=1, description="What it does, in a sentence or two")
    publisher: str = Field(min_length=1, description="Who publishes the specification")
    layer: ProtocolLayer = Field(description="The layer it answers")
    spec_url: str = Field(description="The specification, https")
    spec_version: str = Field(min_length=1, description="The version of the specification implemented")
    status: ProtocolStatus = Field(description="shipped, or planned")
    connects: str = Field(min_length=1, description="What it connects an agent to")
    packages: ProtocolPackages = Field(default_factory=ProtocolPackages)
    protocol_tools: List[str] = Field(
        default_factory=list, description="Its tools' action-class tables, under protocol-tools/"
    )
    appspec_block: Optional[AppspecBlock] = Field(
        default=None, description="The Appspec block that configures it: refused unless `protocols` lists it"
    )

    @field_validator("id")
    @classmethod
    def _an_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError(f"{value!r} is not a protocol id: lower-case letters, digits and hyphens")
        return value

    @field_validator("spec_url")
    @classmethod
    def _https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("a specification is read at an https address")
        return value

    @field_validator("protocol_tools")
    @classmethod
    def _tables_exist(cls, values: List[str]) -> List[str]:
        for table in values:
            if not (PROTOCOL_TOOLS_DIR / f"{table}.yaml").is_file():
                raise ValueError(f"there is no protocol-tools table {table!r}")
        return values


def load_protocols(directory: Path = PROTOCOLS_DIR) -> Dict[str, ProtocolSpec]:
    """Every protocol of a directory, validated, by id; each file named for its id, each block once."""
    found: Dict[str, ProtocolSpec] = {}
    blocks: Dict[str, str] = {}
    for path in sorted(directory.glob("*.yaml")):
        spec = ProtocolSpec.model_validate(yaml.safe_load(path.read_text()) or {})
        if spec.id != path.stem:
            raise ValueError(f"{path.name}: the file is named for {path.stem!r}, the spec says {spec.id!r}")
        if spec.appspec_block is not None:
            block = spec.appspec_block.value
            if block in blocks:
                raise ValueError(f"{path.name}: the block {block!r} is already {blocks[block]!r}'s")
            blocks[block] = spec.id
        found[spec.id] = spec
    return found


#: Every protocol of the catalogue, by id.
PROTOCOL_CATALOGUE: Dict[str, ProtocolSpec] = load_protocols()


def get_protocol(protocol_id: str) -> Optional[ProtocolSpec]:
    """A protocol by id, or None."""
    return PROTOCOL_CATALOGUE.get(protocol_id)


def protocol_of_block(block: str) -> ProtocolSpec:
    """The protocol an Appspec block configures."""
    for spec in PROTOCOL_CATALOGUE.values():
        if spec.appspec_block is not None and spec.appspec_block.value == block:
            return spec
    raise KeyError(block)


def protocols_problems(ids: List[str], *, to_ship: bool) -> List[str]:
    """What is wrong with a list of protocols, in sentences: unknown, said twice, or planned for an application."""
    problems: List[str] = []
    seen: List[str] = []
    for protocol_id in ids:
        if protocol_id in seen:
            problems.append(f"It lists the protocol {protocol_id!r} twice.")
            continue
        seen.append(protocol_id)
        spec = get_protocol(protocol_id)
        if spec is None:
            problems.append(
                f"There is no protocol named {protocol_id!r}: one of {', '.join(sorted(PROTOCOL_CATALOGUE))}."
            )
        elif to_ship and spec.status is ProtocolStatus.PLANNED:
            problems.append(f"{spec.name} ({protocol_id!r}) is planned, not shipped: an application cannot speak it yet.")
    return problems


def json_schema() -> Dict[str, object]:
    """The JSON Schema of a protocol spec."""
    schema = ProtocolSpec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://agentspecs.datalayer.tech/schemas/protocol.json"
    schema["title"] = "Protocol"
    return schema


def schema_text() -> str:
    """The JSON Schema as it is written to :data:`SCHEMA_PATH`."""
    return json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"


def _cell(text: object) -> str:
    words = " ".join(str(text if text is not None else "").split())
    return words.replace("|", "\\|").replace("<", "&lt;").replace("{", "\\{").replace("}", "\\}")


def reference_text() -> str:
    """The reference page: every protocol, by layer, as its spec says it."""
    lines = [
        "<!-- Generated by `python -m agentspecs.protocols` from protocols/*.yaml. Do not edit. -->",
        "",
        "# Protocols",
        "",
        "The agent protocols Datalayer targets, one spec each under `agentspecs/protocols/`.",
        "An agent spec or an application lists the ones it speaks in `protocols`; an",
        "application may not list a planned one, and its `pap`, `pact` and `a2a` blocks",
        "are refused unless their protocol is listed.",
        "",
        "| Protocol | Id | Layer | Publisher | Version implemented | Status | Connects to | Appspec block |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    order = [layer.value for layer in ProtocolLayer]
    for spec in sorted(PROTOCOL_CATALOGUE.values(), key=lambda s: (order.index(s.layer.value), s.id)):
        lines.append(
            f"| [{_cell(spec.name)}]({spec.spec_url}) | `{spec.id}` | {spec.layer.value} | {_cell(spec.publisher)} "
            f"| {_cell(spec.spec_version)} | {spec.status.value} | {_cell(spec.connects)} "
            f"| {'`' + spec.appspec_block.value + '`' if spec.appspec_block else ''} |"
        )
    lines += ["", "## Each protocol", ""]
    for spec in sorted(PROTOCOL_CATALOGUE.values(), key=lambda s: s.id):
        lines += [f"### {spec.name} (`{spec.id}`)", "", " ".join(spec.description.split()), ""]
        if spec.packages.python:
            lines.append(f"- Python: {', '.join(f'`{name}`' for name in spec.packages.python)}")
        if spec.packages.typescript:
            lines.append(f"- TypeScript: {', '.join(f'`{name}`' for name in spec.packages.typescript)}")
        if spec.protocol_tools:
            lines.append(f"- Its tools' action classes: {', '.join(f'`protocol-tools/{t}.yaml`' for t in spec.protocol_tools)}")
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
    "PROTOCOL_CATALOGUE",
    "AppspecBlock",
    "ProtocolLayer",
    "ProtocolPackages",
    "ProtocolSpec",
    "ProtocolStatus",
    "get_protocol",
    "json_schema",
    "load_protocols",
    "protocol_of_block",
    "protocols_problems",
    "reference_text",
    "schema_text",
]
