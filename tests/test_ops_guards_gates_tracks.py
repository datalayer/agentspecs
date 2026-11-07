# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Ops, Guards, Gates and Tracks: the catalogues load, and what each promises is checked.

Guards check, Gates decide, Tracks record, and an Op is not complete unless it
declares how its work is verified. Each of those sentences is a check here.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from pydantic import ValidationError

from agentspecs.gates import (
    GATE_CATALOGUE,
    GateAction,
    GateError,
    GateSpec,
    check_gate,
    get_gate,
    list_gates,
    signals_of,
)
from agentspecs.guards import (
    GUARD_CATALOGUE,
    GuardCategory,
    GuardError,
    GuardSpec,
    GuardStage,
    get_guard,
    get_resolved_guard,
    guards_extending,
    list_guards,
    policy_of,
    policy_ref,
    resolve_guard,
)
from agentspecs.ops import (
    OP_CATALOGUE,
    OpError,
    OpSpec,
    get_op,
    get_resolved_op,
    list_ops,
    ops_using,
    resolve_op,
)
from agentspecs.policies import POLICY_CATALOGUE, PolicySpec
from agentspecs.tracks import (
    REQUIRED_ITEMS,
    TRACK_CATALOGUE,
    TrackError,
    TrackItem,
    TrackSpec,
    get_track,
    list_tracks,
    retention_days,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"
OP = "op-sales-pipeline-board-report"


def _raw(folder: str, identity: str) -> dict:
    return yaml.safe_load((ROOT / folder / f"{identity}.yaml").read_text())


def _guard(**fields) -> dict:
    return {
        "id": "g",
        "name": "G",
        "extends": "default:0.0.1",
        "category": "algorithmic",
        "stages": ["post_run"],
        "check": "something",
        **fields,
    }


def _gate(**fields) -> dict:
    return {
        "id": "t",
        "name": "T",
        "guards": ["confidence-guard"],
        "when": "confidence < 0.8",
        "then": "pause",
        **fields,
    }


def _track(**fields) -> dict:
    return {
        "id": "t",
        "name": "T",
        "retain_for": "1_years",
        "include": [item.value for item in REQUIRED_ITEMS],
        **fields,
    }


class TestAGuardExtendsAPolicy:
    def test_every_guard_extends_a_policy_of_the_catalogue(self):
        assert len(list_guards()) == len(GUARD_CATALOGUE) >= 12
        for guard in list_guards():
            assert guard.extends.split(":")[0] in POLICY_CATALOGUE, guard.id
            assert guard.check.strip() and guard.description.strip()
            assert "guardrail" not in (guard.description + guard.check).lower(), guard.id

    def test_the_seven_categories_and_the_four_stages_are_all_covered(self):
        assert {guard.category for guard in list_guards()} == set(GuardCategory)
        assert {stage for guard in list_guards() for stage in guard.stages} == set(GuardStage)

    def test_a_resolved_guard_names_the_policy_it_verifies_and_carries_nothing_of_it(self):
        guard = get_resolved_guard("sensitive-data-guard:0.0.1")
        assert guard["policy"] == "organization-baseline:0.0.1"
        assert "extends" not in guard
        # The Policy's document is not merged in: it is read through `policy_of`.
        assert not {"rules", "limits", "permissions", "data_scope", "token_limits"} & set(guard)
        assert (guard["id"], guard["name"]) == ("sensitive-data-guard", "Sensitive Data Guard")
        assert guard["category"] == "policy-safety" and guard["stages"] == ["in_flight", "post_run"]
        assert guard["signals"][0]["name"] == "sensitive_data_detected"
        assert guard["tags"] == ["privacy", "pii", "secrets"] and guard["icon"] == "shield-check"

    def test_policy_of_gives_the_policy_spec_written_or_resolved(self):
        written = policy_of(get_guard("permission-guard"))
        assert isinstance(written, PolicySpec) and written.id == "default"
        assert written is POLICY_CATALOGUE["default"]
        resolved = policy_of(get_resolved_guard("sensitive-data-guard"))
        assert resolved.id == "organization-baseline" and resolved.scope == "organization"
        assert policy_of({"id": "g", "extends": "default"}).version == "0.0.1"
        with pytest.raises(GuardError, match="names no Policy"):
            policy_of({"id": "g"})
        with pytest.raises(GuardError, match=r"Guard 'g' extends 'nope' is not a Policy"):
            policy_of({"id": "g", "policy": "nope"})

    def test_a_reference_resolves_to_the_catalogues_id_and_version(self):
        assert policy_ref("default") == "default:0.0.1"
        assert policy_ref("organization-baseline:0.0.1") == "organization-baseline:0.0.1"
        with pytest.raises(ValueError, match="names a version the Policy 'default' does not have"):
            policy_ref("default:0.0.9")

    def test_a_guard_that_extends_nothing_or_no_policy_is_refused(self):
        with pytest.raises(ValidationError):
            GuardSpec(**{key: value for key, value in _guard().items() if key != "extends"})
        with pytest.raises(ValidationError, match="is not a Policy of the catalogue"):
            GuardSpec(**_guard(extends="worker-crawler:0.0.1"))
        with pytest.raises(ValidationError, match="is not a Policy of the catalogue"):
            resolve_guard(_guard(extends="default-platform-user:0.0.1"))
        with pytest.raises(ValidationError, match="does not have"):
            resolve_guard(_guard(extends="default:0.0.2"))

    def test_a_guard_carries_no_field_of_a_policy(self):
        with pytest.raises(ValidationError):
            GuardSpec(**_guard(permissions={"read:data": True}))
        with pytest.raises(ValidationError):
            GuardSpec(**_guard(rules=[]))
        assert resolve_guard(_guard())["policy"] == "default:0.0.1"

    def test_a_guard_names_a_stage_a_category_and_a_check(self):
        for broken in (
            _guard(stages=[]),
            _guard(stages=["post_run", "post_run"]),
            _guard(category="vibes"),
            _guard(check="  "),
        ):
            with pytest.raises(ValidationError):
                GuardSpec(**broken)
        with pytest.raises(ValidationError):
            GuardSpec(**_guard(signals=[{"name": "s", "type": "list"}]))

    def test_the_guards_of_a_policy_are_found(self):
        assert [guard.id for guard in guards_extending("organization-baseline:0.0.1")] == [
            "sensitive-data-guard"
        ]
        assert len(guards_extending("default")) == len(GUARD_CATALOGUE) - 1
        assert get_guard("no-such-guard") is None and get_resolved_guard("no-such-guard") is None


class TestAGateDecides:
    def test_every_gate_reads_guards_that_exist_and_signals_they_report(self):
        assert len(list_gates()) == len(GATE_CATALOGUE) >= 8
        for gate in list_gates():
            for ref in gate.guards:
                assert get_guard(ref) is not None, f"{gate.id}: {ref}"
            reported = {signal.name for ref in gate.guards for signal in get_guard(ref).signals}
            assert set(gate.signals) <= reported, gate.id

    def test_the_catalogue_decides_in_more_than_one_way(self):
        assert {gate.then for gate in list_gates()} >= {
            GateAction.STOP_AND_ESCALATE,
            GateAction.RETRY,
            GateAction.PAUSE,
            GateAction.HUMAN_REVIEW_REQUIRED,
            GateAction.HUMAN_APPROVAL_REQUIRED,
            GateAction.EXPERT_REVIEW_REQUIRED,
        }
        assert get_gate("release-approval:0.0.1").when == "always"

    def test_a_condition_is_read_or_refused(self):
        assert signals_of("confidence < 0.80") == ["confidence"]
        assert signals_of("schema_valid == false or unsupported_claims > 0") == [
            "schema_valid",
            "unsupported_claims",
        ]
        assert signals_of("a and b or a") == ["a", "b"]
        assert signals_of("vendor_risk == high") == ["vendor_risk"]
        assert signals_of("always") == []
        for unreadable in ("confidence <", "import os", "a && b", "0.8 > confidence", "x == 'y'"):
            with pytest.raises(GateError, match="cannot read"):
                signals_of(unreadable)

    def test_a_gate_that_hands_over_to_a_person_says_to_whom(self):
        with pytest.raises(ValidationError, match="reviewers"):
            GateSpec(**_gate(then="human_review_required"))
        assert GateSpec(
            **_gate(then="human_review_required", reviewers=["op-owner"])
        ).reviewers == ["op-owner"]
        # Whichever branch hands over.
        with pytest.raises(ValidationError, match="decides human_approval_required"):
            GateSpec(**_gate(then="pause", otherwise="human_approval_required"))
        assert GateSpec(
            **_gate(then="pause", otherwise="stop_and_escalate", reviewers=["op-owner"])
        )

    def test_a_gate_that_retries_says_how_often_and_one_that_decides_nothing_is_refused(self):
        with pytest.raises(ValidationError, match="max_retries"):
            GateSpec(**_gate(then="retry"))
        with pytest.raises(ValidationError, match="decides nothing"):
            GateSpec(**_gate(then="proceed"))
        with pytest.raises(ValidationError, match="names the `guards`"):
            GateSpec(**_gate(guards=[]))

    def test_a_gate_reading_a_signal_no_guard_reports_is_refused(self):
        guards = {"confidence-guard": _raw("guards", "confidence-guard")}
        check_gate(GateSpec(**_gate()), guards)
        with pytest.raises(GateError, match="none of its Guards reports"):
            check_gate(GateSpec(**_gate(when="vibes > 3")), guards)
        with pytest.raises(GateError, match="not defined"):
            check_gate(GateSpec(**_gate(guards=["ghost"])), guards)


class TestATrackKeepsEvidence:
    def test_the_catalogue_holds_a_default_and_a_long_one(self):
        assert {"standard", "financial-reporting"} <= set(TRACK_CATALOGUE)
        assert len(list_tracks()) == len(TRACK_CATALOGUE)
        assert get_track("standard").retention_days == 365
        assert get_track("financial-reporting:0.0.1").retention_days == 7 * 365
        assert set(get_track("financial-reporting").include) == set(TrackItem)

    def test_evidence_is_not_for_sale(self):
        assert all(track.exchangeable is False for track in list_tracks())
        assert TrackSpec(**_track(exchangeable=False)).exchangeable is False
        with pytest.raises(ValidationError):
            TrackSpec(**_track(exchangeable=True))

    def test_a_retention_is_read_or_refused(self):
        assert retention_days("90_days") == 90
        assert retention_days("18_months") == 540
        assert retention_days("1_year") == 365
        for unreadable in ("forever", "7 years", "0_years", "7y"):
            with pytest.raises(TrackError, match="cannot read"):
                retention_days(unreadable)
        with pytest.raises(ValidationError):
            TrackSpec(**_track(retain_for="forever"))

    def test_a_track_keeps_what_makes_a_record(self):
        assert TrackSpec(**_track()).include == list(REQUIRED_ITEMS)
        with pytest.raises(ValidationError, match="missing: gate_decisions"):
            TrackSpec(
                **_track(
                    include=[
                        item.value
                        for item in REQUIRED_ITEMS
                        if item is not TrackItem.GATE_DECISIONS
                    ]
                )
            )
        with pytest.raises(ValidationError):
            TrackSpec(**_track(include=[*[item.value for item in REQUIRED_ITEMS], "vibes"]))


class TestTheComprehensiveOp:
    """One Cog, and everything the accountability plane puts around it."""

    def test_it_is_in_the_catalogue_and_owned(self):
        assert list(OP_CATALOGUE) == [OP] and len(list_ops()) == 1
        op = get_op(f"{OP}:0.0.1")
        assert op.owner.strip() and op.cogs == ["cog-sales-pipeline-board-report:0.0.1"]
        assert get_op("no-such-op") is None and get_resolved_op("no-such-op") is None

    def test_it_uses_every_kind_of_spec(self):
        op = get_resolved_op(OP)
        assert [cog["id"] for cog in op["cogs"]] == ["cog-sales-pipeline-board-report"]
        assert op["cogs"][0]["agent"] == "worker-sales-pipeline-board-report"
        assert op["frames"] == ["datalayer"]
        assert op["lineage"] == ["datalayer", "sales-pipeline", "board-reporting"]
        assert all(op["guards"][stage.value] for stage in GuardStage)
        assert len(op["gates"]) == 8
        assert op["track"]["id"] == "financial-reporting" and op["track"]["retention_days"] == 2555

    def test_its_guards_are_of_all_seven_categories_each_naming_its_policy(self):
        guards = [guard for stage in get_resolved_op(OP)["guards"].values() for guard in stage]
        assert {guard["category"] for guard in guards} == {
            category.value for category in GuardCategory
        }
        for guard in guards:
            assert guard["policy"].split(":")[0] in POLICY_CATALOGUE and "extends" not in guard
            assert policy_of(guard).id == guard["policy"].split(":")[0]

    def test_it_carries_the_guards_its_frames_declare(self):
        declared = [guard["id"] for guard in get_resolved_op(OP)["frame_guards"]]
        assert declared.count("no-secrets") == 1
        assert {"totals-reconcile", "summary-first", "finance-review"} <= set(declared)

    def test_every_gate_reads_guards_the_op_runs(self):
        op = get_resolved_op(OP)
        ran = {guard["id"] for stage in op["guards"].values() for guard in stage}
        for gate in op["gates"]:
            assert {ref.split(":")[0] for ref in gate["guards"]} <= ran
        assert [gate["id"] for gate in op["gates"]][-2:] == [
            "release-approval",
            "quality-drift-review",
        ]

    def test_what_names_a_spec_is_found(self):
        for ref in (
            "cog-sales-pipeline-board-report",
            "schema-guard:0.0.1",
            "release-approval",
            "financial-reporting",
        ):
            assert [op.id for op in ops_using(ref)] == [OP]
        assert ops_using("standard") == []


class TestAnOpIsNotCompleteWithoutItsValidation:
    def _op(self, **changes) -> dict:
        op = _raw("ops", OP)
        op.update(changes)
        return op

    def test_the_example_resolves_as_written(self):
        assert resolve_op(self._op())["id"] == OP

    @pytest.mark.parametrize(
        "changes, said",
        [
            ({"gates": []}, "names no Gate"),
            ({"track": " "}, "names no Track"),
            ({"guards": {"preflight": ["permission-guard"]}}, "names no post-run Guard"),
            ({"owner": ""}, "names its owner"),
            ({"cogs": []}, "at least one Cog"),
        ],
    )
    def test_an_op_missing_part_of_its_contract_is_refused(self, changes, said):
        with pytest.raises(ValidationError, match=said):
            OpSpec(**self._op(**changes))

    @pytest.mark.parametrize(
        "changes, said",
        [
            ({"cogs": ["ghost-cog"]}, "Cog 'ghost-cog', which is not defined"),
            ({"frames": ["ghost-frame"]}, "ghost-frame"),
            ({"track": "ghost-track"}, "Track 'ghost-track', which is not defined"),
            ({"gates": ["ghost-gate"]}, "Gate 'ghost-gate', which is not defined"),
        ],
    )
    def test_an_op_naming_something_that_does_not_exist_is_refused_by_name(self, changes, said):
        with pytest.raises(OpError, match=said):
            resolve_op(self._op(**changes))

    def test_a_guard_is_run_at_a_stage_it_runs_at(self):
        guards = {**_raw("ops", OP)["guards"], "preflight": ["schema-guard:0.0.1"]}
        with pytest.raises(
            OpError, match="runs Guard 'schema-guard' at preflight; it runs at post_run"
        ):
            resolve_op(self._op(guards=guards))
        with pytest.raises(OpError, match="Guard 'ghost', which is not defined"):
            resolve_op(self._op(guards={**guards, "preflight": ["ghost"]}))

    def test_a_gate_reads_a_guard_the_op_runs(self):
        guards = dict(_raw("ops", OP)["guards"])
        guards["post_run"] = [
            ref for ref in guards["post_run"] if not ref.startswith("consensus-guard")
        ]
        with pytest.raises(
            OpError, match="reads Guard 'consensus-guard:0.0.1', which the Op does not run"
        ):
            resolve_op(self._op(guards=guards))

    def test_gates_are_listed_in_the_order_of_the_stages(self):
        gates = list(_raw("ops", OP)["gates"])
        gates.insert(0, gates.pop())  # the continuous Gate, before the pre-flight one
        with pytest.raises(
            OpError,
            match="Gate 'configuration-check' decides at preflight and is listed after 'quality-drift-review'",
        ):
            resolve_op(self._op(gates=gates))
        # Two Gates of one stage may be in either order.
        gates = list(_raw("ops", OP)["gates"])
        gates[1], gates[2] = gates[2], gates[1]
        assert resolve_op(self._op(gates=gates))["gates"][1]["id"] == "tool-violation-retry"

    def test_an_op_that_is_offered_has_workers_that_are(self):
        # The example is a draft, as its Cog is: that resolves.
        assert get_resolved_op(OP)["enabled"] is False
        with pytest.raises(
            OpError,
            match="is enabled and names Cog 'cog-sales-pipeline-board-report', which is not",
        ):
            resolve_op(self._op(enabled=True))
        assert resolve_op(self._op(enabled=True, cogs=["cog-crawler:0.0.1"]))["enabled"] is True

    def test_a_gate_does_not_decide_before_its_guard_has_run(self):
        guards = dict(_raw("ops", OP)["guards"])
        # The sensitive-data Gate decides in flight; run its Guard post-run only.
        guards["in_flight"] = [
            ref for ref in guards["in_flight"] if not ref.startswith("sensitive-data-guard")
        ]
        with pytest.raises(
            OpError, match="decides at in_flight, before Guard 'sensitive-data-guard' has run"
        ):
            resolve_op(self._op(guards=guards))
