# Copyright (c) 2025-2026 Datalayer, Inc.
#
# BSD 3-Clause License

"""Team specifications.

A *team* is several agents working on one job. This module defines the
``TeamSpec`` Pydantic class and the helpers for loading team definitions from
YAML, the same way ``strategies``, ``memory`` and ``models`` do for theirs — teams
were the one catalogue with no schema at all, which meant nothing checked them
and nothing could load them.

Two ideas carry the design.

**A team composes agents that already exist.** A member names one with ``ref``,
pointing into the agent catalogue exactly as a subagent does
(``jupyter-notebook-compactor:0.0.1``). The alternative — restating a name, a
model, a goal and a list of tools inline — is what the first teams did, and it
produced members that looked like agents, could not be resolved to one, and
drifted from the real spec the moment either changed. A member may still be
defined inline, for a role that exists only inside this team; it simply has no
``ref``.

**The order of work is data, not prose.** ``depends_on`` names the members that
must finish first, so a runtime can compute the order, run independent members
at once, and refuse a team whose graph has a cycle. It replaces sentences like
"On completion of the Triage Agent", which read well and cannot be executed.

**A team may compose applications too.** A member names one with ``app``,
pointing into the application catalogue, and is then that application — its
agent, its connections, its rules, its interface. Such a team says where each
member's loop turns (``runs_in``: the person's browser or a runtime), who asks
whom while the work runs (``talks_to``, over A2A) and which member a person
talks to (``entry``).

Subagents work here as they do on an agent: a member may delegate to
specialists, and ``delegation`` bounds how far that can go for the team as a
whole.

**A scene is a team** (LOOP A-04, decided 2026-10-07). Agents arranged with
their roles, their shared context and their interactions are a team and
nothing else: a team may hold one member — an agent working alone with its
data is a scene — and never none; each member names its ``role``; the team
names its shared ``context`` — how much of the conversation each member is
told, and the Frames they all work under (``agentspecs.frames``); and each
link names its protocol: ``a2a`` to an agent or an application, ``mcp`` to a
member that is an MCP server (``server``), a system of the scene the others
reach tool by tool. A member that talks to one not in the team, and a team
with no member, are refused when the catalogue loads.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class TeamRole(str, Enum):
    """What a member is *for*, structurally.

    Deliberately about position in the work rather than about subject matter: a
    team of analysts and a team of reviewers have the same shape, and a runtime
    scheduling them cares which member opens the work and which closes it, not
    what the work is about.
    """

    COORDINATOR = "coordinator"
    """Routes work to the others and decides when the team is done."""

    INITIATOR = "initiator"
    """Opens the work: takes the request and produces the first result."""

    CONTRIBUTOR = "contributor"
    """Carries the work forward a step."""

    REVIEWER = "reviewer"
    """Checks another member's output and can send it back."""

    FINALIZER = "finalizer"
    """Produces what the team hands back."""


class TeamApproval(str, Enum):
    """Whether a member's output needs a person before it counts."""

    AUTO = "auto"
    MANUAL = "manual"


class TeamExecutionMode(str, Enum):
    """How the members are run."""

    SEQUENTIAL = "sequential"
    """One after another, in declaration order."""

    PARALLEL = "parallel"
    """All at once; nothing waits for anything."""

    GRAPH = "graph"
    """In the order `depends_on` implies — parallel where the graph allows."""

    SUPERVISOR = "supervisor"
    """The supervisor decides who runs next, each turn."""


class TeamPlace(str, Enum):
    """Where a member's loop turns.

    A team of applications can be split between the person's page and a
    runtime: what reads the person's screen and talks to them turns in their
    browser, what reaches a company's systems turns on a runtime, where its
    connections and its credentials are.
    """

    BROWSER = "browser"
    """In the person's browser: the in-browser target the Preview and `loop` use."""

    RUNTIME = "runtime"
    """On a runtime: a cloud runtime on Datalayer, or a local one."""


class TeamProtocol(str, Enum):
    """How one member talks to another."""

    A2A = "a2a"
    """The Agent2Agent protocol: the member talked to is served over A2A, and
    its agent card says what it may be asked and how it answers."""

    MCP = "mcp"
    """The Model Context Protocol: the member talked to is an MCP server
    (`server`), asked tool by tool; its tools say what it does."""


class TeamSharing(str, Enum):
    """How much of the conversation each member is told."""

    SHARED = "shared"
    """One thread, and every member is sent all of it: what a supervisor
    team wants, since routing only makes sense when the member receiving the
    work can see what was already said."""

    ISOLATED = "isolated"
    """A thread per member: the child runs blind and returns a result, as a
    delegation model wants."""

    OWN_TURNS = "own-turns"
    """One thread on screen, but each member is sent only the turns it took
    part in."""


class TeamContext(BaseModel):
    """What the members share: the conversation, and the context they work in.

    A scene's shared context (LOOP A-04): how much of the conversation each
    member is told (`sharing`), and the Frames — the rules, the vocabulary,
    the goals, the style and the norms of the organization, the department,
    the project (`agentspecs.frames`) — every member works under (`frames`),
    in order, as a Cog names its own. A member's own Frames (its application's
    `context`) come on top of the team's.
    """

    sharing: TeamSharing = Field(
        default=TeamSharing.SHARED,
        description=(
            "How much of the conversation each member is given: `shared` (all of it), "
            "`isolated` (its own thread) or `own-turns` (one thread, only its own turns)"
        ),
    )
    frames: List[str] = Field(
        default_factory=list,
        description="The Frames every member works under, in order, `id` or `id:version`",
    )

    @field_validator("frames")
    @classmethod
    def _named_once(cls, frames: List[str]) -> List[str]:
        seen = set()
        for ref in frames:
            identity = ref.split(":")[0]
            if not identity:
                raise ValueError("a Frame of the team's context is named by its id")
            if identity in seen:
                raise ValueError(f"the Frame {identity!r} is named twice in the team's context")
            seen.add(identity)
        return frames


class TeamLink(BaseModel):
    """One member asking another, directly, over a protocol.

    Distinct from `depends_on`, which orders work: a link says who may ask
    whom while the work runs, in either order and as often as it needs.
    """

    member: str = Field(..., description="The member asked, by its id in this team")
    over: TeamProtocol = Field(
        default=TeamProtocol.A2A,
        description=(
            "The protocol it is asked over: `a2a` to an agent or an application, `mcp` to a server"
        ),
    )


class TeamSubagent(BaseModel):
    """A specialist one member may hand work to.

    The same shape as the ``subagents`` entry on an agent spec, deliberately:
    delegation is one idea, and a subagent declared on a team member should be
    written the way it is written anywhere else.
    """

    name: str = Field(
        ...,
        description="How the member addresses it (e.g. `@CellFixer`)",
    )
    ref: str = Field(
        default="",
        description="Agent catalogue reference, `id` or `id:version`. Empty for an inline subagent defined by `instructions`.",
    )
    description: str = Field(
        default="",
        description="What it is for, and when to reach for it. Read by the delegating model, so write it for one.",
    )
    instructions: str = Field(
        default="",
        description="System prompt for a subagent that exists only here. Ignored when `ref` is set.",
    )

    @model_validator(mode="after")
    def _needs_a_definition(self) -> "TeamSubagent":
        if not self.ref and not self.instructions:
            raise ValueError(
                f"subagent {self.name!r} needs either `ref` (an agent from the "
                f"catalogue) or `instructions` (one defined here)"
            )
        return self


class TeamDelegation(BaseModel):
    """How far members may hand work to each other, and to subagents."""

    max_depth: int = Field(
        default=2,
        ge=0,
        description="How many levels of delegation are allowed. 0 forbids it entirely.",
    )
    allow_peer_delegation: bool = Field(
        default=False,
        description="Whether a member may hand work to another member of the same team, rather than only to its own subagents.",
    )
    include_general_purpose: bool = Field(
        default=False,
        description="Whether members also get the general-purpose subagent, for work no specialist covers.",
    )


class TeamMember(BaseModel):
    """One agent's place in a team.

    Prefer `ref`. A member that names a catalogue agent inherits its model,
    tools, prompt and its own subagents; the fields here then say what is
    different *about this member in this team* — what it is for, what it waits
    for, whether a person signs off its output.
    """

    id: str = Field(..., description="Identity within the team; what `depends_on` names")
    ref: str = Field(
        default="",
        description="Agent catalogue reference, `id` or `id:version`",
    )
    app: str = Field(
        default="",
        description=(
            "Application catalogue reference, `id` or `id:version`, in place of "
            "`ref`: the member is that application, with its agent, its "
            "connections, its rules and its interface."
        ),
    )
    server: str = Field(
        default="",
        description=(
            "MCP server catalogue reference, `id` or `id:version`, in place of "
            "`ref` and `app`: the member is that server, a system of the scene "
            "the other members reach over MCP (`talks_to` … `over: mcp`). It "
            "answers tool by tool and asks nobody."
        ),
    )
    runs_in: Optional[TeamPlace] = Field(
        default=None,
        description="Where its loop turns: `browser` or `runtime`. Unsaid, wherever the team runs.",
    )
    talks_to: List[TeamLink] = Field(
        default_factory=list,
        description="The members it asks directly while it works, and over what",
    )
    name: str = Field(
        default="",
        description=(
            "Display name. Falls back to the referenced agent or application, then to `id`."
        ),
    )
    role: TeamRole = Field(
        default=TeamRole.CONTRIBUTOR,
        description="What this member is for, structurally",
    )
    goal: str = Field(
        default="",
        description="What this member is asked to achieve, in this team",
    )
    depends_on: List[str] = Field(
        default_factory=list,
        description="Member ids that must finish first. Empty means it can start immediately.",
    )
    trigger: str = Field(
        default="",
        description=(
            "What starts this member from *outside* the team — an event, a "
            "schedule, a webhook. Distinct from `depends_on`, which is what it "
            "waits for inside. The two used to be one prose field, so "
            "'Event: new ticket received' and 'On completion of the Triage "
            "Agent' were the same kind of thing to a reader and neither was "
            "the same kind of thing to a runtime."
        ),
    )
    approval: TeamApproval = Field(
        default=TeamApproval.AUTO,
        description="Whether a person signs off this member's output",
    )
    subagents: List[TeamSubagent] = Field(
        default_factory=list,
        description="Specialists this member may hand work to",
    )

    # -- Overrides -----------------------------------------------------------
    #
    # A member with a `ref` inherits these from the agent it names; setting one
    # here overrides it for this team. A member without a `ref` is defined by
    # them.
    model: str = Field(default="", description="Model id, overriding the agent's")
    mcp_server: str = Field(
        default="",
        description="MCP server, overriding the agent's",
        alias="mcpServer",
    )
    tools: List[str] = Field(default_factory=list, description="Tools, overriding the agent's")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _needs_a_definition(self) -> "TeamMember":
        if sum(1 for given in (self.ref, self.app, self.server) if given) > 1:
            raise ValueError(
                f"member {self.id!r} is an agent (`ref`), an application (`app`) "
                f"or a server (`server`), not two of them"
            )
        if not self.ref and not self.app and not self.server and not self.name and not self.goal:
            raise ValueError(
                f"member {self.id!r} needs a `ref` into the agent catalogue, an "
                f"`app` from the application catalogue, a `server` from the MCP "
                f"server catalogue, or enough of its own definition (`name`, "
                f"`goal`) to stand alone"
            )
        if self.server:
            if self.talks_to:
                raise ValueError(
                    f"member {self.id!r} is a server: it answers over MCP and asks nobody"
                )
            if self.subagents:
                raise ValueError(f"member {self.id!r} is a server: it has no subagent")
        return self

    @property
    def is_server(self) -> bool:
        """Whether the member is an MCP server of the scene, asked over MCP."""
        return bool(self.server)

    @property
    def display_name(self) -> str:
        """What to show a person: the name, what it references, or the id."""
        return self.name or (self.ref or self.app or self.server).split(":")[0] or self.id


class TeamSupervisor(BaseModel):
    """The agent that routes work within a team.

    Required. A team is not a list of agents — it is a list of agents plus
    someone deciding what happens next, and a spec that leaves that out
    describes a set, not a team. Where the answer is "they simply run in
    order", that is still a decision, and naming the agent that owns it is
    what makes the team inspectable: a person reading the spec can see who
    to ask why a member ran.
    """

    name: str = Field(..., description="Display name")
    ref: str = Field(
        default="",
        description=(
            "Agent catalogue reference, `id` or `id:version`. A supervisor is "
            "an agent like any other; naming one from the catalogue means its "
            "prompt, tools and subagents are defined in one place rather than "
            "restated here."
        ),
    )
    app: str = Field(
        default="",
        description=(
            "Application catalogue reference, `id` or `id:version`: in a team "
            "of applications, the one that decides who is asked next, usually "
            "the team's `entry`."
        ),
    )
    model: str = Field(
        default="",
        description="Model id, overriding the referenced agent's",
    )
    goal: str = Field(
        default="",
        description="What the supervisor is accountable for across the whole run",
    )
    instructions: str = Field(
        default="",
        description=(
            "Supervision prompt, for a supervisor defined only here. Ignored "
            "when `ref` is set — the referenced agent brings its own."
        ),
    )
    approval: TeamApproval = Field(
        default=TeamApproval.AUTO,
        description="Whether a person signs off the supervisor's routing decisions",
    )
    can_terminate: bool = Field(
        default=True,
        description=(
            "Whether the supervisor may end the run before every member has "
            "gone. False makes it a router only, which is what a team wants "
            "when every member must contribute."
        ),
    )

    @model_validator(mode="after")
    def _has_a_definition(self) -> "TeamSupervisor":
        if self.ref and self.app:
            raise ValueError(
                f"supervisor {self.name!r} is an agent (`ref`) or an application (`app`), not both"
            )
        if not self.ref and not self.app and not self.instructions and not self.model:
            raise ValueError(
                f"supervisor {self.name!r} needs a `ref` into the agent "
                f"catalogue, an `app` from the application catalogue, or a "
                f"`model` and `instructions` of its own"
            )
        return self


class TeamValidation(BaseModel):
    """Limits on a team run."""

    timeout: Optional[str] = Field(
        default=None, description="Wall-clock limit for the whole run, e.g. `180s`"
    )
    retry_on_failure: bool = Field(default=False)
    max_retries: int = Field(default=0, ge=0)


class TeamReactionRule(BaseModel):
    """What the team does when something happens mid-run."""

    id: str = Field(...)
    trigger: str = Field(..., description="The condition, by name")
    action: str = Field(..., description="What to do about it")
    auto: bool = Field(default=True, description="Whether it happens without a person")
    max_retries: int = Field(default=0, ge=0)
    escalate_after_retries: int = Field(default=0, ge=0)
    priority: str = Field(default="medium")


class TeamHealthMonitoring(BaseModel):
    """When a member is considered late, stuck, or gone."""

    heartbeat_interval: str = Field(default="15s")
    stale_threshold: str = Field(default="60s")
    unresponsive_threshold: str = Field(default="180s")
    stuck_threshold: str = Field(default="300s")
    max_restart_attempts: int = Field(default=3, ge=0)


class TeamNotifications(BaseModel):
    """When the team tells somebody what it is doing."""

    on_start: bool = Field(default=False)
    on_completion: bool = Field(default=True)
    on_failure: bool = Field(default=True)
    on_escalation: bool = Field(default=True)


class TeamOutput(BaseModel):
    """What the team produces, and where it goes."""

    formats: List[str] = Field(default_factory=list)
    template: str = Field(default="")
    storage: str = Field(default="")


class TeamSuggestion(BaseModel):
    """An opener offered at a team's front door.

    Text and, optionally, a mark to show beside it. The same shape an agent's
    suggestions have, deliberately: a caller listing what can be asked should
    not have to know whether it is looking at a team or at one of its members.
    Both marks are optional and independent — an octicon for chrome drawn in
    line art, an emoji for somewhere with colour.
    """

    text: str = Field(..., description="What is sent when the suggestion is taken")
    icon: Optional[str] = Field(default=None, description="Octicon name to show beside it")
    emoji: Optional[str] = Field(default=None, description="Unicode emoji to show beside it")


class TeamSpec(BaseModel):
    """Specification for a team of agents."""

    id: str = Field(..., description="Unique team identifier")
    version: str = Field(default="0.0.1", description="Team spec version")
    name: str = Field(..., description="Display name")
    description: str = Field(default="", description="What the team is for")
    tags: List[str] = Field(default_factory=list)
    enabled: bool = Field(default=True)

    icon: str = Field(default="people", description="Icon identifier")
    emoji: str = Field(default="\U0001f465", description="Emoji representation")
    color: str = Field(default="", description="Accent colour")

    agent_spec_id: str = Field(
        default="",
        description="The agent spec this team was extracted from, when it was",
    )
    orchestration_protocol: str = Field(default="datalayer")
    execution_mode: TeamExecutionMode = Field(default=TeamExecutionMode.SEQUENTIAL)
    supervisor: TeamSupervisor = Field(
        ...,
        description="Who decides what happens next. Every team has one.",
    )
    routing_instructions: str = Field(default="")
    entry: str = Field(
        default="",
        description=(
            "The member a person talks to, by its id: the team's front door. "
            "Unsaid, the supervisor answers first."
        ),
    )
    suggestions: List[TeamSuggestion] = Field(
        default_factory=list,
        description=(
            "Openers shown in an empty chat, so a person arriving at a team "
            "sees what it can be asked rather than an empty box. At the team "
            "level because they describe the team's front door: the "
            "supervisor answers first, and what it is worth asking is a "
            "property of the whole team rather than of any one member."
        ),
    )
    context: TeamContext = Field(
        default_factory=TeamContext,
        description=(
            "What the members share: how much of the conversation each is told, "
            "and the Frames they all work under"
        ),
    )
    delegation: TeamDelegation = Field(default_factory=TeamDelegation)
    validation: Optional[TeamValidation] = Field(default=None)

    agents: List[TeamMember] = Field(
        default_factory=list,
        description="The members, in declaration order: one at least",
    )

    reaction_rules: List[TeamReactionRule] = Field(default_factory=list)
    health_monitoring: Optional[TeamHealthMonitoring] = Field(default=None)
    notifications: Optional[TeamNotifications] = Field(default=None)
    output: Optional[TeamOutput] = Field(default=None)

    @field_validator("agents")
    @classmethod
    def _members_are_uniquely_named(cls, members: List[TeamMember]):
        if not members:
            # A scene can hold a single agent; it cannot hold none.
            raise ValueError("a team has no member: it holds one at least")
        seen = set()
        for member in members:
            if member.id in seen:
                raise ValueError(f"duplicate member id {member.id!r}")
            seen.add(member.id)
        return members

    @model_validator(mode="after")
    def _dependencies_resolve_and_terminate(self) -> "TeamSpec":
        """Every `depends_on` names a member of this team, and the graph ends.

        Checked here rather than left to a runtime because a team whose graph
        does not resolve has no correct execution at all — and a cycle
        discovered at run time is discovered with a model already loaded and a
        person waiting. Every link, too: who it asks is a member of the team,
        and the protocol fits who is asked — a server over MCP, an agent or an
        application over A2A.
        """
        ids = {member.id for member in self.agents}
        servers = {member.id for member in self.agents if member.is_server}
        if self.entry and self.entry not in ids:
            raise ValueError(f"team {self.id!r} enters at {self.entry!r}, which is not a member")
        if self.entry in servers:
            raise ValueError(
                f"team {self.id!r} enters at {self.entry!r}, a server: "
                "a person talks to an agent or an application"
            )
        for member in self.agents:
            for link in member.talks_to:
                self._link_fits(member, link, ids, servers)
            for needed in member.depends_on:
                if needed not in ids:
                    raise ValueError(
                        f"member {member.id!r} depends on {needed!r}, which is "
                        f"not a member of team {self.id!r}"
                    )
            if member.id in member.depends_on:
                raise ValueError(f"member {member.id!r} depends on itself")
        # Resolving the order is the cycle check: it raises when one is left.
        self.execution_order()
        return self

    def _link_fits(self, member: TeamMember, link: TeamLink, ids: set, servers: set) -> None:
        """A link names another member of the team, over the protocol that fits it."""
        if link.member not in ids:
            raise ValueError(
                f"member {member.id!r} talks to {link.member!r}, which is "
                f"not a member of team {self.id!r}"
            )
        if link.member == member.id:
            raise ValueError(f"member {member.id!r} talks to itself")
        if link.over is TeamProtocol.MCP and link.member not in servers:
            raise ValueError(
                f"member {member.id!r} talks to {link.member!r} over mcp, "
                f"which is not a server: an agent or an application is asked over a2a"
            )
        if link.over is not TeamProtocol.MCP and link.member in servers:
            raise ValueError(
                f"member {member.id!r} talks to {link.member!r} over {link.over.value}, "
                f"which is a server: a server is asked over mcp"
            )

    def execution_order(self) -> List[List[str]]:
        """The members in the order they may run, grouped by what can run at once.

        Each group depends only on the groups before it, so a runtime can run a
        whole group in parallel. A sequential team simply yields groups of one.

        Raises:
            ValueError: if the dependencies contain a cycle.
        """
        remaining = {member.id: set(member.depends_on) for member in self.agents}
        # Declaration order is the tie-break, so the answer is stable rather
        # than whatever the set happened to iterate.
        order = [member.id for member in self.agents]
        groups: List[List[str]] = []
        while remaining:
            ready = [name for name in order if name in remaining and not remaining[name]]
            if not ready:
                stuck = ", ".join(sorted(remaining))
                raise ValueError(f"team {self.id!r} has a dependency cycle among: {stuck}")
            groups.append(ready)
            for name in ready:
                del remaining[name]
            for pending in remaining.values():
                pending.difference_update(ready)
        return groups

    def member(self, member_id: str) -> Optional[TeamMember]:
        """One member by id."""
        for candidate in self.agents:
            if candidate.id == member_id:
                return candidate
        return None

    def referenced_agents(self) -> List[str]:
        """Every agent this team names — members and their subagents.

        What a host needs to know it can actually run this team: the catalogue
        entries that have to exist, in one list, without walking the spec.
        """
        refs: List[str] = []
        for member in self.agents:
            if member.ref:
                refs.append(member.ref)
            for subagent in member.subagents:
                if subagent.ref:
                    refs.append(subagent.ref)
        if self.supervisor and self.supervisor.ref:
            refs.append(self.supervisor.ref)
        # Order preserved, duplicates dropped.
        return list(dict.fromkeys(refs))

    def referenced_apps(self) -> List[str]:
        """Every application this team names — its members and its supervisor.

        A team of applications composes them as a team of agents composes
        agents: by reference, so that each application stays the one of the
        catalogue, with its rules and its connections.
        """
        refs = [member.app for member in self.agents if member.app]
        if self.supervisor and self.supervisor.app:
            refs.append(self.supervisor.app)
        return list(dict.fromkeys(refs))

    def referenced_servers(self) -> List[str]:
        """Every MCP server this team names as a member: the systems of the scene."""
        return list(dict.fromkeys(member.server for member in self.agents if member.server))

    def referenced_frames(self) -> List[str]:
        """Every Frame of the team's shared context, in order."""
        return list(self.context.frames)

    def links(self) -> List[Tuple[str, str, TeamProtocol]]:
        """Every interaction of the scene, in order: (who asks, who is asked, over what)."""
        return [
            (member.id, link.member, link.over)
            for member in self.agents
            for link in member.talks_to
        ]


def _load_team_specs() -> List[TeamSpec]:
    """Load every team YAML in this directory."""
    teams_dir = Path(__file__).parent
    specs: List[TeamSpec] = []
    for yaml_file in sorted(teams_dir.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        try:
            specs.append(TeamSpec(**data))
        except Exception as error:
            # Name the file. A validation error on a bare field path is a
            # puzzle when the catalogue is a directory of them.
            raise ValueError(f"{yaml_file.name}: {error}") from error
    return specs


def _build_enum() -> type:
    """Build the Teams enum from the YAML specs."""
    members = {spec.id.replace("-", "_").upper(): spec.id for spec in _load_team_specs()}
    return Enum("Teams", members, type=str)


TEAM_CATALOGUE: List[TeamSpec] = _load_team_specs()

Teams = _build_enum()


def get_team(team_id: str) -> Optional[TeamSpec]:
    """Get a team specification by id.

    Args:
        team_id: The unique team identifier.

    Returns:
        The TeamSpec, or None if not found.
    """
    for team in TEAM_CATALOGUE:
        if team.id == team_id:
            return team
    return None


def list_teams(tag: Optional[str] = None) -> List[TeamSpec]:
    """List team specifications, optionally filtered by tag.

    Args:
        tag: Only teams carrying this tag.

    Returns:
        The matching TeamSpec specifications.
    """
    if tag is None:
        return list(TEAM_CATALOGUE)
    return [team for team in TEAM_CATALOGUE if tag in team.tags]


def teams_using(agent_ref: str) -> List[TeamSpec]:
    """Every team that names this agent, as a member or as a subagent.

    The question asked when an agent spec is about to change: who depends on
    this? Matches on the bare id as well as `id:version`, because a team may
    pin a version and the agent being changed is the same agent either way.

    Args:
        agent_ref: An agent id, with or without a version.

    Returns:
        The teams that reference it.
    """
    wanted = agent_ref.split(":")[0]
    return [
        team
        for team in TEAM_CATALOGUE
        if any(ref.split(":")[0] == wanted for ref in team.referenced_agents())
    ]
