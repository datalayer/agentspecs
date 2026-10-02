# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Track specifications.

A *Track* is the durable record of an Op or a Cog execution: what happened,
under which context, which Cogs were invoked, which Guards ran, which Gates
were passed or failed, what sources were consulted, who approved, and what
was produced. The idea, and the words, are the Intelligence Hub whitepaper's
(section 5.3).

A Track spec is not a record: it says what a record has to **include**, for
how long it is **retained**, and who may **read** it. It is a policy for
evidence, which an Op names so that what is kept is decided before the Op
runs rather than after something went wrong.

Unlike Frames, Cogs, Ops and Guards, a Track is not exchanged: it stays under
the governance boundary of the Hub that produced it. Evidence is not for sale.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from ..guards import id_of, load_raw


class TrackError(ValueError):
    """A Track that cannot be used — named plainly."""


class TrackItem(str, Enum):
    """What a Track may keep (section 5.3)."""

    OP = "op"
    FRAMES_USED = "frames_used"
    COGS_INVOKED = "cogs_invoked"
    INPUT_DATA = "input_data"
    SOURCE_DOCUMENTS = "source_documents"
    MODEL_VERSIONS = "model_versions"
    CONFIGURATION = "configuration"
    GUARD_RESULTS = "guard_results"
    GATE_DECISIONS = "gate_decisions"
    HUMAN_APPROVALS = "human_approvals"
    HUMAN_EDITS = "human_edits"
    FINAL_OUTPUT = "final_output"
    ACTIONS_TAKEN = "actions_taken"
    TIMESTAMPS = "timestamps"
    USER_IDENTITY = "user_identity"
    PERMISSIONS = "permissions"
    ENVIRONMENT = "environment"
    MEMORY_LINKS = "memory_links"


#: What every Track keeps: without these, a record says neither what ran nor what it decided.
REQUIRED_ITEMS = (
    TrackItem.OP,
    TrackItem.GUARD_RESULTS,
    TrackItem.GATE_DECISIONS,
    TrackItem.FINAL_OUTPUT,
    TrackItem.TIMESTAMPS,
)

_RETENTION = re.compile(r"^(?P<count>[1-9]\d*)_(?P<unit>day|days|month|months|year|years)$")
_DAYS = {"day": 1, "month": 30, "year": 365}


def retention_days(retain_for: str) -> int:
    """A retention as days: `90_days`, `18_months`, `7_years`."""
    matched = _RETENTION.match(retain_for.strip())
    if matched is None:
        raise TrackError(f"cannot read the retention {retain_for!r}: write `90_days`, `18_months` or `7_years`")
    return int(matched.group("count")) * _DAYS[matched.group("unit").rstrip("s")]


class TrackSpec(BaseModel):
    """Specification for a Track: what a record includes, and for how long."""

    id: str = Field(..., description="Unique Track identifier")
    version: str = Field(default="0.0.1", description="Track spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What the record is for")
    retain_for: str = Field(
        ...,
        description="How long a record is kept: `90_days`, `18_months`, `7_years`",
    )
    include: List[TrackItem] = Field(..., description="What a record has to include")
    readers: List[str] = Field(
        default_factory=list,
        description="The roles that may read a record; empty means its Op's owner only",
    )
    redact: List[str] = Field(
        default_factory=list,
        description="Field patterns kept out of the record, e.g. `*Password*`",
    )
    feeds_memory: bool = Field(
        default=False,
        description="Whether corrections, overrides and failures are fed back to Organizational Memory",
    )
    exchangeable: bool = Field(
        default=False,
        description="Whether a record may leave the Hub that produced it. Evidence is not for sale: false.",
    )
    enabled: bool = Field(default=True, description="Whether an Op may name it today")
    tags: List[str] = Field(default_factory=list)
    icon: str = Field(default="log", description="Icon identifier")
    emoji: str = Field(default="\U0001f9fe", description="Emoji representation")

    @field_validator("retain_for")
    @classmethod
    def _is_a_retention(cls, retain_for: str) -> str:
        retention_days(retain_for)
        return retain_for.strip()

    @field_validator("include")
    @classmethod
    def _keeps_what_makes_a_record(cls, include: List[TrackItem]) -> List[TrackItem]:
        if len(set(include)) != len(include):
            raise ValueError("a Track includes an item once")
        missing = [item.value for item in REQUIRED_ITEMS if item not in include]
        if missing:
            raise ValueError(
                "a Track includes at least " + ", ".join(item.value for item in REQUIRED_ITEMS)
                + f"; missing: {', '.join(missing)}"
            )
        return include

    @property
    def retention_days(self) -> int:
        """The retention, as days."""
        return retention_days(self.retain_for)


def load_raw_tracks(directory: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Every Track YAML of a directory as plain data, by id."""
    return load_raw(directory or Path(__file__).parent)


def load_tracks(directory: Optional[Path] = None) -> Dict[str, TrackSpec]:
    """Every Track of a directory, validated."""
    return {identity: TrackSpec(**track) for identity, track in load_raw_tracks(directory).items()}


#: Every Track, by id.
TRACK_CATALOGUE: Dict[str, TrackSpec] = load_tracks()


def get_track(track_id: str) -> Optional[TrackSpec]:
    """A Track, by `id` or `id:version`, or None."""
    return TRACK_CATALOGUE.get(id_of(track_id))


def list_tracks() -> List[TrackSpec]:
    """Every Track."""
    return list(TRACK_CATALOGUE.values())


__all__ = [
    "REQUIRED_ITEMS",
    "TRACK_CATALOGUE",
    "TrackError",
    "TrackItem",
    "TrackSpec",
    "get_track",
    "list_tracks",
    "load_raw_tracks",
    "load_tracks",
    "retention_days",
]
