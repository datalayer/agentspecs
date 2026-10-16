# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The standards catalogue (SH-60, SH-66): AIUC-1 at its
October 15, 2026 release, held to the published index; ISO/IEC 42001 through the crosswalk."""

from __future__ import annotations

import json
import pathlib
import socket
import urllib.request
from datetime import date

import pytest
import yaml

from agentspecs import standards

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"
LIVE_INDEX = "https://standard.aiuc-1.com/llms.txt"


def test_the_catalogue_holds_aiuc_1_and_iso_42001():
    assert set(standards.STANDARD_CATALOGUE) == {"aiuc-1", "iso-42001"}
    aiuc = standards.get_standard("aiuc-1")
    assert aiuc.version == "2026.4"
    assert aiuc.released_on == date(2026, 10, 15) and aiuc.next_release_on == date(2027, 1, 15)
    assert [d.id for d in aiuc.domains] == ["A", "B", "C", "D", "E", "F"]
    by_domain = {d: sum(1 for c in aiuc.controls if c.domain == d) for d in "ABCDEF"}
    assert by_domain == {"A": 9, "B": 10, "C": 12, "D": 4, "E": 18, "F": 2}
    assert len(aiuc.controls) == 55


def test_the_q4_2026_release_is_read_as_published():
    aiuc = standards.get_standard("aiuc-1")
    retired = sorted(c.id for c in aiuc.controls if c.retired)
    assert retired == ["C011", "C012", "D002", "E007", "E014"]
    for control in aiuc.controls:
        if control.retired:
            assert control.retired_in == "2026.4" and control.cadence_months is None
        else:
            assert control.cadence_months in (3, 6, 12)
    # The new third-party testing requirements of the release, quarterly.
    for control_id in ("A009", "B001", "C010", "D004", "E018"):
        control = aiuc.control(control_id)
        assert control.mandatory and control.cadence_months == 3
    d003 = aiuc.control("D003")
    assert d003.title == "Restrict unsafe tool calls"
    assert [e.id for e in d003.evidence] == ["D003.1", "D003.2", "D003.3", "D003.4", "D003.5"]
    # D003.4 human approval was elevated to a core control in this release.
    assert next(e for e in d003.evidence if e.id == "D003.4").required == "core"
    assert len(aiuc.mandatory_controls) == 42
    assert sum(len(c.evidence) for c in aiuc.controls) == 145


def test_every_control_carries_the_evidence_kinds_cadence_and_crosswalks_the_standard_publishes():
    aiuc = standards.get_standard("aiuc-1")
    for control in aiuc.controls:
        assert control.url.startswith("https://standard.aiuc-1.com/")
        for item in control.evidence:
            assert item.kind in standards.EVIDENCE_KINDS
            assert item.id.startswith(control.id + ".")
        for framework in control.crosswalks:
            assert framework in aiuc.frameworks
    # The crosswalks of SH-62 and SH-66 are carried on the controls.
    assert "Article 72: Post-Market Monitoring by Providers and Post-Market Monitoring Plan for High-Risk AI Systems" in aiuc.control("D003").crosswalks["eu-ai-act"]
    assert aiuc.control("D003").crosswalks["nist-ai-rmf"] == ["GOVERN 6.1: Third-party risk policies"]
    assert "ASI02 - Tool Misuse and Exploitation" in aiuc.control("D003").crosswalks["owasp-agentic-top-10"]
    assert any("iso-42001" in c.crosswalks for c in aiuc.controls)


def test_the_spec_is_held_to_the_published_index(monkeypatch):
    """The control ids and titles of the spec are the ones the standard publishes —
    the live index when the network allows, else the stored snapshot it was read from."""
    aiuc = standards.get_standard("aiuc-1")
    snapshot = standards.published_index(standards.AIUC1_INDEX_PATH.read_text(encoding="utf-8"))
    assert len(snapshot) == 55
    assert standards.index_differences(aiuc, snapshot) == []
    live = None
    try:
        with urllib.request.urlopen(LIVE_INDEX, timeout=5) as answer:  # noqa: S310 - the standard's own index
            live = answer.read().decode("utf-8")
    except (OSError, socket.timeout, ValueError):
        live = None
    if live is None:
        pytest.skip("the live index could not be read; the stored snapshot held")
    published = standards.published_index(live)
    assert len(published) >= 50, "the live index no longer lists the controls as the snapshot did"
    assert standards.index_differences(aiuc, published) == [], (
        "the standard has moved on since the spec was read: take the newer release"
    )


def test_a_difference_from_the_index_is_said_in_a_sentence():
    aiuc = standards.get_standard("aiuc-1")
    published = standards.index_of(aiuc)
    changed = {**published, "D003": "Restrict all tool calls", "G001": "A new control"}
    del changed["F002"]
    assert standards.index_differences(aiuc, changed) == [
        "AIUC-1 publishes G001 (A new control), which the spec does not carry",
        "the spec carries F002 (Prevent catastrophic misuse), which AIUC-1 no longer publishes",
        "D003: the spec says 'Restrict unsafe tool calls', AIUC-1 publishes 'Restrict all tool calls'",
    ]


def test_a_newer_release_is_offered_never_applied():
    aiuc = standards.get_standard("aiuc-1")
    assert standards.version_notice(aiuc, today=date(2026, 12, 1)) is None
    notice = standards.version_notice(aiuc, today=date(2027, 1, 15))
    assert notice.startswith("AIUC-1 published a release on 2027-01-15; this catalogue holds version 2026.4")
    assert notice.endswith("the version in force stays locked until then.")
    assert standards.version_notice(standards.get_standard("iso-42001"), today=date(2030, 1, 1)) is None


def test_iso_42001_maps_onto_aiuc_1_clause_by_clause():
    iso = standards.get_standard("iso-42001")
    assert iso.maps_to == "aiuc-1"
    assert len(iso.controls) == 70
    covered = {c.id: c for c in iso.controls}
    assert covered["4.1"].covered_by == ["C001", "E010"] and covered["4.1"].coverage == "partial"
    assert covered["4.2"].covered_by == [] and covered["4.2"].coverage == "none"
    assert covered["A.10.3"].covered_by == ["E006"] and covered["A.10.3"].coverage == "full"
    aiuc_ids = {c.id for c in standards.get_standard("aiuc-1").controls}
    for control in iso.controls:
        assert control.covered_by is not None and control.coverage is not None
        assert set(control.covered_by) <= aiuc_ids
        assert control.crosswalks == {"aiuc-1": control.covered_by}


def test_the_organizations_controls_start_from_templates():
    assert set(standards.TEMPLATES) == {"E001", "E002", "E003", "E010", "E011", "E012", "A001", "A002", "C001", "E006"}
    aiuc = standards.get_standard("aiuc-1")
    for control_id, name in standards.TEMPLATES.items():
        path = standards.TEMPLATES_DIR / name
        assert path.is_file()
        head = path.read_text(encoding="utf-8").split("---")[1]
        assert f"control: {control_id}" in head
        assert any(e.kind == "documentation" for e in aiuc.control(control_id).evidence)
    e006 = standards.template_text("E006", organization="Acme")
    assert "| Anthropic |" in e006 and "| OpenAI |" in e006 and "| Alibaba" in e006
    assert "{{ model_providers }}" not in e006 and "**Organization:** Acme" in e006
    e011 = standards.template_text("E011")
    assert "OVH, Beauharnois (BHS)" in e011 and "{{ datalayer_locations }}" not in e011
    assert "owner" in standards.unfilled_fields(e011) and "own_systems" in standards.unfilled_fields(e011)
    assert standards.unfilled_fields("nothing left") == []
    with pytest.raises(standards.StandardError, match="D003 is not a control the organization writes"):
        standards.template_text("D003")


def test_the_schema_and_the_reference_page_are_generated():
    assert json.loads(standards.SCHEMA_PATH.read_text()) == standards.json_schema()
    assert standards.REFERENCE_PATH.read_text() == standards.reference_text()


def test_a_spec_out_of_step_is_refused_in_a_sentence(tmp_path: pathlib.Path):
    good = yaml.safe_load((ROOT / "standards" / "aiuc-1.yaml").read_text())
    bad = {**good, "id": "bad", "controls": [{**good["controls"][0], "cadence_months": None}]}
    (tmp_path / "bad.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="the control A001 says its cadence in months"):
        standards.load_standards(tmp_path)
    retired = {**good, "id": "bad", "controls": [{**good["controls"][0], "retired": True, "cadence_months": 12}]}
    (tmp_path / "bad.yaml").write_text(yaml.safe_dump(retired))
    with pytest.raises(ValueError, match="the retired control A001 carries no cadence"):
        standards.load_standards(tmp_path)
    (tmp_path / "bad.yaml").write_text(yaml.safe_dump({**good, "id": "other"}))
    with pytest.raises(standards.StandardError, match="bad.yaml: the file is named for 'bad', the spec says 'other'"):
        standards.load_standards(tmp_path)
