# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Teams: the catalogue loads, and the things a team promises are checked.

Teams were the one catalogue with no schema, so nothing verified that a member
named an agent that exists, that the running order could be computed, or that
the order terminated. These are the checks that were missing.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest
import yaml

# Loaded directly rather than as `agentspecs.teams`.
#
# `agentspecs/__init__.py` imports `.composition`, `.discovery`, `.proxy` and
# `.types`, none of which are in this repository — so `import agentspecs`
# raises before any submodule is reached, and every sibling catalogue
# (`loops`, `memory`, `models`) is equally unimportable. That is a pre-existing
# packaging problem and not this module's to fix here; the file under test is
# the real one either way.
_spec = importlib.util.spec_from_file_location(
    "agentspecs_teams_under_test",
    pathlib.Path(__file__).parent.parent / "agentspecs" / "teams" / "__init__.py",
)
_TEAMS = importlib.util.module_from_spec(_spec)
sys.modules["agentspecs_teams_under_test"] = _TEAMS
_spec.loader.exec_module(_TEAMS)

TEAM_CATALOGUE = _TEAMS.TEAM_CATALOGUE
TeamRole = _TEAMS.TeamRole
TeamSpec = _TEAMS.TeamSpec
get_team = _TEAMS.get_team
list_teams = _TEAMS.list_teams
teams_using = _TEAMS.teams_using

AGENTS_DIR = pathlib.Path(__file__).parent.parent / "agentspecs" / "agents"


def _known_agent_refs() -> set[str]:
    """Every agent in the catalogue, by id and by `id:version`."""
    known: set[str] = set()
    for path in AGENTS_DIR.glob("*.yaml"):
        spec = yaml.safe_load(path.read_text())
        known.add(spec["id"])
        known.add(f"{spec['id']}:{spec.get('version', '0.0.1')}")
    return known


def _minimal(**overrides) -> dict:
    """The smallest valid team, for tests about one field at a time."""
    spec = {
        "id": "t",
        "name": "T",
        "supervisor": {"name": "S", "ref": "loop-base:0.0.1"},
        "agents": [{"id": "a", "ref": "x:0.0.1"}],
    }
    spec.update(overrides)
    return spec


class TestCatalogue:
    def test_every_team_loads(self):
        assert TEAM_CATALOGUE, "the team catalogue is empty"

    def test_get_team_finds_one_by_id(self):
        assert get_team("jupyter-notebook") is not None
        assert get_team("no-such-team") is None

    def test_list_teams_filters_by_tag(self):
        tagged = list_teams(tag="notebook")
        assert tagged, "expected at least one notebook team"
        assert all("notebook" in team.tags for team in tagged)


class TestReferencesResolve:
    def test_every_referenced_agent_exists(self):
        """A `ref` that names nothing is a team that cannot run.

        The check the reference-based design exists to make possible: before,
        a member restated a name and there was nothing to resolve.
        """
        known = _known_agent_refs()
        dangling = [
            (team.id, ref)
            for team in TEAM_CATALOGUE
            for ref in team.referenced_agents()
            if ref not in known and ref.split(":")[0] not in known
        ]
        assert not dangling, f"teams reference agents that do not exist: {dangling}"

    def test_teams_using_finds_dependants(self):
        # Asked when an agent spec is about to change: who depends on this?
        users = [team.id for team in teams_using("jupyter-notebook-compactor")]
        assert "jupyter-notebook" in users

    def test_teams_using_matches_without_a_version(self):
        assert teams_using("jupyter-tutor") == teams_using("jupyter-tutor:0.0.1")


class TestExecutionOrder:
    def test_a_chain_runs_one_at_a_time(self):
        team = TeamSpec(
            **_minimal(
                agents=[
                    {"id": "a", "ref": "x:0.0.1"},
                    {"id": "b", "ref": "x:0.0.1", "depends_on": ["a"]},
                    {"id": "c", "ref": "x:0.0.1", "depends_on": ["b"]},
                ]
            )
        )
        assert team.execution_order() == [["a"], ["b"], ["c"]]

    def test_independent_members_share_a_group(self):
        """The point of `depends_on`: what may run at once is now computable."""
        team = TeamSpec(
            **_minimal(
                agents=[
                    {"id": "a", "ref": "x:0.0.1"},
                    {"id": "b", "ref": "x:0.0.1"},
                    {"id": "c", "ref": "x:0.0.1", "depends_on": ["a", "b"]},
                ]
            )
        )
        assert team.execution_order() == [["a", "b"], ["c"]]

    def test_order_follows_declaration_within_a_group(self):
        # Stable, rather than whatever the set happened to iterate.
        team = TeamSpec(
            **_minimal(
                agents=[
                    {"id": "z", "ref": "x:0.0.1"},
                    {"id": "a", "ref": "x:0.0.1"},
                ]
            )
        )
        assert team.execution_order() == [["z", "a"]]

    def test_every_catalogued_team_has_an_order(self):
        for team in TEAM_CATALOGUE:
            groups = team.execution_order()
            assert sum(len(g) for g in groups) == len(team.agents)


class TestValidation:
    def test_a_cycle_is_refused(self):
        """Caught at load, not at run — with a model loaded and a person waiting."""
        with pytest.raises(ValueError, match="cycle"):
            TeamSpec(
                **_minimal(
                    agents=[
                        {"id": "a", "ref": "x:0.0.1", "depends_on": ["b"]},
                        {"id": "b", "ref": "x:0.0.1", "depends_on": ["a"]},
                    ]
                )
            )

    def test_self_dependency_is_refused(self):
        with pytest.raises(ValueError, match="depends on itself"):
            TeamSpec(
                **_minimal(agents=[{"id": "a", "ref": "x:0.0.1", "depends_on": ["a"]}])
            )

    def test_dependency_on_a_stranger_is_refused(self):
        with pytest.raises(ValueError, match="not a member"):
            TeamSpec(
                **_minimal(
                    agents=[{"id": "a", "ref": "x:0.0.1", "depends_on": ["nobody"]}]
                )
            )

    def test_duplicate_member_ids_are_refused(self):
        with pytest.raises(ValueError, match="duplicate member"):
            TeamSpec(
                **_minimal(
                    agents=[{"id": "a", "ref": "x:0.0.1"}, {"id": "a", "ref": "y:0.0.1"}]
                )
            )

    def test_a_team_needs_a_supervisor(self):
        """A team is agents plus someone deciding what happens next."""
        spec = _minimal()
        del spec["supervisor"]
        with pytest.raises(ValueError):
            TeamSpec(**spec)

    def test_a_supervisor_needs_a_definition(self):
        with pytest.raises(ValueError, match="needs a `ref`"):
            TeamSpec(**_minimal(supervisor={"name": "S"}))

    def test_a_member_needs_a_definition(self):
        with pytest.raises(ValueError, match="needs a `ref`"):
            TeamSpec(**_minimal(agents=[{"id": "a"}]))

    def test_a_subagent_needs_a_definition(self):
        with pytest.raises(ValueError, match="needs either"):
            TeamSpec(
                **_minimal(
                    agents=[
                        {
                            "id": "a",
                            "ref": "x:0.0.1",
                            "subagents": [{"name": "Helper"}],
                        }
                    ]
                )
            )


class TestJupyterNotebookTeam:
    """The team the reference-based design was written for."""

    def test_the_tutor_supervises_and_cannot_end_the_run(self):
        team = get_team("jupyter-notebook")
        assert team.supervisor.ref == "jupyter-tutor:0.0.1"
        # A tutor would end the run when the learner understood, which is
        # exactly when a requested compaction has not happened yet.
        assert team.supervisor.can_terminate is False

    def test_both_specialists_are_members(self):
        team = get_team("jupyter-notebook")
        assert [m.ref for m in team.agents] == [
            "jupyter-tutor:0.0.1",
            "jupyter-notebook-compactor:0.0.1",
        ]

    def test_the_compactor_needs_a_person(self):
        # It rewrites the notebook somebody is working in.
        team = get_team("jupyter-notebook")
        assert team.member("compactor").approval.value == "manual"
        assert team.member("tutor").approval.value == "auto"

    def test_members_may_not_delegate_to_each_other(self):
        # The tutor handing work to the compactor would edit a notebook the
        # learner is working in — the one thing the tutor exists not to do.
        team = get_team("jupyter-notebook")
        assert team.delegation.allow_peer_delegation is False

    def test_roles_are_structural(self):
        team = get_team("jupyter-notebook")
        assert team.member("tutor").role is TeamRole.INITIATOR
        assert team.member("compactor").role is TeamRole.FINALIZER
