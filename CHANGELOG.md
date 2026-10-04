<!--
  ~ Copyright (c) 2025-2026 Datalayer, Inc.
  ~
  ~ BSD 3-Clause License
-->

# Changelog

Each version names the LOOP boxes it carries — the plan's ids, as its commits say them — and links the pages that document them, at <https://agentspecs.datalayer.tech>.

## 0.0.26

"Decision", never "judgment": the typed questions Jev answers are decisions, in the catalogue's words and on the wire; and *A Simple Agent* decides with Jev.

- Models: the capability `judgments` is `decisions` (Jev, `cloudflare:gtw/typesafe/jev` and `cloudflare:wrk/typesafe/jev`), and `judge` is `decider` (a chat model that may be asked the same typed questions: `gpt-oss-120b`, Claude Sonnet 4.6). A spec naming `judgments` or `judge` is refused when the catalogue loads: no alias is kept.
- Apps: a decision's `judgment_model` is `decision_model`; the four decision applications say it so. `app_problems` says "… to decide with" and "… does not answer typed decisions". The Appspec JSON Schema is written again (it also gains `record.suggest_tests`, which it lacked).
- datalayer-ai-inference's typed-decision endpoint is `POST /api/ai-inference/v1/decisions`, as the Jev specs say.
- Tools: `decide` (`action: read`), which asks Jev typed questions — `noul`, `choice`, `score` — through datalayer-ai-inference's `POST /decisions` with the runtime's ai-inference token, bound to `agent_runtimes.tools.decisions.decide`. Documented under Tools.
- Agents: *A Simple Agent* (`example-simple`) lists `decide`, says so in its description, welcome message and system prompt, and suggests three decisions: is a ticket urgent, which team handles a request, how positive a review is.

## 0.0.25

An agent may be switched to other models than its own.

- `model_additionals`, optional on an agent: the other models of the catalogue it may be switched to, beside its `model`, each a catalogue `id` (not an alias) and a chat model, never a typed-judgment one. agent-runtimes offers those its inference serves, as datalayer-ai-inference lists them at startup.
- The four enabled agents (*A Simple Agent*, *Example Once Trigger Agent*, *Jupyter Notebook Compactor*, *Crawler Agent*) list `alibaba:qwen-max`: with their own `bedrock:us.anthropic.claude-sonnet-4-6`, the chat models datalayer-ai-inference serves from the catalogue.
- Tests: an additional model is a chat model of the catalogue, not the agent's own, listed once; every enabled agent lists what datalayer-ai-inference serves. Documented with the agent fields.

## 0.0.24

A composed page is shown, and a rule is written one way (LOOP R-01, E-01).

LOOP boxes: R-01, E-01 — [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- *Support desk*'s layout is `page`, the page with the composer over it: agent-runtimes draws a `chat` layout as the conversation alone, so its page composed on the Canvas was no longer shown.
- `app_problems` says when a chat, a widget or a worker composes a page its layout does not show: "Its page is composed but its layout is chat, the conversation alone: choose page or split to show it." — agent-runtimes' `surfaceUnshown` sentence. No catalogue application does.
- `dump_app` writes a rule on one class of action alone (`applies_to: send`), as a person writes it and as agent-runtimes' TypeScript writer does; *Customer interview* and *Report from a file* are rebuilt from their `app.py` so.
- Tests: the problem is said for a chat layout and not for `page` or `split`; a lone class is written alone, named tools and several classes as a list.

## 0.0.23

How an example was built is in the catalogue (LOOP E-05).

LOOP boxes: E-05 — [Applications](https://agentspecs.datalayer.tech/apps).

- A surface's `composed_by` takes `canvas`: its page was composed by a person on the Canvas. *Support desk*, the Canvas example, says it; it said `developer`, as the two examples written in Python do.
- An example written in Python is the one with an `app.py` in the folder named for it; one composed on the Canvas says `composed_by: canvas`; any other was written as a spec.
- Tests: *Support desk* is the one example composed on the Canvas, and it has no `app.py`.

## 0.0.22

The eleven examples of LOOP §9 are in the catalogue: four more applications (LOOP E-01, E-02, E-14).

LOOP boxes: E-01, E-02, E-14 — [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- *Support desk* (`support-desk`), a chat on the document Q&A agent: starters, a product setting, answers from the documents it was given with the passage cited, and a page composed on the Canvas bound to what a chat publishes (`/question`, `/answer`, `/status`, `/inputs/product`) with a button that sends a question and one that starts over.
- *Customer interview* (`customer-interview`), a chat written in Python: `apps/customer-interview/app.py` asks for consent first, then what to learn, answers each message in a step, saves an insight from a button and records a structured result. Its spec is the one `loop apps build` writes from it.
- *Report from a file* (`report-from-a-file`), a widget written in Python: `apps/report-from-a-file/app.py` asks for a CSV, has the Jupyter data analyst report on it in the sandbox and keeps the report as an output; its page binds the report's kind and question at `/inputs/<id>`, the report at `/output`.
- *Weekly pipeline report* (`pipeline-report`), the rigorous worker: every Monday, the Sales Pipeline Board Report Cog under the twelve Guards, eight Gates and the Financial Reporting Track of `op-sales-pipeline-board-report`, with a rule that asks before anything is sent; its page binds a worker's `/goal`, `/activity`, `/report`, `/status` and `/draft`.
- Each of the four says at its top what was verified and what was not: all pass the instant checks and their pages are valid A2UI v0.9; none has run live, since each names an agent that is not enabled.
- Tests: the catalogue holds the eleven, each of its kind, with faces of their own; the Python examples sit beside a built spec; the weekly report runs the Op's checks and asks before sending. The reference's examples now come from *Customer interview*, the first application by id.

## 0.0.21

The *Quote Calculator* is valid A2UI v0.9 and bound to what a widget's page publishes (LOOP R-01, C-04).

LOOP boxes: R-01, C-04; the documentation of UI plugins and the catalog of visual components, G-05 — [UI Plugins](https://agentspecs.datalayer.tech/agents/ui-plugins), [Components](https://agentspecs.datalayer.tech/agents/ui-plugins/components).

- Its `ChoicePicker` options are `{label, value}`, as A2UI v0.9 requires, not plain strings.
- Its seats, plan and term are its settings (`interface.settings`), written at `/inputs/<id>`; its answer is read at `/output` and where it stands at `/status`, the paths the runtime publishes a widget's page at. It bound `/outputs/total` and `/outputs/lines`, which nothing publishes.
- A test validates every block of every catalogue application's surface that is an A2UI basic component against A2UI v0.9's basic catalog and common types (kept beside it, as `@a2ui/web_core` ships them), and that a block writing under `/inputs` writes one of the application's settings.

## 0.0.20

The landing's four decision templates, each an application of the catalogue, and the floating assistant in the Appspec (LOOP E-01, D-07, T-24).

LOOP boxes: E-01, D-07, T-24 — [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- Three decision applications beside *Ship or fix*: *Supplier comparison* (`supplier-comparison`), *Data quality investigation* (`data-quality`) and *Model choice* (`model-choice`), each on the Jupyter data analyst with the decision's ten components, typed judgments by `cloudflare:gtw/typesafe/jev`, and the question, contents, criteria, confidence and scenarios of its template.
- `deployment.embedded.mode` takes a fourth mode, `assistant`: a character on the page that speaks in a balloon.
- `interface.assistant` names the character the application's floating assistant shows: `paperclip`, `wizard`, `cat` or `eyes`, the characters Datalayer's plugin contributes. Another name is refused; when unsaid, the paper clip.

## 0.0.19

The catalog of visual components (LOOP C-13).

LOOP boxes: C-13 — [UI Plugins](https://agentspecs.datalayer.tech/agents/ui-plugins), [Components](https://agentspecs.datalayer.tech/agents/ui-plugins/components).

- Every component a UI plugin renders, with its properties as a JSON Schema, its bindings and its events: A2UI's basic catalog by its names, Datalayer's own as its custom catalog, hosted by the UI plugins rather than in a place of its own.
- An Appspec's components and its surface are checked against the catalog: `app_problems` refuses a component the catalog does not have.
- UI plugins by that name only: nothing mentions or checks what they were called before.

## 0.0.18

LOOP boxes: S-07 — [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- The Appspec reference, generated from its JSON Schema (`agentspecs.apps.reference`): every field, what it means, its default, the parts and the choices, and an example of each field taken from an application of the catalogue. `python -m agentspecs.apps` writes it to the documentation beside the schema, and a test keeps the two the same.

## 0.0.17

An application's face, chosen as a person's is on their profile.

LOOP boxes: I-07 (in part), I-11 — [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `avatar` and `banner` on the Appspec: each the name of a drawing (`AstronautIcon`, `SvgTutorialsHero`) from the sets people choose theirs from. Neither is required: the `emoji` stands for the avatar, and where only text goes; the id seeds the banner. A name must be written as a drawing's name is — a capital letter, then letters and digits (`AstronautIcon`) — or it is refused; the JSON Schema carries the same pattern.

## 0.0.16

What three implementations of the same decision need in order to agree.

LOOP boxes: F-07, and R-05's rule decision, in part — [Applications](https://agentspecs.datalayer.tech/apps).

- A pattern (`*gmail*`, `generate_*`) means the same thing wherever it is read: `*` is any
  run of characters, `?` any one, and nothing else is special — no bracket expressions,
  which Python and JavaScript read differently. `agentspecs.actions.matches`, `is_pattern`.
- A condition compares an argument with a word, a number, true or false; a list or a
  mapping is refused, since equality of those is not the same in every language.
  A whole number beyond 2\*\*53 - 1, and a number that is not finite, are refused too, and
  an argument beyond that range equals nothing: JavaScript holds no such integer exactly.
- `dump_app` writes an application the same way every time: `schema` first, then the keys
  in the order the spec declares them, and not the layout when it is its kind's own. A
  scenario's weights and the components of a surface, whose keys the spec does not
  declare, are written in alphabetical order, a component's `id` and what it is first.

## 0.0.15

Applications, and what a tool does to the world.

LOOP boxes: F-01, F-02, F-06, F-10, F-11, I-01 — [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- Applications: a new spec, the **Appspec**, under `agentspecs/apps/` (`schema: loop.app/v1`).
  An application is an agent with an interface, rules, tests and a place to run; four
  kinds — `chat`, `widget`, `decision`, `worker` — and one spec. It stands alone: it is not
  an Op, and Guards, Gates and a Track are optional, under `checks`.
- Rules in four behaviours — `do_it`, `if_asked`, `ask_first`, `leave_to_me` — written in a
  person's words (`action`) and applied to a class of action or to named tools
  (`applies_to`). `behaviour_for` says what an application does when its agent calls a
  tool: with no rule, reading is done and anything that acts waits for a person.
- Identity and permissions: an application has a face (`emoji`, 👀 until one is chosen) and
  `permissions` — the Spaces it reads or writes, and its computer (browse, files, shell),
  each off until it is turned on.
- Connections: an application reaches nothing it does not name. Each says how far (`read`,
  `write`), in whose name (`owner`, `user`), and optionally which tools (`only`).
- **Action classes** (`agentspecs.actions`): `read`, `write`, `send`, `buy`, `delete`,
  `publish`. Every tool of `tools/` now carries `action`; every MCP server carries
  `actions`. Five servers were read off the running server and classed — Tavily, the
  filesystem, charts, Slack and Google Workspace's 120 tools; the nine others say
  `checked: null` and class nothing. A tool with no class is unknown, and unknown is the
  most restricted; a server's own `readOnlyHint` is not read.
- What a tool does can depend on what it is asked: a tool says its class, and `when` an
  argument makes it another (`add_label_ids` including `TRASH`, `action: delete`).
  `classes_of` and `behaviour_for` take the `arguments` of a call; without them they
  answer for the worst the tool can do. A rule that names a tool decides what the tool
  does of its own, and what its arguments make it do besides is still decided by its
  class. `tool_escalations` lists where that changes the decision.
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
