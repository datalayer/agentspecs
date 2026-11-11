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

DOGWOOD_EXAMPLES = {
    "dogwood-approval-before-payment",
    "dogwood-approval-before-account-change",
    "dogwood-transfers-per-hour",
    "dogwood-distinct-payees",
    "dogwood-running-total",
    "dogwood-spend-per-session",
}


def test_the_catalogue_holds_the_default_and_an_organizations_baseline():
    assert set(policies.POLICY_CATALOGUE) == {
        "default",
        "organization-baseline",
        *DOGWOOD_EXAMPLES,
    }
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


# -- the dogwood section (AC-40) ---------------------------------------------------------------


def _installed_shield(at_least: str):
    module = pytest.importorskip(
        "agent_shield.policy",
        reason="datalayer-agent-shield is not installed here; CI installs it to hold the copy",
    )
    from agent_shield.__version__ import __version__ as installed

    def parts(version: str) -> tuple[int, ...]:
        return tuple(int(piece) for piece in version.split(".")[:3])

    if parts(installed) < parts(at_least):
        pytest.skip(f"agent-shield {installed} is older than {at_least}")
    return module


def test_the_dogwood_parser_is_the_packages_own_verbatim():
    _installed_shield(policies.SHIELD_SCHEMA_SOURCE_VERSION)
    from agent_shield.policy import dogwood as own

    carried = policies.DOGWOOD_PARSER_PATH.read_text(encoding="utf-8")
    assert carried == pathlib.Path(own.__file__).read_text(encoding="utf-8")


def test_the_dogwood_examples_are_organization_documents_and_off():
    for name in DOGWOOD_EXAMPLES:
        spec = policies.get_policy(name)
        assert spec.scope == "organization" and not spec.enabled
        assert "dogwood" in spec.tags
        assert policies.dogwood_problems(spec.policy["dogwood"]) == ([], spec.dogwood_notes)


def _temporal(window: str = "1h", operators: int = 1) -> str:
    body = " && ".join(
        f'formerly within {window} Datalayer::Action::"a{i}"::request{{ eventResource: resource }}'
        for i in range(operators)
    )
    return f"permit (principal, action, resource) when temporal {{ {body} }};"


@pytest.mark.parametrize(
    ("text", "said"),
    [
        (_temporal("25h"), "looks back 25h, over the 24-hour window AgentCore allows"),
        (_temporal("1h", 4), "4 temporal operators, over AgentCore's quota of 3"),
        ("\n".join([_temporal()] * 21), "21 temporal policies, over AgentCore's quota of 20"),
        (
            'permit (principal, action, resource) when temporal { formerly within 1h X::Action::"a"::request{ input.u: u } };',
            "bound by no 'exists' or 'for'",
        ),
        ("def temporal once(?w, ?s) { formerly within ?w ?s };", "macros"),
    ],
)
def test_a_dogwood_set_is_validated_as_it_is_read(text: str, said: str):
    problems = policies.document_problems({"scope": "organization", "dogwood": {"policies": text}})
    assert len(problems) == 1 and problems[0].startswith("dogwood: ") and said in problems[0]


def test_the_cedar_is_checked_with_cedarpy_and_said_unchecked_without(
    monkeypatch: pytest.MonkeyPatch,
):
    import builtins

    broken = "permit (principal, action, resource) when { ) };"
    real = builtins.__import__

    def without_cedarpy(name, *args, **kwargs):
        if name == "cedarpy":
            raise ImportError("no cedarpy")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_cedarpy)
    problems, notes = policies.dogwood_problems({"policies": broken})
    assert problems == []
    assert notes == [
        "cedarpy is not installed: the temporal clauses and the quotas were checked, the Cedar was not"
    ]
    monkeypatch.undo()
    pytest.importorskip("cedarpy")
    problems, notes = policies.dogwood_problems({"policies": broken})
    assert len(problems) == 1 and problems[0].startswith("Cedar refuses the set") and notes == []


def test_the_dogwood_examples_decide_as_they_say():
    """Each example, decided by agent-shield's evaluator over a session's events."""
    shield = _installed_shield("0.2.18")
    pytest.importorskip("cedarpy")
    from datetime import datetime, timedelta, timezone

    t0 = datetime(2026, 11, 9, tzinfo=timezone.utc)

    def run(example: str, steps: list[tuple[str, dict]]) -> list[bool]:
        parsed = shield.parse_set(policies.get_policy(example).policy["dogwood"]["policies"])
        log = shield.EventLog()
        verdicts = []
        for n, (tool, inputs) in enumerate(steps):
            call = shield.CedarCall(
                principal='Datalayer::User::"alice"',
                action=f'Datalayer::Action::"{tool}"',
                resource='Datalayer::Runtime::"r1"',
                context={"input": inputs},
            )
            moment = t0 + timedelta(minutes=n)
            answer = shield.evaluate(parsed, call, log.events, moment)
            log.decided(f"k{n}", call, allowed=answer.allowed, at=moment)
            if answer.allowed:
                log.ended(f"k{n}", moment + timedelta(seconds=1), ok=True)
            verdicts.append(answer.allowed)
        return verdicts

    assert run(
        "dogwood-approval-before-payment",
        [
            ("payments___pay", {"invoice": "i1"}),
            ("payments___approve", {"invoice": "i1"}),
            ("payments___pay", {"invoice": "i1"}),
            ("payments___pay", {"invoice": "i2"}),
        ],
    ) == [False, True, True, False]
    assert run("dogwood-transfers-per-hour", [("bank___transfer", {})] * 7) == [True] * 5 + [False] * 2
    payees = ["ann", "bob", "ann", "cy", "dee", "bob"]
    assert run("dogwood-distinct-payees", [("bank___transfer", {"payee": p}) for p in payees]) == [
        True,
        True,
        True,
        True,
        False,
        True,
    ]
    amounts = [200000, 200000, 200000, 100000]
    assert run(
        "dogwood-running-total", [("payments___pay", {"amountCents": a}) for a in amounts]
    ) == [True, True, False, True]
    assert run("dogwood-spend-per-session", [("shield___model", {"credits": 400})] * 3) == [
        True,
        True,
        False,
    ]


def test_an_account_change_needs_the_same_recommendation_approved_within_the_hour():
    """The AWS account agent's rule: approved, not approved, another approved, approved two hours ago."""
    shield = _installed_shield("0.2.18")
    pytest.importorskip("cedarpy")
    from datetime import datetime, timedelta, timezone

    parsed = shield.parse_set(
        policies.get_policy("dogwood-approval-before-account-change").policy["dogwood"]["policies"]
    )
    t0 = datetime(2026, 11, 11, 7, tzinfo=timezone.utc)

    def run(steps: list[tuple[int, str, str]]) -> list[bool]:
        log = shield.EventLog()
        verdicts = []
        for n, (minutes, tool, recommendation) in enumerate(steps):
            call = shield.CedarCall(
                principal='Datalayer::User::"alice"',
                action=f'Datalayer::Action::"aws_account___{tool}"',
                resource='Datalayer::Runtime::"r1"',
                context={"input": {"recommendation": recommendation}},
            )
            moment = t0 + timedelta(minutes=minutes)
            answer = shield.evaluate(parsed, call, log.events, moment)
            log.decided(f"k{n}", call, allowed=answer.allowed, at=moment)
            if answer.allowed:
                log.ended(f"k{n}", moment + timedelta(seconds=1), ok=True)
            verdicts.append(answer.allowed)
        return verdicts

    # Not approved: refused. Approved, then applied: permitted.
    assert run([(0, "apply_fix", "rec-1"), (1, "approve_recommendation", "rec-1"), (2, "apply_fix", "rec-1")]) == [
        False,
        True,
        True,
    ]
    # Another recommendation approved: refused.
    assert run([(0, "approve_recommendation", "rec-2"), (1, "apply_fix", "rec-1")]) == [True, False]
    # Approved two hours before: refused.
    assert run([(0, "approve_recommendation", "rec-1"), (120, "apply_fix", "rec-1")]) == [True, False]
    # Reading and recording are left to the rules.
    assert run([(0, "list_recommendations", "")]) == [True]
