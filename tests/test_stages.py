# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Stages: the catalogue loads, each kind reads, what is staged is in the catalogue, and every refusal is a sentence."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentspecs.stages import (
    STAGE_CATALOGUE,
    StageError,
    StageKind,
    StageSpec,
    check_stage,
    get_stage,
    list_stages,
    resolve_stage,
)


def _stage(**changes):
    base = {"id": "a-stage", "scene": "sales-and-accounting:0.0.1", "deployments": {"accounting": "demo-accounting"}}
    base.update(changes)
    return base


class TestCatalogue:
    def test_thirteen_stages_of_the_three_kinds(self):
        assert sorted(STAGE_CATALOGUE) == [
            "accounting",
            "coding-agent-behind-the-shield",
            "crop-monitoring",
            "disaster-assessment",
            "month-end-close",
            "pact-a-personal-agent-at-a-business",
            "pap-a-person-and-a-company",
            "pap-approve-once",
            "pap-two-companies",
            "pap-your-application-a-company",
            "pong",
            "sales-and-accounting",
            "ucp-a-purchase-approved",
        ]
        assert {stage.kind for stage in list_stages()} == set(StageKind)
        assert [stage.id for stage in list_stages(StageKind.APP)] == ["accounting"]
        assert [stage.id for stage in list_stages(StageKind.BATTLE)] == ["pong"]

    def test_the_demo_stages_are_public_and_deployed_the_scripted_ones_public_and_not(self):
        demo = [stage for stage in list_stages(StageKind.SCENE) if "demo" in stage.tags]
        assert sorted(stage.id for stage in demo) == [
            "coding-agent-behind-the-shield",
            "crop-monitoring",
            "disaster-assessment",
            "month-end-close",
            "sales-and-accounting",
        ]
        assert all(stage.public and stage.deployments for stage in demo)
        scripted = [stage for stage in list_stages(StageKind.SCENE) if "scripted" in stage.tags]
        assert len(scripted) == 6
        assert all(stage.public and not stage.deployments for stage in scripted)
        assert sorted(stage.id for stage in list_stages(public=False)) == ["accounting", "pong"]

    def test_each_stage_wears_what_it_stages(self):
        stage = get_stage("sales-and-accounting")
        assert stage is not None
        assert (stage.name, stage.emoji) == ("Sales & Accounting", "🤝")
        assert stage.description.startswith("A sales desk asks Accounting")
        assert get_stage("pong").emoji == "🏓"
        assert get_stage("accounting").name == "Accounting, on its own"
        assert get_stage("sales-and-accounting:0.0.1") is stage
        assert get_stage("nobody") is None

    def test_the_disaster_assessment_stage_deploys_both_members_on_runtimes(self):
        assert get_stage("disaster-assessment").deployments == {
            "disaster-assessment": "demo-disaster-assessment",
            "change-detection": "demo-change-detection",
        }


class TestRefusals:
    @pytest.mark.parametrize(
        "changes, says",
        [
            ({"app": "accounting:0.0.2"}, "one thing on stage"),
            ({"scene": "", "deployments": {}}, "not nothing"),
            ({"scene": "", "battle": "pong:0.0.1"}, "names no deployments"),
            ({"id": "A Stage"}, "a slug"),
            ({"deployments": {"Accounting": "demo-accounting"}}, "a slug"),
            ({"deployments": {"accounting": "Demo Accounting"}}, "demo-accounting"),
            ({"extra": 1}, "extra"),
        ],
    )
    def test_as_it_is_read(self, changes, says):
        with pytest.raises(ValidationError) as caught:
            StageSpec(**_stage(**changes))
        assert says in str(caught.value)

    def test_what_it_names_is_in_the_catalogue(self):
        with pytest.raises(StageError, match="not in the catalogue"):
            check_stage(StageSpec(**_stage(scene="nobody:0.0.1")))
        with pytest.raises(StageError, match="the catalogue has version"):
            check_stage(StageSpec(**_stage(scene="sales-and-accounting:9.9.9")))
        with pytest.raises(StageError, match="not in the catalogue"):
            check_stage(StageSpec(**_stage(scene="", app="nobody")))
        with pytest.raises(StageError, match="not in the catalogue"):
            check_stage(StageSpec(**_stage(scene="", deployments={}, battle="nobody")))

    def test_its_deployments_are_its_members(self):
        with pytest.raises(StageError, match="who is not on the stage"):
            check_stage(StageSpec(**_stage(deployments={"nobody": "demo-nobody"})))
        with pytest.raises(StageError, match="scripted scene"):
            check_stage(StageSpec(**_stage(scene="pap-approve-once", deployments={"ada": "demo-ada"})))
        with pytest.raises(StageError, match="the one application on it"):
            check_stage(StageSpec(**_stage(scene="", app="accounting", deployments={"sales": "demo-sales"})))

    def test_resolved_from_what_it_stages_unless_it_says(self):
        stage = resolve_stage(StageSpec(**_stage()))
        assert (stage.name, stage.emoji, stage.icon) == ("Sales & Accounting", "🤝", "people")
        own = resolve_stage(StageSpec(**_stage(name="Our books", emoji="📗")))
        assert (own.name, own.emoji) == ("Our books", "📗")
        assert own.description.startswith("A sales desk")
