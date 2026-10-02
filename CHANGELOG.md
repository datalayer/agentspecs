<!--
  ~ Copyright (c) 2025-2026 Datalayer, Inc.
  ~
  ~ BSD 3-Clause License
-->

# Changelog

## 0.0.15

Applications, and what a tool does to the world.

- Applications: a new spec, the **Appspec**, under `agentspecs/apps/` (`schema: loop.app/v1`).
  An application is an agent with an interface, rules, tests and a place to run; four
  kinds — `chat`, `widget`, `decision`, `worker` — and one spec. It stands alone: it is not
  an Op, and Guards, Gates and a Track are optional, under `checks`.
- Rules in four behaviours — `do_it`, `if_asked`, `ask_first`, `leave_to_me` — written in a
  person's words (`action`) and applied to a class of action or to named tools
  (`applies_to`). `behaviour_for` says what an application does when its agent calls a
  tool: with no rule, reading is done and anything that acts waits for a person.
- Connections: an application reaches nothing it does not name. Each says how far (`read`,
  `write`), in whose name (`owner`, `user`), and optionally which tools (`only`).
- **Action classes** (`agentspecs.actions`): `read`, `write`, `send`, `buy`, `delete`,
  `publish`. Every tool of `tools/` now carries `action`; every MCP server carries
  `actions`. Five servers were read off the running server and classed — Tavily, the
  filesystem, charts, Slack and Google Workspace's 120 tools; the nine others say
  `checked: null` and class nothing. A tool with no class is unknown, and unknown is the
  most restricted; a server's own `readOnlyHint` is not read.
- What is wrong is said in a sentence (`AppError`), by the name of the field; a key the
  spec does not know is refused. `app_problems` for references that do not resolve,
  `app_setup` for what is named and not enabled.
- The JSON Schema of the Appspec is published at `agentspecs/apps/appspec.schema.json`,
  and a test keeps it current.
- Four applications, one of each kind: `web-research`, `quote-calculator`, `ship-or-fix`,
  `inbox-triage`.
- `agentspecs.apps`, `agentspecs.actions`. Documentation: a section for applications,
  with the action classes and a page on when a rule is enough and when a Gate is needed.

## 0.0.14

The rest of the whitepaper's execution and accountability model (#20).

- Guards: a new spec, under `agentspecs/guards/`. **A Guard extends a guardrail** — the
  policy it verifies — by the extension mechanism, and adds its `category` (the seven of
  the whitepaper), the `stages` of an Op it runs at (pre-flight, in-flight, post-run,
  continuous), its `method` (code, a Cog, a person), what it `check`s and the `signals` it
  reports. Resolved, it carries the guardrail's permissions, data scope and handling, and
  limits. Twelve Guards, of every category and stage.
- Gates: a new spec, under `agentspecs/gates/`. A Gate reads `guards`, and decides: `when`
  a condition on their signals holds (or `always`), `then` one of nine actions — proceed,
  pause, retry, more validation, human review, human approval, expert review, stop, stop
  and escalate. A condition that cannot be read, or reads a signal no Guard reports, is
  refused; a Gate that hands over to a person names its `reviewers`. Eight Gates.
- Tracks: a new spec, under `agentspecs/tracks/`: what a record has to `include`, how long
  it is retained (`retain_for`), who may read it. Never exchangeable. `standard` (one year)
  and `financial-reporting` (everything, seven years).
- Ops: a new spec, under `agentspecs/ops/`: an owner, the Cogs that do the work, workflow
  Frames, a supervisor, and a **validation strategy** — Guards by stage, Gates, a Track. An
  Op with no post-run Guard, no Gate or no Track is refused, as is one whose Gate reads a
  Guard it does not run or decides before that Guard has run.
- `op-sales-pipeline-board-report` is the comprehensive example: one Cog with its Frames,
  twelve Guards, eight Gates and a seven-year Track.
- `agentspecs.ops`, `agentspecs.guards`, `agentspecs.gates`, `agentspecs.tracks`.
- Documentation: a section for each, the example walked through under Ops, and what a
  Guard adds to a guardrail on the guardrails page.

## 0.0.13

What the review of 0.0.12 asked.

- Frames: composing several Frames merges every contributor **once**, from the root down.
  0.0.12 merged each named Frame already resolved, so a parent two Frames share was replayed
  for the second, and its copy of a term or a Guard undid what the first had said about it.
- Frames: a resolved Frame carries its `lineage` (`get_resolved_frame(...).lineage`), as the
  documentation said. `lineage` is computed; a spec that writes one is refused.
- Cogs: a Cog of kind `model` or `combined` is refused when resolved. 0.0.12 resolved it as a
  `context` Cog, which is not what it says it is.
- Cogs: the agent, fragment and Frame catalogues are read once. 0.0.12 parsed every agent
  YAML again for each `resolve_cog` and each `get_resolved_cog`. What is returned is a copy.
- Extension: a parent's `!replace` and `!remove` reach what the child's fragments brought in
  — the documented order, fragments first and the parent second — whether the parent says
  them itself or brings them in through a fragment of its own. Before, the parent's
  markers were consumed when the parent was resolved, and a fragment's entries survived a
  parent that replaced the list.

## 0.0.12

- Frames: a new spec, under `agentspecs/frames/`. A Frame is the context work happens in,
  written down — rules, terminology, goals, style, norms, process, architecture, prompts —
  with the skills, tools and MCP servers the work depends on and the **Guards** its output
  has to pass, in the whitepaper's seven categories. It names its `scope` (organization,
  department, team, project, role or relationship) and its `owner`, both required. The
  concept is the Intelligence Hub whitepaper's.
- Frames inherit with `extends`, by the extension mechanism agents use — one parent, three
  deep at most, a cycle refused by name — and several compose in order. Five Frames:
  `datalayer` (the company Frame, the root), `web-research`, `sales-pipeline`,
  `board-reporting` and `customer-research`.
- Cogs: a new spec, under `agentspecs/cogs/`. A Cog **extends an agent spec** and is
  **equipped with Frames**. Resolved, it is the agent with the Cog's changes, the Frames'
  skills, tools and MCP servers added to the agent's and their context rendered onto its
  system prompt, plus `agent`, `frames`, `kind` and `frame_context` (the lineage, the
  owners and the Guards). Three Cogs: `cog-crawler` (extends `worker-crawler`, enabled),
  `cog-sales-pipeline-board-report` and `cog-customer-interviewer`.
- `agentspecs.frames` and `agentspecs.cogs` load, validate and resolve the two catalogues;
  `agentspecs.compose` is the `extends` / `includes` resolution, which lived only in
  agent-runtimes' code generation.
- Documentation: Frames and Cogs each have a section; Extension says how both use it; the
  README lists every catalogue with its current count.

## 0.0.11

- UI plugins: what was called a *UI extension* is a **UI plugin**. One spec per plugin
  under `agentspecs/ui-plugins/` (`a2ui`, `mcp-apps`, `mcp-ui`) — its name, what it renders,
  the protocol's documentation and whether it is enabled.
- Agents: the field `ui_extension` is renamed `ui_plugin` in every agent spec. **A rename
  of a field**: a consumer that reads `ui_extension` reads nothing from 0.0.11 on.
- Agents: four agent specs are enabled — `example-simple` (A Simple Agent), `worker-crawler`
  (Crawler Agent), `jupyter-notebook-compactor` (Jupyter Notebook Compactor) and
  `example-one-trigger` (Example Once Trigger Agent). Every other agent spec stays in the
  catalogue with `enabled: false`: listed, and not offered.
- Models: of the Cloudflare models, only Jev is offered — `cloudflare:gtw/typesafe/jev` and
  `cloudflare:wrk/typesafe/jev`. The six Workers AI chat models stay in the catalogue with
  `available: false`.
- MCP servers: `tavily` (Tavily Search) and `earthdata` (Earthdata MCP) are enabled; the
  others stay listed and not offered.
- Events: specs for the kinds agent-runtimes emits and had none for — `agent-output` (a
  triggered run or a chat turn produced its output), `agent-assigned` (a runtime was given
  its agent) and `generic` (the kind of an event created with none).
- Outputs: `csv` and `json` are enabled; the others stay listed and not offered.
- Skills: `crawl` (Web Crawl Skill) is enabled; the others stay listed and not offered.
- Memory: a spec says whether it is `enabled`. `mem0` is; `ephemeral`, `memu` and `simplemem`
  stay listed and not offered.

## 0.0.10

- Model providers: one spec per provider under `agentspecs/model-providers/` (Anthropic,
  Amazon Bedrock, OpenAI, Azure OpenAI, Alibaba Cloud Model Studio, Cloudflare, Ollama) —
  its site, its documentation, its terms of service, its privacy policy, what it says
  about the data a request carries, and whether it runs the model or the user's machine
  does. `agentspecs.model_providers`; a model naming a provider with no spec is refused.
- Models: `provider_url`, the page on the provider's site that describes the model, on
  every spec.
- Models: the six Cloudflare chat models renamed in 0.0.9 (`cloudflare:<vendor>/<model>` →
  `cloudflare:wrk/<vendor>/<model>`) keep their older id as an `aliases` entry: `get_model`
  answers it and the `AIModels` enum keeps the older member with the older value, so a
  consumer that named a model before its id moved still finds it. 0.0.9 was a catalogue
  migration and should have said so.
- Models: `zero_data_retention` is the model provider's retention and nothing else;
  `request_logging` (`none` or `gateway`) says where the route keeps a log of the
  request. Jev through AI Gateway is ZDR at Typesafe and logged at the gateway; Jev at
  Workers AI's endpoint is ZDR and unlogged. A route for sensitive data is chosen on both.
- Models: a `route` is Cloudflare's endpoint, not a kind of model — `workers-ai` is Workers
  AI's own endpoint, which serves the `@cf/` models and the third-party ones it fronts
  alike; `ai-gateway` is through the gateway. The catalogue refuses, when it loads, a
  Cloudflare model whose id, file name and `route` disagree, a Cloudflare id with no
  flavour, and a route on any other provider's model. `pricing` requires both prices,
  non-negative and finite.

## 0.0.9

- Models: Jev, Typesafe's typed-judgment model, in the catalogue once per Cloudflare route —
  `cloudflare:gtw/typesafe/jev` and `cloudflare:wrk/typesafe/jev` — with the
  capability `judgments`; `gpt-oss-120b` and Claude Sonnet 4.6 carry `judge`, a chat model
  that may be asked the same questions.
- Models: `route` (`workers-ai` or `ai-gateway`) says which Cloudflare product a model is
  reached through; `context_window`, `zero_data_retention` and `pricing` (dollars per
  million tokens) are typed fields a service can meter and choose by. The capability
  vocabulary and the routes are checked when the catalogue loads.
- The Cloudflare ids and spec files carry the flavour: `cloudflare:wrk/<vendor>/<model>`
  in `cloudflare-wrk-*.yaml` (Workers AI) and `cloudflare:gtw/<vendor>/<model>` in
  `cloudflare-gtw-*.yaml` (AI Gateway). The six chat models were `cloudflare:<vendor>/<model>`;
  datalayer-ai-inference still accepts that spelling as the Workers AI flavour.

## 0.0.8

- Models: Cloudflare Workers AI as a provider — six models (`gpt-oss-120b`, Llama 3.3 70B,
  Qwen3.8 27B, Gemma 4 26B, GLM-5.2, Kimi K2.6), asked for as `cloudflare:<vendor>/<model>`
  and hosted through datalayer-ai-inference; the docs page says how they are billed.
- An id with a vendor segment (`cloudflare:openai/gpt-oss-120b`) gets an enum name of its own
  (`CLOUDFLARE_OPENAI_GPT_OSS_120B`): the slash is replaced like the colon.
