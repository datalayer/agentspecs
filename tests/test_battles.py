# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Battles: the catalogue loads, each variant reads, and every refusal is a sentence."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentspecs.battles import (
    BATTLE_CATALOGUE,
    MIN_CLOCK_SECONDS,
    BattleArena,
    BattleDecision,
    BattleError,
    BattleSpec,
    BattleVariant,
    check_battle,
    get_battle,
    list_battles,
)


def _battle(**changes):
    base = {
        "id": "a-race",
        "name": "A race",
        "variant": "race",
        "goal": "List the open invoices.",
        "clock_seconds": 60,
        "contestants": [
            {"id": "blue", "scene": "sales-and-accounting:0.0.1"},
            {"id": "red", "scene": "sales-and-accounting:0.0.1"},
        ],
        "referee": {"decides_by": "first_done"},
    }
    base.update(changes)
    return base


class TestCatalogue:
    def test_three_battles_one_per_variant(self):
        assert sorted(BATTLE_CATALOGUE) == ["invoice-race", "pong", "report-challenge"]
        assert {battle.variant for battle in list_battles()} == set(BattleVariant)

    def test_each_is_decided_as_its_variant(self):
        assert get_battle("invoice-race").decides_by is BattleDecision.FIRST_DONE
        assert get_battle("pong").decides_by is BattleDecision.SCORE
        assert get_battle("pong").arena is BattleArena.PONG
        assert get_battle("report-challenge").decides_by is BattleDecision.MEASURE
        assert get_battle("report-challenge").referee.measure == "report-quality-guard:0.0.1"

    def test_by_id_or_versioned_reference(self):
        assert get_battle("pong:0.0.1") is get_battle("pong")
        assert get_battle("chess") is None
        assert list_battles(BattleVariant.GAME) == [get_battle("pong")]

    def test_contestants_play_the_catalogue(self):
        for battle in list_battles():
            check_battle(battle)
            assert len(battle.contestants) >= 2
            assert all(contestant.shown_as for contestant in battle.contestants)
            assert battle.rehearsal.expects


class TestRefusals:
    def test_one_contestant(self):
        with pytest.raises(ValidationError, match="at least two contestants"):
            BattleSpec(**_battle(contestants=[{"id": "blue", "scene": "sales-and-accounting"}]))

    def test_two_contestants_one_id(self):
        with pytest.raises(ValidationError, match="its own id"):
            BattleSpec(**_battle(contestants=[
                {"id": "blue", "scene": "sales-and-accounting"},
                {"id": "blue", "scene": "sales-and-accounting"},
            ]))

    def test_a_scene_and_an_app(self):
        with pytest.raises(ValidationError, match="never both"):
            BattleSpec(**_battle(contestants=[
                {"id": "blue", "scene": "sales-and-accounting", "app": "accounting"},
                {"id": "red", "scene": "sales-and-accounting"},
            ]))

    def test_neither_a_scene_nor_an_app(self):
        with pytest.raises(ValidationError, match="never neither"):
            BattleSpec(**_battle(contestants=[{"id": "blue"}, {"id": "red", "scene": "sales-and-accounting"}]))

    def test_a_game_without_an_arena(self):
        with pytest.raises(ValidationError, match="names its arena"):
            BattleSpec(**_battle(variant="game", referee={"decides_by": "score"}))

    def test_an_arena_on_a_race(self):
        with pytest.raises(ValidationError, match="only a game has an arena"):
            BattleSpec(**_battle(arena="pong"))

    def test_a_race_decided_by_score(self):
        with pytest.raises(ValidationError, match="a race is decided by `first_done`"):
            BattleSpec(**_battle(referee={"decides_by": "score"}))

    def test_a_challenge_without_a_measure(self):
        with pytest.raises(ValidationError, match="names the Guard that measures"):
            BattleSpec(**_battle(variant="challenge", referee={"decides_by": "measure"}))

    def test_a_measure_on_a_race(self):
        with pytest.raises(ValidationError, match="names no measure"):
            BattleSpec(**_battle(referee={"decides_by": "first_done", "measure": "report-quality-guard"}))

    def test_a_clock_under_ten_seconds(self):
        with pytest.raises(ValidationError, match=f"at least {MIN_CLOCK_SECONDS} seconds"):
            BattleSpec(**_battle(clock_seconds=5))

    def test_an_empty_goal(self):
        with pytest.raises(ValidationError, match="says its goal"):
            BattleSpec(**_battle(goal="  "))

    def test_runs_in_on_a_scene(self):
        with pytest.raises(ValidationError, match="its cast says where it runs"):
            BattleSpec(**_battle(contestants=[
                {"id": "blue", "scene": "sales-and-accounting", "runs_in": "runtime"},
                {"id": "red", "scene": "sales-and-accounting"},
            ]))

    def test_a_colour_off_the_palette(self):
        with pytest.raises(ValidationError, match="neither a name of the palette"):
            BattleSpec(**_battle(contestants=[
                {"id": "blue", "scene": "sales-and-accounting", "color": "blueish"},
                {"id": "red", "scene": "sales-and-accounting"},
            ]))

    def test_a_scene_the_catalogue_does_not_hold(self):
        battle = BattleSpec(**_battle(contestants=[
            {"id": "blue", "scene": "chess-club"},
            {"id": "red", "scene": "sales-and-accounting"},
        ]))
        with pytest.raises(BattleError, match="a scene 'chess-club', which is not in the catalogue"):
            check_battle(battle)

    def test_a_scene_at_another_version(self):
        battle = BattleSpec(**_battle(contestants=[
            {"id": "blue", "scene": "sales-and-accounting:9.9.9"},
            {"id": "red", "scene": "sales-and-accounting"},
        ]))
        with pytest.raises(BattleError, match="the catalogue has version 0.0.1"):
            check_battle(battle)

    def test_an_app_the_catalogue_does_not_hold(self):
        battle = BattleSpec(**_battle(contestants=[
            {"id": "blue", "app": "nowhere"},
            {"id": "red", "scene": "sales-and-accounting"},
        ]))
        with pytest.raises(BattleError, match="an app 'nowhere'"):
            check_battle(battle)

    def test_a_measure_guard_without_a_number_signal(self):
        battle = BattleSpec(**_battle(
            variant="challenge", referee={"decides_by": "measure", "measure": "outcome-guard"},
        ))
        with pytest.raises(BattleError, match="has no number signal"):
            check_battle(battle)

    def test_a_measure_guard_the_catalogue_does_not_hold(self):
        battle = BattleSpec(**_battle(
            variant="challenge", referee={"decides_by": "measure", "measure": "taste-guard"},
        ))
        with pytest.raises(BattleError, match="a Guard 'taste-guard'"):
            check_battle(battle)


class TestReportQualityGuard:
    def test_the_challenges_measure_is_a_cog_judged_outcome_guard(self):
        from agentspecs.guards import get_guard

        guard = get_guard("report-quality-guard")
        assert guard is not None
        assert guard.category.value == "outcome"
        assert guard.method.value == "cog"
        assert [signal.name for signal in guard.signals if signal.type == "number"] == [
            "quality",
            "ungrounded_figures",
        ]
