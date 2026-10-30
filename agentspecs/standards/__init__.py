# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Standard specifications.

A *standard* is what a conformance report answers: its version, its domains,
and its controls — each with an id and a title as the standard's own pages
say them, mandatory or optional, retired or not, the cadence it carries, the
evidence items it takes (by kind: documentation, config, logs, evals, report,
demonstration) and its crosswalk references to other frameworks. One YAML per
standard under ``standards/``: ``aiuc-1`` (the first) read from
standard.aiuc-1.com's six domain pages at its October 15, 2026 release, and
``iso-42001`` read through AIUC-1's crosswalk, each clause naming the AIUC-1
controls that cover it and how far (``covered_by``, ``coverage``).

**The version is tracked, never applied silently**: a spec says
the standard's ``version``, when that version was ``released_on``, when the
next is due (``next_release_on``) and the day it was ``read_on``;
:func:`version_notice` says, in a sentence, when a newer release is due or
has been published since the spec was read, and the test in
``tests/test_standards.py`` holds the spec's control ids and titles to the
published index (``aiuc-1.index.txt``, the control lines of the standard's
``llms.txt``; the live page when the network allows).

**The organization's controls** start from the templates under
``standards/templates/``: one Markdown text per control a person must write
and sign (the failure plans, acceptable use, processing locations, regulatory
compliance, the data policies, the risk taxonomy, vendor due diligence), with
``{{ }}`` fields the Studio fills; :func:`template_text` renders one with
what the catalogue knows — the model providers for E006, where Datalayer runs
for E011.

The Shield's evidence map (``agent_shield.conformance``) reads this catalogue
and keeps no copy of it. ``python -m agentspecs.standards`` writes the JSON
Schema beside the specs and the reference page of the documentation.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ROOT = Path(__file__).resolve().parent.parent

#: The standard specs.
STANDARDS_DIR = _ROOT / "standards"

#: Where the JSON Schema is kept, beside the specs.
SCHEMA_PATH = STANDARDS_DIR / "standard.schema.json"

#: The templates of the organization's controls.
TEMPLATES_DIR = STANDARDS_DIR / "templates"

#: The published index of AIUC-1's controls, as its ``llms.txt`` lists them.
AIUC1_INDEX_PATH = STANDARDS_DIR / "aiuc-1.index.txt"

#: Where the reference page is kept in the documentation site, when the checkout has one.
REFERENCE_PATH = _ROOT.parent / "docs" / "docs" / "standards" / "index.md"

#: The evidence kinds a standard names (AIUC-1's five, and a report the organization records).
EVIDENCE_KINDS = ("documentation", "config", "logs", "evals", "report", "demonstration", "retired")

_ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")
_CONTROL_ID = re.compile(r"^[A-Z]?\.?[A-Z0-9][A-Za-z0-9.]{0,15}$")
_VERSION = re.compile(r"^\d{4}(\.\d+)?$")


class StandardError(ValueError):
    """A standard the catalogue refuses, said in a sentence."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


Application = Literal["mandatory", "optional"]
Required = Literal["core", "supplemental"]
Coverage = Literal["full", "partial", "none"]
EvidenceKind = Literal["documentation", "config", "logs", "evals", "report", "demonstration", "retired"]


class Domain(_Strict):
    """One domain (AIUC-1 says *principle*; ISO 42001 a clause group)."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    url: str = Field(default="", description="The domain's page, https")


class EvidenceItem(_Strict):
    """One evidence item of a control, as the standard lists it (``D003.1 Config: …``)."""

    id: str = Field(min_length=1, description="The standard's id of the item, e.g. D003.1")
    kind: EvidenceKind
    title: str = Field(min_length=1)
    required: Required = Field(description="core: must be demonstrated; supplemental: opted into")
    category: str = Field(default="", description="The standard's evidence category, e.g. technical-implementation")
    locations: List[str] = Field(default_factory=list, description="Where the standard typically finds it")
    description: str = Field(default="")


class Activity(_Strict):
    """One control activity, as the standard words it."""

    required: Required
    activity: str = Field(min_length=1)


class Control(_Strict):
    """One control (AIUC-1 says *requirement*; ISO 42001 a clause)."""

    id: str = Field(description="The standard's own id, e.g. D003, or an ISO clause such as A.9.4")
    title: str = Field(min_length=1, description="The standard's own title, verbatim")
    domain: str = Field(min_length=1, description="The id of its domain")
    application: Application
    retired: bool = Field(default=False, description="Retired in a release; kept so an older certification still reads")
    retired_in: Optional[str] = Field(default=None, description="The release that retired it")
    url: str = Field(default="", description="Its page, https")
    cadence_months: Optional[int] = Field(
        default=None, ge=1, description="How often it is demonstrated again: 3, 6 or 12 months; none when retired"
    )
    type: Optional[Literal["preventative", "detective"]] = None
    summary: str = Field(default="")
    keywords: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list, description="The agent capabilities it applies to")
    activities: List[Activity] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    crosswalks: Dict[str, List[str]] = Field(
        default_factory=dict, description="Framework id → the references of that framework this control maps to"
    )
    covered_by: Optional[List[str]] = Field(
        default=None, description="For a standard that maps to another: that standard's controls covering this one"
    )
    coverage: Optional[Coverage] = Field(
        default=None, description="The crosswalk's gap analysis as published: full (no gap), partial, none (a full gap)"
    )
    coverage_note: str = Field(default="")

    @field_validator("id")
    @classmethod
    def _an_id(cls, value: str) -> str:
        if not _CONTROL_ID.fullmatch(value):
            raise ValueError(f"{value!r} is not a control id")
        return value

    @field_validator("url")
    @classmethod
    def _https(cls, value: str) -> str:
        if value and not value.startswith("https://"):
            raise ValueError("a control's page is read at an https address")
        return value

    @model_validator(mode="after")
    def _cadence_unless_retired(self) -> "Control":
        if self.retired:
            if self.cadence_months is not None:
                raise ValueError(f"the retired control {self.id} carries no cadence")
            if not self.retired_in:
                raise ValueError(f"the retired control {self.id} says the release that retired it")
        elif self.cadence_months is None:
            raise ValueError(f"the control {self.id} says its cadence in months")
        if (self.covered_by is None) != (self.coverage is None):
            raise ValueError(f"the control {self.id} says both `covered_by` and `coverage`, or neither")
        # `coverage` is the crosswalk's own gap analysis, kept as published: a clause the
        # certification process itself answers is "full" with no control named, and a clause
        # a related control only touches may be "none" with that control named.
        return self

    @property
    def mandatory(self) -> bool:
        return self.application == "mandatory" and not self.retired


class StandardSpec(_Strict):
    """One standard."""

    id: str = Field(description="Its id, the file's name")
    version: str = Field(description="The standard's version: AIUC-1's quarter (2026.4), ISO's year (2023)")
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    enabled: bool = True
    tags: List[str] = Field(default_factory=list)
    published_by: str = Field(min_length=1)
    url: str = Field(min_length=1, description="Where the standard is published, https")
    released_on: date = Field(description="When this version was released")
    next_release_on: Optional[date] = Field(default=None, description="When the next version is due; none when not scheduled")
    read_on: date = Field(description="The day the spec was written from the published pages")
    read_from: str = Field(default="", description="Where it was read when not at `url`")
    certificate_valid_months: int = Field(ge=1, description="How long a certification against it holds")
    evidence_kinds: Dict[str, str] = Field(description="Each evidence kind the standard names, in a sentence")
    frameworks: Dict[str, str] = Field(default_factory=dict, description="Framework id → its name, for the crosswalks")
    maps_to: Optional[str] = Field(default=None, description="The standard its controls are covered by (iso-42001 → aiuc-1)")
    domains: List[Domain]
    controls: List[Control]

    @field_validator("id")
    @classmethod
    def _an_id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError(f"{value!r} is not a standard id: lower-case letters, digits and hyphens")
        return value

    @field_validator("version")
    @classmethod
    def _a_version(cls, value: str) -> str:
        if not _VERSION.fullmatch(value):
            raise ValueError(f"{value!r} is not a standard's version: a year, or a year and a quarter (2026.4)")
        return value

    @field_validator("url", "read_from")
    @classmethod
    def _https(cls, value: str) -> str:
        if value and not value.startswith("https://"):
            raise ValueError("a standard is read at an https address")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "StandardSpec":
        domains = {d.id for d in self.domains}
        seen: set[str] = set()
        for control in self.controls:
            if control.id in seen:
                raise ValueError(f"the control {control.id} is listed twice")
            seen.add(control.id)
            if control.domain not in domains:
                raise ValueError(f"the control {control.id} is in the domain {control.domain!r}, which the standard does not list")
            for framework in control.crosswalks:
                if framework not in self.frameworks:
                    raise ValueError(f"the control {control.id} crosswalks to {framework!r}, which `frameworks` does not name")
            for item in control.evidence:
                if item.kind != "retired" and item.kind not in self.evidence_kinds:
                    raise ValueError(f"the evidence {item.id} is of the kind {item.kind!r}, which the standard does not name")
            if (control.covered_by is not None) != (self.maps_to is not None):
                raise ValueError(
                    f"the control {control.id} {'says' if control.covered_by is not None else 'does not say'} what covers it, "
                    f"but the standard {'maps to nothing' if self.maps_to is None else 'maps to ' + self.maps_to}"
                )
        if self.read_on < self.released_on:
            raise ValueError("a standard cannot be read before its version was released")
        return self

    def control(self, control_id: str) -> Control:
        for found in self.controls:
            if found.id == control_id:
                return found
        raise StandardError(f"{self.name} has no control {control_id!r}")

    @property
    def mandatory_controls(self) -> List[Control]:
        return [c for c in self.controls if c.mandatory]


def load_standards(directory: Path = STANDARDS_DIR) -> Dict[str, StandardSpec]:
    """Every standard of a directory, validated, by id; each file named for its id."""
    found: Dict[str, StandardSpec] = {}
    for path in sorted(directory.glob("*.yaml")):
        spec = StandardSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        if spec.id != path.stem:
            raise StandardError(f"{path.name}: the file is named for {path.stem!r}, the spec says {spec.id!r}")
        found[spec.id] = spec
    for spec in found.values():
        if spec.maps_to is not None:
            target = found.get(spec.maps_to)
            if target is None:
                raise StandardError(f"{spec.id}: maps to {spec.maps_to!r}, which is not in the catalogue")
            known = {c.id for c in target.controls}
            for control in spec.controls:
                for other in control.covered_by or []:
                    if other not in known:
                        raise StandardError(f"{spec.id}: the control {control.id} is covered by {other!r}, which {target.id} has not")
    return found


#: Every standard of the catalogue, by id.
STANDARD_CATALOGUE: Dict[str, StandardSpec] = load_standards()


def get_standard(standard_id: str) -> Optional[StandardSpec]:
    """A standard by id, or None."""
    return STANDARD_CATALOGUE.get(standard_id)


def version_notice(spec: StandardSpec, today: Optional[date] = None) -> Optional[str]:
    """When the standard has moved on since the spec was read, in a sentence; None while current.

    The notice is offered, never applied: the organization's version stays
    locked until a person takes the newer spec.
    """
    today = today or date.today()
    if spec.next_release_on is None:
        return None
    if today >= spec.next_release_on:
        return (
            f"{spec.name} published a release on {spec.next_release_on.isoformat()}; this catalogue holds "
            f"version {spec.version} (released {spec.released_on.isoformat()}, read {spec.read_on.isoformat()}). "
            "A newer spec can be taken; the version in force stays locked until then."
        )
    return None


# ---------------------------------------------------------------------------
# The published index
# ---------------------------------------------------------------------------

_INDEX_LINE = re.compile(r"^- \[([A-F]\d{3}): (.*)\]")


def published_index(text: str) -> Dict[str, str]:
    """The control ids and titles an ``llms.txt`` (or the stored snapshot) lists."""
    found: Dict[str, str] = {}
    for line in text.splitlines():
        match = _INDEX_LINE.match(line.strip())
        if match:
            found[match.group(1)] = match.group(2).strip()
    return found


def index_of(spec: StandardSpec) -> Dict[str, str]:
    """The spec's controls in the published index's words: retired ones carry the `[Retired]` mark."""
    return {c.id: (f"[Retired] {c.title}" if c.retired else c.title) for c in spec.controls}


def index_differences(spec: StandardSpec, published: Dict[str, str]) -> List[str]:
    """How the spec differs from a published index, in sentences; empty when it is in step."""
    own = index_of(spec)
    problems: List[str] = []
    for control_id in sorted(set(published) - set(own)):
        problems.append(f"{spec.name} publishes {control_id} ({published[control_id]}), which the spec does not carry")
    for control_id in sorted(set(own) - set(published)):
        problems.append(f"the spec carries {control_id} ({own[control_id]}), which {spec.name} no longer publishes")
    for control_id in sorted(set(own) & set(published)):
        if own[control_id] != published[control_id]:
            problems.append(f"{control_id}: the spec says {own[control_id]!r}, {spec.name} publishes {published[control_id]!r}")
    return problems


# ---------------------------------------------------------------------------
# The organization's controls: templates
# ---------------------------------------------------------------------------

#: The controls a person writes and signs, and the template each starts from.
TEMPLATES: Dict[str, str] = {
    "E001": "e001-failure-plan-security-breaches.md",
    "E002": "e002-failure-plan-harmful-outputs.md",
    "E003": "e003-failure-plan-hallucinations.md",
    "E010": "e010-acceptable-use.md",
    "E011": "e011-processing-locations.md",
    "E012": "e012-regulatory-compliance.md",
    "A001": "a001-input-data-policy.md",
    "A002": "a002-output-data-policy.md",
    "C001": "c001-risk-taxonomy.md",
    "E006": "e006-vendor-due-diligence.md",
}

#: How often each of them is reviewed, in months (the standard's cadence for the control).
_FIELD = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def _providers_table() -> str:
    """The model providers the catalogue names, one row each, for E006."""
    from agentspecs.model_providers import list_model_providers  # noqa: PLC0415

    rows = ["| Provider | Hosting | Terms | Privacy | Data usage |", "| --- | --- | --- | --- | --- |"]
    for provider in sorted(list_model_providers(), key=lambda p: p.name):
        rows.append(
            f"| {provider.name} | {provider.hosting} | {provider.terms_url or '—'} | "
            f"{provider.privacy_url or '—'} | {provider.data_usage_url or '—'} |"
        )
    return "\n".join(rows)


#: Where Datalayer runs its managed service, in words (never a plane's internal name).
DATALAYER_PROCESSING_LOCATIONS = (
    "| Datalayer's managed service | OVH, Beauharnois (BHS), Québec, Canada | Runtimes, the record, IAM, Contents, the observability ingest |\n"
    "| Datalayer's staging plane | OVH, Beauharnois (BHS), Québec, Canada | Pre-production runtimes; the same services |"
)


def template_text(control_id: str, **fields: str) -> str:
    """The starting text of the organization's document for a control, its fields filled.

    What the catalogue knows is filled here — the model providers (E006),
    where Datalayer runs (E011); what only the organization knows stays a
    ``{{ field }}`` the Studio asks for, and a document is signed only once
    none is left.
    """
    if control_id not in TEMPLATES:
        raise StandardError(f"{control_id} is not a control the organization writes; one of {', '.join(TEMPLATES)}")
    text = (TEMPLATES_DIR / TEMPLATES[control_id]).read_text(encoding="utf-8")
    known = {"model_providers": _providers_table, "datalayer_locations": lambda: DATALAYER_PROCESSING_LOCATIONS}
    for name, value in fields.items():
        text = text.replace("{{ " + name + " }}", value)
    for name, fill in known.items():
        text = text.replace("{{ " + name + " }}", fill())
    return text


def unfilled_fields(text: str) -> List[str]:
    """The ``{{ field }}`` names a document still carries: it cannot be signed while any is left."""
    return sorted({match.group(1) for match in _FIELD.finditer(text)})


# ---------------------------------------------------------------------------
# Schema and reference
# ---------------------------------------------------------------------------


def json_schema() -> Dict[str, object]:
    """The JSON Schema of a standard spec."""
    schema = StandardSpec.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://agentspecs.datalayer.tech/schemas/standard.json"
    schema["title"] = "Standard"
    return schema


def schema_text() -> str:
    return json.dumps(json_schema(), indent=2, sort_keys=True) + "\n"


def _cell(text: object) -> str:
    words = " ".join(str(text if text is not None else "").split())
    return words.replace("|", "\\|").replace("<", "&lt;").replace("{", "\\{").replace("}", "\\}")


def reference_text() -> str:
    """The reference page: every standard, its domains and controls."""
    lines = [
        "<!-- Generated by `python -m agentspecs.standards` from standards/*.yaml. Do not edit. -->",
        "",
        "# Standards",
        "",
        "What a conformance report answers: a standard's version,",
        "domains and controls, each with the evidence kinds it takes, its cadence and its crosswalks,",
        "one spec each under `agentspecs/standards/`. The Shield's evidence map",
        "(`agent_shield.conformance`) reads them and gives each control one of five statuses; the",
        "standard's version is tracked and offered, never applied silently.",
        "",
        "| Standard | Id | Version | Released | Next release | Read on | Controls | Mandatory | Retired |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for spec in sorted(STANDARD_CATALOGUE.values(), key=lambda s: s.id):
        lines.append(
            f"| [{_cell(spec.name)}]({spec.url}) | `{spec.id}` | {spec.version} | {spec.released_on.isoformat()} "
            f"| {spec.next_release_on.isoformat() if spec.next_release_on else 'not scheduled'} | {spec.read_on.isoformat()} "
            f"| {len(spec.controls)} | {len(spec.mandatory_controls)} | {sum(1 for c in spec.controls if c.retired)} |"
        )
    for spec in sorted(STANDARD_CATALOGUE.values(), key=lambda s: s.id):
        lines += ["", f"## {spec.name} (`{spec.id}`)", "", " ".join(spec.description.split()), ""]
        lines.append(f"- Published by {_cell(spec.published_by)}; a certification holds {spec.certificate_valid_months} months.")
        lines.append(f"- Evidence kinds: {', '.join(f'**{k}** ({_cell(v)})' for k, v in spec.evidence_kinds.items())}.")
        if spec.frameworks:
            lines.append(f"- Crosswalks to: {', '.join(_cell(v) for v in spec.frameworks.values())}.")
        if spec.maps_to:
            lines.append(f"- Each control names the `{spec.maps_to}` controls that cover it, and how far.")
        for domain in spec.domains:
            controls = [c for c in spec.controls if c.domain == domain.id]
            if not controls:
                continue
            lines += ["", f"### {domain.id}. {_cell(domain.name)}", ""]
            if spec.maps_to:
                lines += ["| Clause | Title | Covered by | Coverage |", "| --- | --- | --- | --- |"]
                for control in controls:
                    lines.append(
                        f"| {control.id} | {_cell(control.title)} | {', '.join(control.covered_by or []) or '—'} "
                        f"| {control.coverage}{(': ' + _cell(control.coverage_note)) if control.coverage_note else ''} |"
                    )
            else:
                lines += ["| Control | Title | Application | Cadence | Evidence |", "| --- | --- | --- | --- | --- |"]
                for control in controls:
                    title = f"[{_cell(control.title)}]({control.url})" if control.url else _cell(control.title)
                    application = "retired" if control.retired else control.application
                    cadence = f"every {control.cadence_months} months" if control.cadence_months else "—"
                    evidence = ", ".join(f"{e.id} ({e.kind})" for e in control.evidence if e.kind != "retired") or "—"
                    lines.append(f"| {control.id} | {title} | {application} | {cadence} | {evidence} |")
    lines += [
        "",
        "## The organization's controls",
        "",
        "The controls a person writes and signs start from a template under `standards/templates/`"
        ", with what the catalogue knows filled in:",
        "",
    ]
    for control_id, name in TEMPLATES.items():
        lines.append(f"- `{control_id}`: `{name}`")
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
    "AIUC1_INDEX_PATH",
    "DATALAYER_PROCESSING_LOCATIONS",
    "EVIDENCE_KINDS",
    "STANDARD_CATALOGUE",
    "TEMPLATES",
    "TEMPLATES_DIR",
    "Activity",
    "Control",
    "Domain",
    "EvidenceItem",
    "StandardError",
    "StandardSpec",
    "get_standard",
    "index_differences",
    "index_of",
    "json_schema",
    "load_standards",
    "published_index",
    "reference_text",
    "schema_text",
    "template_text",
    "unfilled_fields",
    "version_notice",
]
