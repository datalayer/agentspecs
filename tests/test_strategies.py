# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""The strategies catalogue: control-loop reasoning strategies."""

from pathlib import Path

import agentspecs
from agentspecs.strategies import (
    STRATEGY_CATALOGUE,
    Strategies,
    StrategySpec,
    get_strategy,
    list_strategies,
)


def test_the_catalogue_loads_every_yaml():
    folder = Path(agentspecs.__file__).parent / "strategies"
    ids = sorted(path.stem for path in folder.glob("*.yaml"))
    assert sorted(spec.id for spec in STRATEGY_CATALOGUE) == ids
    assert ids == ["data-analysis", "human-in-the-loop", "ooda", "plan-execute-critic"]


def test_lookup_and_enum():
    spec = get_strategy("human-in-the-loop")
    assert isinstance(spec, StrategySpec)
    assert spec.human is not None and spec.human.approval_required
    assert get_strategy("missing") is None
    assert Strategies.OODA.value == "ooda"
    assert list_strategies() == STRATEGY_CATALOGUE


def test_no_loops_catalogue_remains():
    assert not (Path(agentspecs.__file__).parent / "loops").exists()
