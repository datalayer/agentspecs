# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The policies catalogue (SH-50): the Shield's schema carried verbatim, the documents it holds."""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml

from agentspecs import policies

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"


def test_the_catalogue_holds_the_default_and_an_organizations_baseline():
    assert set(policies.POLICY_CATALOGUE) == {"default", "organization-baseline"}
    default = policies.get_policy("default")
    assert default.scope == "session" and default.enabled
    baseline = policies.get_policy("organization-baseline")
    assert baseline.scope == "organization"
    assert baseline.policy["harnesses"] == {
        "admit": ["claude-code", "codex"],
        "credentials": "account",
    }
    assert baseline.policy["limits"]["spend"] == {"soft": 500, "hard": 1000}


def test_the_default_is_decision_5s():
    rules = {rule["name"]: rule for rule in policies.get_policy("default").policy["rules"]}
    assert rules["read inside the workspace"]["decision"] == "allow"
    assert rules["edit and move inside the workspace"]["decision"] == "allow"
    assert rules["delete"]["decision"] == "ask"
    assert rules["run a command"]["decision"] == "ask"
    assert rules["outside the workspace"]["decision"] == "ask"
    assert rules["git push"]["decision"] == "ask" and rules["git push"]["commands"]
    assert rules["sudo"]["decision"] == "ask"
    assert policies.get_policy("default").policy["network"] == {"fetch": []}


def test_the_shield_schema_is_the_packages_own_verbatim():
    agent_shield_policy = pytest.importorskip(
        "agent_shield.policy",
        reason="datalayer-agent-shield is not installed here; CI installs it to hold the copy",
    )
    from agent_shield.__version__ import __version__ as installed

    def parts(version: str) -> tuple[int, ...]:
        return tuple(int(piece) for piece in version.split(".")[:3])

    if parts(installed) < parts(policies.SHIELD_SCHEMA_SOURCE_VERSION):
        pytest.skip(
            f"the carried schema is agent-shield {policies.SHIELD_SCHEMA_SOURCE_VERSION}'s and {installed} is installed: "
            "the two packages release in turn, each pinning the other's last"
        )
    carried = json.loads(policies.SHIELD_SCHEMA_PATH.read_text())
    assert carried == agent_shield_policy.policy_json_schema()
    # And every document of the catalogue is one the package's own model takes.
    for spec in policies.POLICY_CATALOGUE.values():
        agent_shield_policy.parse_policy(spec.policy, spec.id)


def test_the_catalogue_schema_points_its_policy_at_the_shields():
    schema = json.loads(policies.SCHEMA_PATH.read_text())
    assert schema == policies.json_schema()
    assert schema["properties"]["policy"]["$ref"] == "shield-policy.schema.json"
    assert schema["additionalProperties"] is False


def test_the_reference_page_is_the_catalogue():
    assert policies.REFERENCE_PATH.read_text() == policies.reference_text()


def test_a_document_with_an_unknown_key_or_a_loose_threshold_is_refused_in_a_sentence(
    tmp_path: pathlib.Path,
):
    good = yaml.safe_load((ROOT / "policies" / "default.yaml").read_text())
    bad = {**good, "id": "bad", "policy": {**good["policy"], "rulez": []}}
    (tmp_path / "bad.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(
        policies.PolicyError,
        match=r"bad.yaml: policy: the document: Additional properties are not allowed \('rulez' was unexpected\)",
    ):
        policies.load_policies(tmp_path)
    assert policies.document_problems({"scope": "nowhere"}) == [
        "scope: 'nowhere' is not one of ['organization', 'team', 'session']"
    ]
    assert policies.document_problems("x") == [
        "a policy document is a mapping with a scope, not str"
    ]


def test_a_file_named_otherwise_than_its_id_is_refused(tmp_path: pathlib.Path):
    good = yaml.safe_load((ROOT / "policies" / "default.yaml").read_text())
    (tmp_path / "other.yaml").write_text(yaml.safe_dump(good))
    with pytest.raises(policies.PolicyError, match="named for 'other', the spec says 'default'"):
        policies.load_policies(tmp_path)
    with pytest.raises(policies.PolicyError, match="There is no policy named 'nope'"):
        policies.get_policy("nope")
