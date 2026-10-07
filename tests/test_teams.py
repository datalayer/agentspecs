# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Teams: the catalogue loads, and the things a team promises are checked.

Teams were the one catalogue with no schema, so nothing verified that a member
named an agent that exists, that the running order could be computed, or that
the order terminated. These are the checks that were missing.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from agentspecs.teams import (
    TEAM_CATALOGUE,
    TeamRole,
    TeamSpec,
    get_team,
    list_teams,
    teams_using,
)

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
        assert get_team("jupyter") is not None
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
        assert "jupyter" in users

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

    def test_sequencing_is_depends_on_not_a_trigger(self):
        # `trigger` is what starts a member from outside the team; waiting
        # for another member is `depends_on`, which is what a runtime orders
        # by. "On completion of ..." as a trigger reads well and runs never.
        misplaced = [
            f"{team.id}/{member.id}: {member.trigger}"
            for team in list_teams()
            for member in team.agents
            if member.trigger.lower().startswith("on completion of")
        ]
        assert not misplaced, misplaced


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
            TeamSpec(**_minimal(agents=[{"id": "a", "ref": "x:0.0.1", "depends_on": ["a"]}]))

    def test_dependency_on_a_stranger_is_refused(self):
        with pytest.raises(ValueError, match="not a member"):
            TeamSpec(**_minimal(agents=[{"id": "a", "ref": "x:0.0.1", "depends_on": ["nobody"]}]))

    def test_duplicate_member_ids_are_refused(self):
        with pytest.raises(ValueError, match="duplicate member"):
            TeamSpec(
                **_minimal(agents=[{"id": "a", "ref": "x:0.0.1"}, {"id": "a", "ref": "y:0.0.1"}])
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


class TestJupyterTeam:
    """The team the reference-based design was written for.

    It began as two — a Tutor and a Compactor for a learner, then an analysis
    team — and is one team of six since the two were merged under the id
    `jupyter`.
    """

    def test_the_analyst_supervises_and_cannot_end_the_run(self):
        team = get_team("jupyter")
        assert team.supervisor.ref == "jupyter-data-analyst:0.0.1"
        # A front door that could end the run would end it when its own
        # analysis is done, which is exactly when a requested write-up, deck or
        # compaction has not happened yet.
        assert team.supervisor.can_terminate is False

    def test_all_six_specialists_are_members(self):
        team = get_team("jupyter")
        assert [m.ref for m in team.agents] == [
            "jupyter-data-analyst:0.0.1",
            "jupyter-notebook-reviewer:0.0.1",
            "jupyter-notebook-writer:0.0.1",
            "example-decks:0.0.1",
            "jupyter-tutor:0.0.1",
            "jupyter-notebook-compactor:0.0.1",
        ]

    def test_the_compactor_needs_a_person(self):
        # It rewrites the notebook somebody is working in.
        team = get_team("jupyter")
        assert team.member("compactor").approval.value == "manual"
        assert team.member("tutor").approval.value == "auto"

    def test_members_may_not_delegate_to_each_other(self):
        # The tutor handing work to the compactor would edit a notebook the
        # learner is working in — the one thing the tutor exists not to do.
        team = get_team("jupyter")
        assert team.delegation.allow_peer_delegation is False

    def test_roles_are_structural(self):
        team = get_team("jupyter")
        assert team.member("analyst").role is TeamRole.INITIATOR
        assert team.member("compactor").role is TeamRole.FINALIZER
        assert team.member("writer").role is TeamRole.FINALIZER


APPS_DIR = pathlib.Path(__file__).parent.parent / "agentspecs" / "apps"


class TestTeamsOfApplications:
    """A team may compose applications.

    Sales, in the browser, asks Accounting, on a runtime, over A2A.
    """

    def test_every_referenced_application_exists(self):
        known = {yaml.safe_load(path.read_text())["id"] for path in APPS_DIR.glob("*.yaml")}
        dangling = [
            (team.id, ref)
            for team in TEAM_CATALOGUE
            for ref in team.referenced_apps()
            if ref.split(":")[0] not in known
        ]
        assert not dangling, f"teams reference applications that do not exist: {dangling}"

    def test_sales_and_accounting_talk_over_a2a_with_sales_at_the_door(self):
        from agentspecs.teams import TeamPlace, TeamProtocol

        team = get_team("sales-and-accounting")
        assert team is not None
        assert team.entry == "sales"
        assert team.supervisor.app == "sales:0.0.1"
        assert team.referenced_apps() == ["sales:0.0.1", "accounting:0.0.1"]
        assert team.referenced_agents() == []
        sales, accounting = team.member("sales"), team.member("accounting")
        assert sales.runs_in is TeamPlace.BROWSER
        assert accounting.runs_in is TeamPlace.RUNTIME
        assert [(link.member, link.over) for link in sales.talks_to] == [
            ("accounting", TeamProtocol.A2A)
        ]
        assert accounting.talks_to == []
        assert sales.display_name == "sales"

    def test_the_applications_validate(self):
        """`loop apps validate`, the checks it makes of the spec, for each member."""
        from agentspecs.apps import APP_CATALOGUE, app_problems

        team = get_team("sales-and-accounting")
        for ref in team.referenced_apps():
            assert app_problems(APP_CATALOGUE[ref.split(":")[0]]) == [], ref

    def test_a_member_is_an_agent_or_an_application_not_both(self):
        with pytest.raises(ValueError, match="not two of them"):
            TeamSpec(**_minimal(agents=[{"id": "a", "ref": "x:0.0.1", "app": "sales"}]))
        with pytest.raises(ValueError, match="not two of them"):
            TeamSpec(**_minimal(agents=[{"id": "a", "app": "sales", "server": "odoo-accounting"}]))
        with pytest.raises(ValueError, match="not both"):
            TeamSpec(**_minimal(supervisor={"name": "S", "ref": "x", "app": "sales"}))

    def test_a_link_and_the_entry_name_members(self):
        apps = [{"id": "a", "app": "sales"}, {"id": "b", "app": "accounting"}]
        with pytest.raises(ValueError, match="talks to 'c'"):
            TeamSpec(**_minimal(agents=[{**apps[0], "talks_to": [{"member": "c"}]}, apps[1]]))
        with pytest.raises(ValueError, match="talks to itself"):
            TeamSpec(**_minimal(agents=[{**apps[0], "talks_to": [{"member": "a"}]}, apps[1]]))
        with pytest.raises(ValueError, match="enters at 'z'"):
            TeamSpec(**_minimal(agents=apps, entry="z"))
        with pytest.raises(ValueError):
            TeamSpec(
                **_minimal(
                    agents=[{**apps[0], "talks_to": [{"member": "b", "over": "smoke"}]}, apps[1]]
                )
            )
        with pytest.raises(ValueError):
            TeamSpec(**_minimal(agents=[{**apps[0], "runs_in": "moon"}, apps[1]]))


MCP_SERVERS_DIR = pathlib.Path(__file__).parent.parent / "agentspecs" / "mcp-servers"

#: The four scenes of the home page (LOOP A-08), each a team: its entry, its
#: other members, and the MCP servers under each member.
SCENES = {
    "sales-and-accounting": ("sales", ["accounting"], {"accounting": ["odoo-accounting"]}),
    "month-end-close": ("month-end-close", [], {"month-end-close": ["odoo-accounting"]}),
    "crop-monitoring": ("crop-monitoring", [], {"crop-monitoring": ["earthdata"]}),
    "disaster-assessment": (
        "event-response",
        ["disaster-assessment", "change-detection"],
        {"disaster-assessment": ["earthdata"], "change-detection": ["earthdata"]},
    ),
}


class TestScenes:
    """A scene is a team (LOOP A-04, decided 2026-10-07).

    One member allowed, none refused; each member its role; the team its
    shared context; each link its protocol, fitting who is asked.
    """

    def test_a_team_may_hold_one_member_and_never_none(self):
        alone = TeamSpec(**_minimal(agents=[{"id": "a", "ref": "x:0.0.1"}]))
        assert [member.id for member in alone.agents] == ["a"]
        assert alone.execution_order() == [["a"]]
        with pytest.raises(ValueError, match="has no member"):
            TeamSpec(**_minimal(agents=[]))

    def test_a_member_talking_to_one_not_in_the_scene_is_refused(self):
        with pytest.raises(ValueError, match="talks to 'nobody', which is not a member"):
            TeamSpec(
                **_minimal(agents=[{"id": "a", "app": "sales", "talks_to": [{"member": "nobody"}]}])
            )

    def test_a_server_is_asked_over_mcp_and_an_agent_over_a2a(self):
        from agentspecs.teams import TeamProtocol

        members = [
            {"id": "a", "app": "accounting", "talks_to": [{"member": "odoo", "over": "mcp"}]},
            {"id": "odoo", "server": "odoo-accounting:0.0.1"},
        ]
        team = TeamSpec(**_minimal(agents=members))
        assert team.member("odoo").is_server
        assert team.member("odoo").display_name == "odoo-accounting"
        assert team.referenced_servers() == ["odoo-accounting:0.0.1"]
        assert team.links() == [("a", "odoo", TeamProtocol.MCP)]
        # The protocol fits who is asked.
        with pytest.raises(ValueError, match="over a2a, which is a server"):
            TeamSpec(
                **_minimal(
                    agents=[
                        {**members[0], "talks_to": [{"member": "odoo", "over": "a2a"}]},
                        members[1],
                    ]
                )
            )
        with pytest.raises(ValueError, match="over mcp, which is not a server"):
            TeamSpec(
                **_minimal(
                    agents=[
                        {"id": "a", "app": "sales", "talks_to": [{"member": "b", "over": "mcp"}]},
                        {"id": "b", "app": "accounting"},
                    ]
                )
            )
        # A server answers and asks nobody; a person talks to no server.
        with pytest.raises(ValueError, match="is a server: it answers over MCP and asks nobody"):
            TeamSpec(**_minimal(agents=[{**members[1], "talks_to": [{"member": "a"}]}, members[0]]))
        with pytest.raises(ValueError, match="a server: a person talks to an agent"):
            TeamSpec(**_minimal(agents=members, entry="odoo"))

    def test_the_shared_context_names_the_conversation_and_the_frames(self):
        from agentspecs.frames import compose_frames
        from agentspecs.teams import TeamSharing

        plain = TeamSpec(**_minimal())
        assert plain.context.sharing is TeamSharing.SHARED
        assert plain.referenced_frames() == []
        team = TeamSpec(
            **_minimal(
                context={"sharing": "own-turns", "frames": ["datalayer:0.0.1", "sales-pipeline"]}
            )
        )
        assert team.context.sharing is TeamSharing.OWN_TURNS
        assert team.referenced_frames() == ["datalayer:0.0.1", "sales-pipeline"]
        # The Frames compose as a Cog's do.
        assert compose_frames(team.referenced_frames()).frames == ["datalayer", "sales-pipeline"]
        with pytest.raises(ValueError, match="named twice"):
            TeamSpec(**_minimal(context={"frames": ["datalayer", "datalayer:0.0.1"]}))
        with pytest.raises(ValueError):
            TeamSpec(**_minimal(context={"sharing": "telepathy"}))
        # What jupyter.yaml wrote before the context had Frames still reads.
        assert get_team("jupyter").context.sharing is TeamSharing.SHARED

    def test_every_frame_and_server_a_team_names_exists(self):
        from agentspecs.frames import get_frame

        known_servers = {
            yaml.safe_load(path.read_text())["id"] for path in MCP_SERVERS_DIR.glob("*.yaml")
        }
        for team in TEAM_CATALOGUE:
            for ref in team.referenced_frames():
                assert get_frame(ref.split(":")[0]) is not None, (team.id, ref)
            for ref in team.referenced_servers():
                assert ref.split(":")[0] in known_servers, (team.id, ref)

    def test_the_four_scenes_of_the_home_page(self):
        """LOOP A-08: Sales & Accounting, Month-end close, Crop monitoring, Disaster assessment."""
        from agentspecs.apps import APP_CATALOGUE, app_problems
        from agentspecs.teams import TeamPlace, TeamProtocol, TeamRole

        for scene, (entry, others, servers) in SCENES.items():
            team = get_team(scene)
            assert team is not None, scene
            assert "scene" in team.tags or scene == "sales-and-accounting", scene
            assert team.entry == entry and team.supervisor.app.startswith(f"{entry}:"), scene
            assert [member.id for member in team.agents] == [entry, *others], scene
            assert team.member(entry).role is TeamRole.INITIATOR, scene
            # Its page words: a name, one line, and the entry's starters as its openers.
            assert team.name and team.description.strip(), scene
            front = APP_CATALOGUE[entry]
            assert [item.text for item in team.suggestions] == [
                starter.message for starter in front.interface.starters
            ], scene
            # The entry asks each other member over A2A; the others ask nobody.
            assert [(asked, over) for _, asked, over in team.links()] == [
                (other, TeamProtocol.A2A) for other in others
            ], scene
            for other in others:
                assert team.member(other).talks_to == [], scene
                assert team.member(other).runs_in is TeamPlace.RUNTIME, scene
            # The MCP servers under each member are its application's connections.
            for member in team.agents:
                app = APP_CATALOGUE[member.app.split(":")[0]]
                assert app_problems(app) == [], (scene, member.id)
                assert [
                    connection.server.split(":")[0] for connection in app.connections
                ] == servers.get(member.id, []), (scene, member.id)
            # A member with a connection runs where its credential is.
            for member in team.agents:
                if servers.get(member.id):
                    assert member.runs_in is TeamPlace.RUNTIME, (scene, member.id)

    def test_a_single_agent_scene_says_so(self):
        for scene in ("month-end-close", "crop-monitoring"):
            team = get_team(scene)
            assert len(team.agents) == 1, scene
            assert team.description.startswith("One agent, its data:"), scene
            assert team.links() == [], scene
            assert team.delegation.max_depth == 0, scene

    def test_what_each_scene_needs_is_said_as_setup(self):
        """What is not enabled is setup, said in words (LOOP E-01): the agents are off,
        earthdata is on, odoo-accounting is off."""
        from agentspecs.apps import APP_CATALOGUE, app_setup

        assert app_setup(APP_CATALOGUE["month-end-close"]) == [
            "The agent 'worker-month-end-close:0.0.1' is not enabled.",
            "The MCP server 'odoo-accounting:0.0.1' is not enabled.",
        ]
        assert app_setup(APP_CATALOGUE["crop-monitoring"]) == [
            "The agent 'worker-crop-monitoring:0.0.1' is not enabled.",
        ]
        assert app_setup(APP_CATALOGUE["event-response"]) == [
            "The agent 'worker-event-response:0.0.1' is not enabled.",
        ]
        for identity in ("disaster-assessment", "change-detection"):
            assert app_setup(APP_CATALOGUE[identity]) == [
                f"The agent 'worker-{identity}:0.0.1' is not enabled.",
            ]

    def test_earthdata_reads_its_searches_at_can_read(self):
        """Earthdata's tools are classed (read off its code): at *Can read* the two
        searches are done, and the download — which writes files — is left to the person."""
        from agentspecs.apps import APP_CATALOGUE, Behaviour, tool_behaviours

        for identity in ("crop-monitoring", "disaster-assessment", "change-detection"):
            behaviours = tool_behaviours(APP_CATALOGUE[identity])
            assert behaviours["earthdata.search_earth_datasets"] is Behaviour.DO_IT, identity
            assert behaviours["earthdata.search_earth_datagranules"] is Behaviour.DO_IT, identity
            assert behaviours["earthdata.download_earth_data_granules"] is Behaviour.LEAVE_TO_ME, (
                identity
            )
