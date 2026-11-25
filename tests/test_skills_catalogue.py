# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Skills: what a spec names is in the catalogue, with what a page shows of it.

A page that lists an agent's skills draws each one's icon, its name and its description
from the catalogue. A skill named by an agent with no spec of its own was drawn as its
bare id (``datalayer-memory-add``, 25 November 2026): no spec may name one the
catalogue does not have.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"

#: The kinds whose specs name skills, in a top-level ``skills`` list.
NAMING_KINDS = ("agents", "cogs", "frames", "fragments", "teams", "apps")


def _catalogue() -> dict[str, dict]:
    return {
        spec["id"]: spec
        for spec in (
            yaml.safe_load(path.read_text()) for path in sorted((ROOT / "skills").glob("*.yaml"))
        )
    }


def _bare(ref: object) -> str:
    """A skill reference without its version: ``crawl:0.0.1`` is ``crawl``."""
    raw = ref.get("id", "") if isinstance(ref, dict) else str(ref)
    return raw.split(":", 1)[0].strip()


def _references(spec: dict) -> list[str]:
    """Every skill reference of a spec, as written: its ``skills`` and its ``optional.skills``."""
    optional = (spec.get("optional") or {}).get("skills") or []
    return [
        ref.get("id", "") if isinstance(ref, dict) else str(ref)
        for ref in [*(spec.get("skills") or []), *optional]
    ]


def _named() -> dict[str, list[str]]:
    """Each skill id a spec names, with the specs that name it."""
    named: dict[str, list[str]] = {}
    for kind in NAMING_KINDS:
        for path in sorted((ROOT / kind).rglob("*.yaml")):
            spec = yaml.safe_load(path.read_text())
            if not isinstance(spec, dict):
                continue
            optional = (spec.get("optional") or {}).get("skills") or []
            for ref in [*(spec.get("skills") or []), *optional]:
                skill_id = _bare(ref)
                if skill_id:
                    named.setdefault(skill_id, []).append(f"{kind}/{path.name}")
    return named


def test_a_spec_file_is_named_after_its_id():
    for path in sorted((ROOT / "skills").glob("*.yaml")):
        assert yaml.safe_load(path.read_text())["id"] == path.stem


def test_every_skill_a_spec_names_is_in_the_catalogue():
    named = _named()
    # The memory skills and the identity skill among them: the ones that had no spec.
    assert {"datalayer-memory-add", "datalayer-whoami", "crawl"} <= set(named)
    catalogue = _catalogue()
    missing = {skill: where[:3] for skill, where in named.items() if skill not in catalogue}
    assert missing == {}


@pytest.mark.parametrize("skill_id", sorted(_catalogue()))
def test_a_skill_says_what_a_page_shows_of_it(skill_id):
    spec = _catalogue()[skill_id]
    name = str(spec.get("name") or "").strip()
    description = " ".join(str(spec.get("description") or "").split())
    # A name a person reads, never the id again.
    assert name and name != skill_id and name.lower() != skill_id.replace("-", " ")
    # One line of a menu: a sentence, not a paragraph, and not an instruction to the model.
    assert 20 <= len(description) <= 260
    assert "Use it when" not in description and "Use when" not in description
    # One way to load it.
    assert spec.get("module") or spec.get("package")
    assert spec.get("icon") and spec.get("emoji")


def test_a_versioned_reference_names_the_catalogue_version():
    # A page resolves `<id>:<version>` whole: another version than the catalogue's is no skill.
    catalogue = _catalogue()
    wrong = {}
    for kind in NAMING_KINDS:
        for path in sorted((ROOT / kind).rglob("*.yaml")):
            spec = yaml.safe_load(path.read_text())
            if not isinstance(spec, dict):
                continue
            for raw in _references(spec):
                skill_id, _, version = raw.partition(":")
                if version and str(catalogue[skill_id]["version"]) != version:
                    wrong[f"{kind}/{path.name}"] = raw
    assert wrong == {}


def test_an_optional_reference_is_read_with_its_version():
    """`optional.skills` names skills too: a wrong version there is a wrong version."""
    spec = {
        "skills": ["crawl:0.0.1", {"id": "pdf:0.0.1"}],
        "optional": {"skills": ["image-stock:9.9.9"]},
    }
    assert _references(spec) == ["crawl:0.0.1", "pdf:0.0.1", "image-stock:9.9.9"]
    assert _references({"optional": None}) == [] and _references({}) == []


def test_the_memory_skills_are_told_apart():
    catalogue = _catalogue()
    memory = [spec for skill, spec in catalogue.items() if skill.startswith("datalayer-memory-")]
    assert len(memory) == 4
    for field in ("name", "description", "icon", "emoji"):
        assert len({spec[field] for spec in memory}) == 4
