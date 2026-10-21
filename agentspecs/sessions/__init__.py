# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The session file (MH-12): ``datalayer-session/1``.

A session — one conversation of one person with one application's agent,
kept in the application's record — travels as a JSONL file whose first line
is the session (``record_type: session``) and whose other lines are its
record's entries in order (``record_type: entry``), redacted. A team
session's file is the team line (``record_type: team_session``: the
execution, the team, the seats in order with each seat's session uid)
followed by each seat's session line and entries. The file is imported as
a *new* session whose author is the importer; it never carries a credential,
a signed user, a runtime's address or a file's bytes.

One spec, ``sessions/datalayer-session-1.yaml``: the format's id, its caps,
the states, the kinds an entry may carry, the redaction rules by name and
the sentences a reader refuses a file in — the same words on every surface
(the runtime, ``loop``, the chat, agent-teams), generated into each by
agent-runtimes' ``make specs``. The models here validate one line at a time
(:func:`parse_line`); a line that is not one of the three, an entry of a
kind the record does not have, an entry without ``at``, a team line without
its seats, a file of another version — each is refused in the spec's
sentence, never read as a default.

``python -m agentspecs.sessions`` writes the JSON Schema beside the spec and
the reference page of the documentation.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

_ROOT = Path(__file__).resolve().parent

#: The format spec.
SPEC_PATH = _ROOT / "datalayer-session-1.yaml"

#: Where the JSON Schema is kept, beside the spec.
SCHEMA_PATH = _ROOT / "session-file.schema.json"

#: Where the reference page is kept in the documentation site, when the checkout has one.
REFERENCE_PATH = _ROOT.parent.parent / "docs" / "docs" / "sessions" / "index.md"

#: A session's uid: 8 to 128 letters, digits, hyphens or underscores, as the runtime says it.
SESSION_UID = re.compile(r"^[A-Za-z0-9_-]{8,128}$")

#: A title at most this long (MH-43).
TITLE_LIMIT = 200


class SessionFileError(ValueError):
    """A session file refused, said in the spec's sentence."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RedactionRule(_Strict):
    """One rule redaction applies at export, by name."""

    id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class FormatCaps(_Strict):
    """What a reader refuses a file over."""

    max_bytes: int = Field(gt=0)
    max_entries: int = Field(gt=0)


class SessionFormat(_Strict):
    """The format, as ``datalayer-session-1.yaml`` says it."""

    id: str
    version: str
    format: str = Field(pattern=r"^datalayer-session/[1-9][0-9]*$")
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    extension: str = Field(min_length=1)
    caps: FormatCaps
    states: List[str] = Field(min_length=1)
    entry_kinds: List[str] = Field(min_length=1)
    redaction_rules: List[RedactionRule] = Field(min_length=1)
    refusals: Dict[str, str]

    @field_validator("entry_kinds", "states")
    @classmethod
    def _each_once(cls, values: List[str]) -> List[str]:
        if len(set(values)) != len(values):
            raise ValueError("each is named once")
        return values


def load_format(path: Path = SPEC_PATH) -> SessionFormat:
    """The format spec, validated."""
    return SessionFormat.model_validate(yaml.safe_load(path.read_text()) or {})


#: The format.
SESSION_FORMAT: SessionFormat = load_format()

#: ``datalayer-session/1``.
FORMAT = SESSION_FORMAT.format

#: The states of a session, as the record says them.
STATES = tuple(SESSION_FORMAT.states)

#: The kinds an entry line may carry.
ENTRY_KINDS = tuple(SESSION_FORMAT.entry_kinds)

#: The redaction rules, by id.
REDACTION_RULES = tuple(rule.id for rule in SESSION_FORMAT.redaction_rules)

#: The caps.
MAX_BYTES = SESSION_FORMAT.caps.max_bytes
MAX_ENTRIES = SESSION_FORMAT.caps.max_entries

#: The refusal sentences, by name; ``refusal(name, **facts)`` fills one in.
REFUSALS = dict(SESSION_FORMAT.refusals)


def refusal(name: str, **facts: Any) -> str:
    """The spec's sentence for a refusal, its facts filled in."""
    return REFUSALS[name].format(**facts)


class SessionState(str, Enum):
    """A session's state."""

    OPEN = "open"
    PAUSED = "paused"
    ENDED = "ended"


class Owner(_Strict):
    """Who a session is: a uid, never a handle (a handle is the target's to resolve)."""

    uid: str = Field(min_length=1)


class SessionApp(_Strict):
    """The application a session is of, and the version it was had on."""

    id: str = Field(min_length=1)
    version: int = Field(ge=0)


class ForkedFrom(_Strict):
    """A clone's source: the session, and the turn it was cut at."""

    uid: str = Field(min_length=1)
    at_turn: int = Field(ge=0)


class ImportedFrom(_Strict):
    """An import's source: the file's digest, when and by whom it was exported."""

    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    exported_at: str = Field(min_length=1)
    exported_by: Owner


class Lineage(_Strict):
    """Where a session came from: both keys said, each ``null`` when it did not."""

    forked_from: Optional[ForkedFrom]
    imported_from: Optional[ImportedFrom]


class TeamForkedFrom(_Strict):
    """A team session clone's source: the run."""

    execution_id: str = Field(min_length=1)


class TeamLineage(_Strict):
    """Where a team session came from."""

    forked_from: Optional[TeamForkedFrom]
    imported_from: Optional[ImportedFrom]


class SessionLine(_Strict):
    """The first line: the session."""

    record_type: str = Field(pattern=r"^session$")
    format: str = Field(pattern=r"^datalayer-session/1$")
    uid: str
    app: SessionApp
    agent: str = Field(min_length=1, description="The agentspec bound to it when exported")
    harness: Optional[str] = Field(description="Its harness when the agent is one; null otherwise")
    owner: Owner
    state: SessionState
    turns: int = Field(ge=0, description="The person's turns in the file: up to the last complete one")
    title: str = Field(max_length=TITLE_LIMIT)
    archived: bool
    lineage: Lineage
    kinds: List[str] = Field(
        description="The kinds the application's record keeps: what is in the file",
        json_schema_extra={"items": {"enum": list(ENTRY_KINDS), "type": "string"}},
    )
    entries: int = Field(ge=0, description="How many entry lines follow")
    exported_at: str = Field(min_length=1)
    exported_by: Owner
    redactions: int = Field(ge=0, description="How many values redaction replaced or dropped")

    @field_validator("uid")
    @classmethod
    def _a_uid(cls, value: str) -> str:
        if not SESSION_UID.fullmatch(value):
            raise ValueError("a session's uid is 8 to 128 letters, digits, hyphens or underscores")
        return value

    @field_validator("kinds")
    @classmethod
    def _known_kinds(cls, values: List[str]) -> List[str]:
        unknown = [kind for kind in values if kind not in ENTRY_KINDS]
        if unknown:
            raise ValueError(f"kinds the record does not have: {', '.join(unknown)}")
        return values


class EntryLine(_Strict):
    """One entry of the record, as the record holds it, redacted."""

    record_type: str = Field(pattern=r"^entry$")
    kind: str = Field(json_schema_extra={"enum": list(ENTRY_KINDS)})
    at: str = Field(min_length=1, description="When it was recorded, ISO 8601")
    summary: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("kind")
    @classmethod
    def _a_kind(cls, value: str) -> str:
        if value not in ENTRY_KINDS:
            raise ValueError(f"the record does not have the kind {value!r}: one of {', '.join(ENTRY_KINDS)}")
        return value


class TeamSeat(_Strict):
    """One seat of a team session, with its session."""

    id: str = Field(min_length=1)
    session_uid: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    harness: Optional[str]


class TeamSpecRef(_Strict):
    """The team spec a run was of."""

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)


class TeamLine(_Strict):
    """The first line of a team session's file: the run, then each seat's session follows."""

    record_type: str = Field(pattern=r"^team_session$")
    format: str = Field(pattern=r"^datalayer-session/1$")
    execution_id: str = Field(min_length=1)
    team: TeamSpecRef
    owner: Owner
    state: SessionState
    seats: List[TeamSeat] = Field(description="In order, each with its session uid; never empty")
    lineage: TeamLineage
    exported_at: str = Field(min_length=1)
    exported_by: Owner
    redactions: int = Field(ge=0)

    @model_validator(mode="after")
    def _seats(self) -> "TeamLine":
        if not self.seats:
            raise ValueError(REFUSALS["team_without_seats"])
        seen = set()
        for seat in self.seats:
            if seat.id in seen:
                raise ValueError(f"the seat {seat.id!r} is named twice")
            seen.add(seat.id)
        return self


Line = Union[SessionLine, EntryLine, TeamLine]

_LINES = {"session": SessionLine, "entry": EntryLine, "team_session": TeamLine}


def _said(error: ValidationError) -> str:
    first = error.errors()[0]
    where = ".".join(str(part) for part in first.get("loc", ()))
    message = str(first.get("msg", "")).removeprefix("Value error, ")
    return f"{where}: {message}" if where else message


def parse_line(value: Any, *, line: int = 1) -> Line:
    """One line of a file, as its ``record_type`` says, validated.

    Raises
    ------
    SessionFileError
        In the spec's sentence: a line that is not an object or not one of
        the three, a first line without its format or of another version, an
        entry of a kind the record does not have or without ``at``, a team
        line without seats — and any other field refused, named.
    """
    if not isinstance(value, dict):
        raise SessionFileError(refusal("not_a_line", line=line, record_type=type(value).__name__))
    record_type = value.get("record_type")
    model = _LINES.get(str(record_type))
    if model is None:
        if line == 1:
            raise SessionFileError(refusal("unversioned"))
        raise SessionFileError(refusal("not_a_line", line=line, record_type=record_type))
    if model is not EntryLine:
        fmt = value.get("format")
        if not fmt:
            raise SessionFileError(refusal("unversioned"))
        if fmt != FORMAT:
            raise SessionFileError(refusal("other_version", format=fmt))
    if model is EntryLine:
        kind = value.get("kind")
        if kind not in ENTRY_KINDS:
            raise SessionFileError(refusal("unknown_kind", line=line, kind=kind, kinds=", ".join(ENTRY_KINDS)))
        if not str(value.get("at") or "").strip():
            raise SessionFileError(refusal("entry_without_at", line=line))
    try:
        return model.model_validate(value)
    except ValidationError as invalid:
        raise SessionFileError(f"Line {line} is refused: {_said(invalid)}.") from None


def within_caps(size: int, entries: int) -> Optional[str]:
    """The sentence that refuses a file over the caps, or ``None``."""
    if size > MAX_BYTES or entries > MAX_ENTRIES:
        return refusal("too_large", entries=f"{entries:,}".replace(",", " "), megabytes=round(size / (1024 * 1024)))
    return None


def json_schema() -> Dict[str, object]:
    """The JSON Schema of a line of the file: one of the three."""
    defs: Dict[str, Any] = {}
    one_of = []
    for name, model in (("SessionLine", SessionLine), ("EntryLine", EntryLine), ("TeamLine", TeamLine)):
        schema = model.model_json_schema(ref_template="#/$defs/{model}")
        defs.update(schema.pop("$defs", {}))
        defs[name] = schema
        one_of.append({"$ref": f"#/$defs/{name}"})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://agentspecs.datalayer.tech/schemas/session-file.json",
        "title": "SessionFileLine",
        "description": f"One line of a {FORMAT} file: the session, the team session, or an entry.",
        "oneOf": one_of,
        "$defs": defs,
    }


def schema_text() -> str:
    """The JSON Schema as it is written to :data:`SCHEMA_PATH`."""
    return json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"


def _cell(text: object) -> str:
    words = " ".join(str(text if text is not None else "").split())
    return words.replace("|", "\\|").replace("<", "&lt;").replace("{", "\\{").replace("}", "\\}")


def reference_text() -> str:
    """The reference page: the format, its lines, the kinds, the rules and the refusals."""
    spec = SESSION_FORMAT
    lines = [
        "<!-- Generated by `python -m agentspecs.sessions` from sessions/datalayer-session-1.yaml. Do not edit. -->",
        "",
        "# Session files",
        "",
        f"`{spec.format}`: {_cell(spec.description)}",
        "",
        f"JSONL (`{spec.media_type}`, `{spec.extension}`). The first line is the session",
        "(`record_type: session`) — or, for a team session, the team line",
        "(`record_type: team_session`) followed by each seat's session line — and every",
        "other line is one entry of the record (`record_type: entry`), in order, redacted.",
        f"A file over {spec.caps.max_entries:,} entries or {spec.caps.max_bytes // (1024 * 1024)} MB is refused with its counts.",
        "The file never carries a credential, a signed user, a runtime's address or a",
        "file's bytes; it is imported as a new session whose author is the importer.",
        "",
        "## States",
        "",
        ", ".join(f"`{state}`" for state in spec.states),
        "",
        "## Entry kinds",
        "",
        ", ".join(f"`{kind}`" for kind in spec.entry_kinds),
        "",
        "## Redaction rules",
        "",
        "| Rule | What it does |",
        "| --- | --- |",
    ]
    for rule in spec.redaction_rules:
        lines.append(f"| `{rule.id}` | {_cell(rule.description)} |")
    lines += ["", "## Refusals", "", "| Name | Sentence |", "| --- | --- |"]
    for name, sentence in spec.refusals.items():
        lines.append(f"| `{name}` | {_cell(sentence)} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    SCHEMA_PATH.write_text(schema_text())
    if REFERENCE_PATH.parent.parent.is_dir():
        REFERENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        REFERENCE_PATH.write_text(reference_text())


__all__ = [
    "ENTRY_KINDS",
    "FORMAT",
    "MAX_BYTES",
    "MAX_ENTRIES",
    "REDACTION_RULES",
    "REFERENCE_PATH",
    "REFUSALS",
    "SCHEMA_PATH",
    "SESSION_FORMAT",
    "SESSION_UID",
    "SPEC_PATH",
    "STATES",
    "TITLE_LIMIT",
    "EntryLine",
    "ForkedFrom",
    "ImportedFrom",
    "Lineage",
    "Line",
    "Owner",
    "SessionApp",
    "SessionFileError",
    "SessionFormat",
    "SessionLine",
    "SessionState",
    "TeamForkedFrom",
    "TeamLine",
    "TeamLineage",
    "TeamSeat",
    "TeamSpecRef",
    "json_schema",
    "load_format",
    "main",
    "parse_line",
    "reference_text",
    "refusal",
    "schema_text",
    "within_caps",
]
