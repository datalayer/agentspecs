# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Frames and Cogs: the catalogues load, and what each promises is checked.

A Frame is owned, scoped, inherited and composed; a Cog extends an agent and is
equipped with Frames. Each of those words is a check here.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml
from pydantic import ValidationError

from agentspecs.cogs import (
    COG_CATALOGUE,
    CogError,
    CogKind,
    cogs_using,
    get_cog,
    get_resolved_cog,
    list_cogs,
    resolve_cog,
)
from agentspecs.frames import (
    FRAME_CATALOGUE,
    FrameError,
    FrameScope,
    FrameSpec,
    GuardCategory,
    compose_frames,
    frame_lineage,
    get_frame,
    get_resolved_frame,
    list_frames,
    merge_lists,
    render_frames,
    resolve_frame,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent / "agentspecs"


def _ids(folder: str) -> set[str]:
    """Every spec of a catalogue, by id and by `id:version`."""
    known: set[str] = set()
    for path in (ROOT / folder).rglob("*.yaml"):
        spec = yaml.safe_load(path.read_text())
        known.add(spec["id"])
        known.add(f"{spec['id']}:{spec.get('version', '0.0.1')}")
    return known


def _frame(identity: str, **fields) -> dict:
    return {"id": identity, "name": identity, "scope": "team", "owner": "somebody", **fields}


class TestTheFrameCatalogue:
    def test_it_holds_the_frames_the_cogs_need(self):
        assert {"datalayer", "web-research", "sales-pipeline", "board-reporting", "customer-research"} <= set(
            FRAME_CATALOGUE
        )
        assert len(list_frames()) == len(FRAME_CATALOGUE)

    def test_a_frame_is_found_by_id_and_by_versioned_reference(self):
        assert get_frame("web-research").id == "web-research"
        assert get_frame("web-research:0.0.1").id == "web-research"
        assert get_frame("no-such-frame") is None

    @pytest.mark.parametrize("frame", list_frames(), ids=lambda frame: frame.id)
    def test_every_frame_is_owned_scoped_and_says_something(self, frame: FrameSpec):
        assert frame.owner.strip()
        assert isinstance(frame.scope, FrameScope)
        assert frame.description.strip()
        assert frame.rules, "a Frame with no rule orients nothing"

    @pytest.mark.parametrize("frame", list_frames(), ids=lambda frame: frame.id)
    def test_every_reference_of_a_frame_is_in_its_catalogue(self, frame: FrameSpec):
        for field, folder in (("skills", "skills"), ("tools", "tools"), ("mcp_servers", "mcp-servers")):
            for ref in getattr(frame, field):
                assert ref in _ids(folder), f"{frame.id}: {field} names {ref!r}, which is not in {folder}"
        if frame.extends:
            assert frame.extends in _ids("frames")

    def test_there_is_one_root_and_every_other_frame_reaches_it(self):
        roots = [frame.id for frame in list_frames() if not frame.extends]
        assert roots == ["datalayer"]
        for frame in list_frames():
            if frame.extends:
                assert frame_lineage(frame.id)[-1] == "datalayer"

    def test_a_guard_says_which_of_the_seven_categories_it_is(self):
        guards = [guard for frame in list_frames() for guard in frame.guards]
        assert guards
        assert {guard.category for guard in guards} <= set(GuardCategory)
        assert len(GuardCategory) == 7


class TestAFrameIsOwned:
    def test_a_frame_without_an_owner_is_refused(self):
        with pytest.raises(ValidationError):
            FrameSpec(**_frame("f", owner="  "))
        with pytest.raises(ValidationError):
            FrameSpec(id="f", name="F", scope="team")

    def test_a_scope_is_one_of_the_six(self):
        with pytest.raises(ValidationError):
            FrameSpec(**_frame("f", scope="planet"))

    def test_two_guards_of_one_frame_have_two_ids(self):
        guard = {"id": "g", "category": "algorithmic", "description": "d"}
        with pytest.raises(ValidationError):
            FrameSpec(**_frame("f", guards=[guard, guard]))


class TestAFrameInherits:
    def test_a_child_carries_what_its_parent_says_and_adds_its_own(self):
        company = get_frame("datalayer")
        resolved = get_resolved_frame("web-research")
        written = get_frame("web-research")
        assert resolved.rules[: len(company.rules)] == company.rules
        assert resolved.rules[len(company.rules) :] == written.rules
        assert set(company.terminology) < set(resolved.terminology)
        assert [guard.id for guard in resolved.guards][0] == "no-secrets"
        # Its own identity, not its parent's.
        assert (resolved.id, resolved.scope, resolved.owner) == (written.id, written.scope, written.owner)
        assert frame_lineage("web-research") == ["datalayer"]
        assert frame_lineage("datalayer") == []

    def test_lists_append_once_and_the_markers_say_otherwise(self):
        assert merge_lists(["a", "b"], ["b", "c"]) == ["a", "b", "c"]
        assert merge_lists(["a", "b"], ["!remove a", "c"]) == ["b", "c"]
        assert merge_lists(["a", "b"], ["!replace", "c"]) == ["c"]
        # A reference is the same entry whatever its version.
        assert merge_lists(["crawl:0.0.1"], ["crawl:0.0.2"]) == ["crawl:0.0.1"]
        assert merge_lists(["crawl:0.0.1"], ["!remove crawl"]) == []

    def test_a_term_and_a_guard_of_the_child_win(self):
        frames = {
            "p": _frame("p", terminology={"Deal": "old", "Lead": "kept"}, guards=[{"id": "g", "category": "expert", "description": "old", "required": True}]),
            "c": _frame("c", extends="p", terminology={"Deal": "new"}, guards=[{"id": "g", "category": "expert", "description": "new", "required": False}]),
        }
        resolved = resolve_frame(frames["c"], frames)
        assert resolved["terminology"] == {"Deal": "new", "Lead": "kept"}
        assert resolved["guards"] == [{"id": "g", "category": "expert", "description": "new", "required": False}]

    def test_a_cycle_is_refused_by_name(self):
        frames = {"a": _frame("a", extends="b"), "b": _frame("b", extends="a")}
        with pytest.raises(FrameError, match="a → b → a"):
            resolve_frame(frames["a"], frames)

    def test_a_chain_is_at_most_three_deep(self):
        frames = {
            "a": _frame("a", extends="b"),
            "b": _frame("b", extends="c"),
            "c": _frame("c", extends="d"),
            "d": _frame("d"),
        }
        # Project, department, company: three.
        assert resolve_frame(frames["b"], frames)["lineage"] == ["c", "d"]
        with pytest.raises(FrameError, match="deeper than 3"):
            resolve_frame(frames["a"], frames)

    def test_a_parent_that_does_not_exist_is_named(self):
        frames = {"a": _frame("a", extends="ghost:0.0.1")}
        with pytest.raises(FrameError, match="ghost:0.0.1"):
            resolve_frame(frames["a"], frames)


class TestFramesCompose:
    def test_two_frames_with_one_parent_bring_its_rules_once(self):
        context = compose_frames(["sales-pipeline:0.0.1", "board-reporting:0.0.1"])
        assert context.frames == ["sales-pipeline", "board-reporting"]
        assert context.lineage == ["datalayer", "sales-pipeline", "board-reporting"]
        company = get_frame("datalayer")
        for rule in company.rules:
            assert context.rules.count(rule) == 1
        assert [guard.id for guard in context.guards].count("no-secrets") == 1
        assert {"totals-reconcile", "summary-first"} <= {guard.id for guard in context.guards}
        assert set(context.owners) == set(context.lineage)

    def test_the_same_frame_twice_is_refused(self):
        with pytest.raises(FrameError, match="named twice"):
            compose_frames(["web-research", "web-research:0.0.1"])

    def test_the_rendered_context_says_who_owns_it_and_what_to_check(self):
        text = render_frames(compose_frames(["web-research"]))
        assert text.startswith("## Frames")
        assert "Web Research Frame — owned by Datalayer Research" in text
        for title in ("### Rules", "### Terminology", "### Goals", "### Style", "### Norms", "### Process", "### Guards"):
            assert title in text
        assert "**sources-cited** (source-grounding, required)" in text
        assert "1. Restate the question" in text
        # Capability is given, not told.
        assert "tavily" not in text
        assert render_frames(compose_frames([])) == ""


class TestTheCogCatalogue:
    def test_it_holds_the_three_worker_cogs(self):
        assert set(COG_CATALOGUE) == {"cog-crawler", "cog-sales-pipeline-board-report", "cog-customer-interviewer"}
        assert len(list_cogs()) == 3
        assert get_cog("cog-crawler:0.0.1").id == "cog-crawler"
        assert get_cog("no-such-cog") is None
        assert get_resolved_cog("no-such-cog") is None

    @pytest.mark.parametrize("cog", list_cogs(), ids=lambda cog: cog.id)
    def test_every_cog_extends_an_agent_and_names_frames_that_exist(self, cog):
        assert cog.extends in _ids("agents")
        assert cog.frames
        for ref in cog.frames:
            assert ref in _ids("frames")
        assert cog.kind is CogKind.CONTEXT
        assert cog.id not in _ids("agents")

    def test_each_extends_the_worker_the_issue_names(self):
        assert {cog.id: cog.extends.split(":")[0] for cog in list_cogs()} == {
            "cog-crawler": "worker-crawler",
            "cog-sales-pipeline-board-report": "worker-sales-pipeline-board-report",
            "cog-customer-interviewer": "worker-customer-interviewer",
        }

    def test_the_cogs_under_a_frame_are_found_through_inheritance_too(self):
        assert {cog.id for cog in cogs_using("datalayer")} == set(COG_CATALOGUE)
        assert [cog.id for cog in cogs_using("board-reporting:0.0.1")] == ["cog-sales-pipeline-board-report"]


class TestACogResolves:
    def test_it_is_the_agent_it_extends_with_what_it_says_differently(self):
        agent = yaml.safe_load((ROOT / "agents" / "worker-crawler.yaml").read_text())
        cog = get_resolved_cog("cog-crawler")
        assert cog["agent"] == "worker-crawler"
        for inherited in ("model", "harness", "sandbox_variant", "memory", "icon", "suggestions"):
            assert cog[inherited] == agent[inherited]
        assert cog["id"] == "cog-crawler" and cog["name"] == "Crawler Cog"
        assert cog["welcome_message"] != agent["welcome_message"]
        # A list appends: the agent's tags, then the Cog's.
        assert cog["tags"] == [*agent["tags"], "cog"]
        assert "extends" not in cog and "includes" not in cog

    def test_its_frames_give_it_capability_and_context(self):
        agent = yaml.safe_load((ROOT / "agents" / "worker-crawler.yaml").read_text())
        cog = get_resolved_cog("cog-crawler")
        assert cog["frames"] == ["web-research"]
        # The Frame's skill is added to the agent's, once.
        assert cog["skills"] == [*agent["skills"], "crawl:0.0.1"]
        assert cog["mcp_servers"] == ["tavily:0.0.1"]
        assert cog["system_prompt"].startswith(agent["system_prompt"].strip())
        assert "## Frames" in cog["system_prompt"]
        assert "Never present a search-result snippet" in cog["system_prompt"]
        context = cog["frame_context"]
        assert context["lineage"] == ["datalayer", "web-research"]
        assert [guard["id"] for guard in context["guards"]] == [
            "no-secrets",
            "sources-cited",
            "source-supports-claim",
            "recency-stated",
        ]

    def test_two_frames_compose_on_one_cog(self):
        cog = get_resolved_cog("cog-sales-pipeline-board-report")
        assert cog["frames"] == ["sales-pipeline", "board-reporting"]
        assert "Weighted pipeline" in cog["system_prompt"]
        assert "One page of summary first" in cog["system_prompt"]
        assert cog["system_prompt"].count("Never put a secret") == 1

    def test_a_cog_with_no_frame_is_refused(self):
        with pytest.raises(ValidationError, match="at least one Frame"):
            resolve_cog({"id": "c", "name": "C", "extends": "worker-crawler", "frames": []})

    def test_a_cog_extends_an_agent_that_exists_and_does_not_take_its_id(self):
        with pytest.raises(CogError, match="not an agent spec"):
            resolve_cog({"id": "c", "name": "C", "extends": "ghost:0.0.1", "frames": ["web-research"]})
        with pytest.raises(CogError, match="has the id of an agent"):
            resolve_cog({"id": "worker-crawler", "name": "C", "extends": "worker-crawler", "frames": ["web-research"]})

    def test_a_cog_naming_a_frame_that_does_not_exist_is_refused_by_name(self):
        with pytest.raises(CogError, match="ghost"):
            resolve_cog({"id": "c", "name": "C", "extends": "worker-crawler", "frames": ["ghost"]})
