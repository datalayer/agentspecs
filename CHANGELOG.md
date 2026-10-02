<!--
  ~ Copyright (c) 2025-2026 Datalayer, Inc.
  ~
  ~ BSD 3-Clause License
-->

# Changelog

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
