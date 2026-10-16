<!--
  ~ Copyright (c) 2025-2026 Datalayer, Inc.
  ~
  ~ BSD 3-Clause License
-->

# Changelog

Each version names the LOOP boxes it carries — the plan's ids, as its commits say them — and links the pages that document them, at <https://agentspecs.datalayer.tech>.

## Unreleased

- 0.0.109 (VOICE.md VO-16, VO-47, decision 18 revised; 16 October 2026). The licence register takes `where: machine` — the person's own machine, where agent-runtimes' `voice` extra installs from PyPI — and lists what the extra brings there: sounddevice and PortAudio, kokoro-onnx, onnxruntime, espeakng-loader (MIT) and the kokoro-82m store; phonemizer's and eSpeak NG's notes say that through the extra they reach the person's machine too, where the register does not admit GPL (the user's or counsel's decision, VO-01); a GPL library used on the machine is refused. `moonshine-base-en-server` hears English spoken turns on the server (decision 18, revised by the user). 2 tests.

- 0.0.108 (VOICE.md VO-47, decision 18; 16 October 2026). `moonshine-base-en-server`: Moonshine Base (English, MIT) on the server — the browser's own pinned 8-bit export, run by onnxruntime with the speech service's greedy decoder (`engine: onnxruntime`, `where: [server]`), measured beside Whisper small for short spoken turns; its register line says no new library is used. `transcriber_for(language, "server")` names large-v3-turbo, the model that hears a language at any length; the speech service picks a turn's model itself. 1 test.

- 0.0.107 (SHIELD.md SH-57, SH-46, SH-45; 16 October 2026). **The long tail, listed:** the register takes a `tier` — `catalogue` (a spec launches it, drilled, offered) or `listed` — and every other agent of agentclientprotocol.com/get-started/agents (36 of the page's 43, read on 16 October 2026 at each project's own page and cross-checked against the ACP registry) is registered `listed` with its documented launch command (`command`, null where undocumented: fount, kaagum, stdio Bus), its licence, its terms, the credential it takes and whether serving it to third parties is permitted (`refused` citing the clause for Augment, Blackbox, Factory Droid, Junie, Poolside and Qoder; `unknown`, said, for Cursor, GitHub Copilot, Kiro, Kimi Code, Muse Spark Code and fount — allowed in the listed tier only); a listed harness has no spec, is offered by nothing, and naming one is refused *listed, not drilled yet* (`listed_refusal`, `harness_problems`); a spec beside a listed entry does not load. The reference page lists them. **An organization's own harness:** an `org-…` spec with its register entry, validated together by `organization_harness` (the terms, the licence, the credential and the pinned version required as for any harness), refused in the shared catalogue; `command_digest` and `admission_id` (`<id>@<digest, 12>`) name the command an administrator reviewed and admits on the organization's policy (`harnesses.admit`). **Harnesses in teams:** a team member may be a `harness` (a catalogue id, never with `ref`, `app`, `server`, `tools` or `mcpServer`; what the harness cannot honour refused at load), a link may go `over: acp` to a harness only; `referenced_harnesses`; the `coding-agents` team (Claude Code writes, Codex reviews, a supervisor delegating). JSON Schemas and references regenerated; 6 tests.

- A `standards/` spec kind (SHIELD.md SH-60, SH-66, §6.9, decisions 15 and 16; 15 October 2026): what a conformance report answers — a standard's version, domains and controls, each with its id and title as the standard publishes them, mandatory or optional, retired or not, its cadence in months, its evidence items by kind (documentation, config, logs, evals, report, demonstration), its control activities and its crosswalk references. `aiuc-1` written from standard.aiuc-1.com's six domain pages at the October 15, 2026 release: 55 controls (42 mandatory, 5 retired in this release), 145 evidence items, crosswalks to 14 frameworks (the EU AI Act, NIST AI RMF, ISO/IEC 42001, MITRE ATLAS, the OWASP Top 10 for LLM and for Agentic Applications, OWASP AIVSS, CSA AICM, SOC 2, IBM's Risk Atlas, Cisco's framework, the Colorado AI Act, California SB 53, NYC Local Law 144). `iso-42001` as the second standard, read through AIUC-1's crosswalk: 70 clauses, each naming the AIUC-1 controls that cover it and the published gap analysis (`covered_by`, `coverage`). The version tracked, never applied silently: `released_on`, `next_release_on`, `read_on`, `version_notice` offering a newer release; `aiuc-1.index.txt` the published control index, and a test holding the spec to it (the live `llms.txt` when the network allows). The organization's controls (SH-64) start from `standards/templates/` — the failure plans E001 to E003, acceptable use E010, processing locations E011 (pre-filled with where Datalayer runs), regulatory compliance E012, the data policies A001 and A002, the risk taxonomy C001, vendor due diligence E006 (pre-filled with the model providers of the catalogue) — rendered by `template_text`, signable only once `unfilled_fields` is empty. JSON Schema at `standards/standard.schema.json`; the reference page generated by `python -m agentspecs.standards`; 10 tests.
- A `policies/` spec kind (SHIELD.md SH-50, §6.7, decision 10; 15 October 2026): the Shield's policy document — the rules deciding an agent's actions by class, kind, path and command, the limits with soft and hard thresholds (tool calls, terminals open, bytes written, the model budget in tokens, the spend limit in credits), the hosts a fetch may reach, the MCP servers lent, the harnesses admitted and whose credentials run them. One schema everywhere, the `agent-shield` package's, carried verbatim as `policies/shield-policy.schema.json` and held to the package's own by a test; each catalogue entry wraps a document as `policy` under `id`, `version`, `name`, `description`, `enabled`, `tags` (`policies/policy.schema.json`). The catalogue: `default` (decision 5's session document) and `organization-baseline` (an example of what an administrator writes in IAM). `jsonschema` is a dependency; the reference page is generated by `python -m agentspecs.policies`.
- `record.include` takes `diffs` and `terminals` (SHIELD.md §6.4, SH-34, 15 October 2026): a harness's edits are kept whole — the file's old and new text — only when `diffs` is named, else each diff's hash and size; a terminal's output only when `terminals` is named, else its command and exit. JSON Schema and reference regenerated; 0.0.102.
- *A Claude Code Agent* (`example-harness-claude-code`, SHIELD.md SH-10, 15 October 2026): the first agent of the catalogue on a harness — `harness: claude-code`, off in the shared catalogue because it needs the account's own `ANTHROPIC_API_KEY`, which the harness declares and the runtime is given by name. The Datalayer runtime serves a catalogue harness through its ACP adapter (agent-runtimes 1.5.31): the sentence saying no runtime does is gone.
- A `harnesses/` spec kind (SHIELD.md SH-01, §3.1; the register of SH-04, §3.3; decided on the defaults of decisions 1 to 5, 15 October 2026): an agent program driven over the Agent Client Protocol — `claude-code` (`@agentclientprotocol/claude-agent-acp` 0.91.0, API keys only: Anthropic's terms refuse subscription credentials routed for others), `codex` (`@agentclientprotocol/codex-acp` 2.2.2, API keys only), `gemini-cli` (0.64.0, `--experimental-acp`; a Google login needs Code Assist Standard or Enterprise since 18 June 2026), `goose` (1.54.0, `goose acp`), `opencode` (1.19.0, `opencode acp`), `openhands` (1.16.0, `openhands acp`), one framework over ACP, `fast-agent` (`uvx fast-agent-acp` 0.10.45, §2.5), and `custom`, whose command an organization's own spec names and which the shared catalogue refuses. Each says how it is launched (`acp`), what it needs (`requires`, secrets as ids of `env-vars/`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `LLM_API_KEY` added), what it honours of an agent spec (`honours`, `skills`, `instructions_file`) and its `terms`; `harnesses/register.yaml` registers every one with its licence, terms, credential, third-party serving and tier restrictions, each with where it was read on 15 October 2026 — a harness without an entry, or whose entry disagrees with its spec, does not load. An agent spec's `harness:` takes a harness id beside `pydantic-ai` and `vercel-ai`; `agent_harness_problems` says in a sentence what the harness cannot honour (`model:`, `subagents:`, `skills:`), and `custom`. JSON Schema at `harnesses/harness.schema.json`, the reference page generated. Served by the Datalayer runtime's ACP adapter from agent-runtimes 1.5.31 (SHIELD SH-10).
- Appspec `interface.voice.input: hands_free` is built (VOICE.md VO-12, VO-13, 15 October 2026): a conversation by voice — the composer offers *Talk with it*, a turn ends after a short silence and is sent, the answer is said as it is written, listening goes on, and speaking over the agent stops its voice and its run. No longer refused; `HANDS_FREE_NOT_BUILT` is gone. JSON Schema and reference regenerated.
- A smaller speech model for spoken turns on the server (VOICE.md VO-47, decided by the user 15 October 2026): `whisper-small`, OpenAI's Whisper small in its CTranslate2 conversion (`Systran/faster-whisper-small`, MIT), pinned file by file, kept at `openai/whisper-small`; measured on the fixtures at 3.3% WER in English and 16.1% in French, about four times faster than large-v3-turbo, which keeps long recordings. In the licence register.
- A speech model for the server (VOICE.md VO-34, decision 4): `whisper-large-v3-turbo`, OpenAI's Whisper large-v3-turbo in its CTranslate2 conversion, run by faster-whisper on Datalayer's servers only, every file pinned by SHA-256 and kept at `openai/whisper-large-v3-turbo` in Datalayer's storage; `transcriber_for(language, "server")` answers it. The licence register names faster-whisper, CTranslate2, tokenizers, av and the FFmpeg its wheel ships as used, on the server.
- Appspec `interface.voice.input`: `hands_free` is refused in a sentence until it is built (VOICE.md VO-12, decided 14 October 2026), no longer taken for click-to-talk; `VoiceInput` is `off` or `push_to_talk`. JSON Schema and reference regenerated.
- *Exchange Desk* is on (AGENT_PROTOCOLS PI-42): drilled live on r1 on 14 October 2026 on runtime image 0.0.34 — asked by a person's own agent signed in through Datalayer to exchange order `ord_7Hk2` for size L, it proposed the exchange and went on to tell the person it waits for their approval.
- *Returns Desk* and *Shop Concierge* are on (AGENT_PROTOCOLS PI-42): drilled live on r1 on 13 October 2026 at the hosted Manzanita — a return and a repair asked through its API with `pap_propose`, the return approved by the person and done once; a conversation handed to Marta, of the shop's staff, who answered in it. *Exchange Desk* stays off until the runtime offers a company's turn the tools of its code.
- *Order Desk* is on (AGENT_PROTOCOLS PI-42): drilled live on r1 on 13 October 2026 at the hosted Manzanita, the person signed in both by Direct Sign-In and by Device Sign-In, and their order answered for them.
- *Signed Reader* is on (AGENT_PROTOCOLS EX-11): drilled live on r1 on 13 October 2026 at the hosted Example Verifier, which said the signature holds and named the application; a site its signed fetch does not name refused.
- A pair of examples (AGENT_PROTOCOLS PR-13, E-02; decided 2026-10-13): `pair` (`AppPair`: an `id` and a `role`, `business` or `personal_agent`) links a PACT business to the personal agent that asks it; one of a pair speaks PACT, a business says its scopes, a personal agent answers as no business. *Guest Desk* (a business: `profile:read`, off and registering nobody) and *Errand Runner* (its personal agent, naming no business) are the catalogue's pair, both off until run live: when a person has copied both, the Studio registers the personal agent's copy with the business's copy and points it there.
- A `signed_fetch` block (AGENT_PROTOCOLS EX-11, decided 2026-10-13): an application reads pages at the exact sites it names (`AppSignedFetch`, `AppSignedFetchSite`: an id and a domain each), with `GET` only, through the gateway's `signed-fetch` toolset on its safe egress path, every request signed with its own Web Bot Auth key and recorded, a `read` under its Rules; listed under `protocols` as `web-bot-auth`, which now configures it. *Signed Reader* reads Example Verifier (`verify.examples.datalayer.run`) and says whom it saw; off until the gateway's signed fetch is deployed — [the Appspec page](https://agentspecs.datalayer.tech/apps#companies-and-businesses-over-agent-protocols).
- *Travel Desk* and *Shopping Desk* are on (AGENT_PROTOCOLS PI-42): drilled live on r1 on 13 October 2026 at the hosted Example Air, Example Store and Example Outfitters, as a Preview's runtime reaches the gateway, each saying what was verified live and what not; *Order Desk* stays off until the hosted Manzanita finishes Direct Sign-In (counterparts 0.0.5).
- A company's operation may give a standing permission (PAP_DATALAYER R-07, decided 2026-10-13: the Ledgerly pattern): `pap.company.operations[].allows` in place of `tool` — at one of the application's own company connections (in each person's account, able to change things), what confirming there does (`write` or `buy`), every bound a term of the operation (a maximum or the value allowed), how many uses and for how many days. Only the person confirms it, and its summary says every bound; once they do, it is recorded as the approval in advance they would give in Datalayer — [the Appspec page](https://agentspecs.datalayer.tech/apps#companies-and-businesses-over-agent-protocols).
- *Trusted Agent Protocol* (`tap`) says the draft built from Visa's public Merchant Specifications (AGENT_PROTOCOLS PR-24, decided 2026-10-13): the tags `agent-browser-auth` and `agent-payer-auth`, its specification's page, the packages implementing it; still `planned` for applications until Visa confirms it.
- A `pact.business` block (AGENT_PROTOCOLS PR-13, PI-32; decided 2026-10-13): an application answers as a PACT 1.0 business — its Brand's name (the application's `owner` when unsaid), the scopes a person may delegate with what each lets a personal agent do, and the personal agents its Maker registered, each its issuer and where its keys are (`AppPactBusiness`, `AppPactRegisteredAgent`); enabled, it names at least one; listed under `protocols` as `pact` — [the Appspec page](https://agentspecs.datalayer.tech/apps#companies-and-businesses-over-agent-protocols).
- The protocol examples reach the counterparts Datalayer hosts (AGENT_PROTOCOLS PI-42): *Order Desk* at `manzanita.examples.datalayer.run`, *Travel Desk* at `air.examples.datalayer.run` (audience `https://air.examples.datalayer.run/a2a`), *Shopping Desk* at `store.examples.datalayer.run` and `outfitters.examples.datalayer.run`; *Bookkeeping Desk*'s Northwind has no hosted counterpart and stays off.
- A `pap` block names the Personal Agent Protocol profile it is written for, `profile: draft-01` (PAP_DATALAYER S-03): one Datalayer speaks, or it is refused in a sentence (*This application asks for Personal Agent Protocol profile “x”; Datalayer speaks draft-01.*); a block without one is refused too, an application without the block has none. Every catalogue application with a `pap` block names it — [the Appspec reference](https://agentspecs.datalayer.tech/apps/reference#apppap).

## 0.0.76

- *Report from a File* reports a cell's text as data — quoted as written, never hidden or acted on — and *Support Desk*'s sample documentation speaks to its customers (STUDIO E-01: the four examples *Ready* on Datalayer).

## 0.0.75

- A test can be a short conversation (STUDIO E-01): `tests.cases[].turns` in place of `ask`, each turn what the person says (`say`), the option of a choice they pick (`choose`) or an action of its code they press (`press`, with its `payload`), judged on the whole conversation — *Customer Interview*'s four tests answer its consent and its goal, and press its `save` and `finish` — [a test that is a conversation](https://agentspecs.datalayer.tech/apps#a-test-that-is-a-conversation).

- *Quote Calculator* and *Support Desk* search their documents before their first words; *Report from a File* takes a CSV only and refuses any other file in a sentence (STUDIO E-01).

## 0.0.74

- `signs` — the argument of an MCP server's tool that carries what it sends (STUDIO I-10): an application's runtime closes it with its byline, *Written by 📬 Inbox Triage, for Ana Lopez.*, so a mail or a message sent through a connection says which application wrote it and for whom. Gmail's send and draft (`body`), Google Chat's message (`message_text`), Slack's post and reply (`text`) say it; only a tool that acts may — [action classes](https://agentspecs.datalayer.tech/apps#action-classes).

- *Quote Calculator* and *Support Desk* told what their tests ask (STUDIO E-01).

## 0.0.73

- A test can give its application text files with what it asks (STUDIO E-01): `tests.cases[].files`, each a name and its text (at most 120,000 characters) — *Report from a File*'s cases carry their CSVs.
- *Support Desk* ships its *Product documentation* and *Returns policy* as `samples`, given to the application made from it (E-01).

## 0.0.72

0.0.71 was tagged but not published: its tests failed in CI on the decision model and the generated reference.

- `samples` — what an example is tried on before it is anybody's, published with it by Datalayer and read only (STUDIO E-06, E-11): documents of its contents (*Quote Calculator*'s *Price list*, a sample CSV a visitor's browser sandbox is given) and a decision's alternatives with their evidence and metrics (each of the four decisions); validated, in the schema and the reference — [apps reference](https://agentspecs.datalayer.tech/apps/reference).
- The four decisions decide with `cloudflare:wrk/typesafe/jev`, the route Datalayer's ai-inference offers (E-06).

## 0.0.70

- A custom component's `source` may be a file of the application's folder, by its path in it — `components/dial.js` (STUDIO P-29): a `.js` or `.mjs` file inside the folder, no absolute path and no `..`; packaged with the application and served by the server it is installed beside — [apps reference](https://agentspecs.datalayer.tech/apps/reference).

## 0.0.69

- `example-blank` (STUDIO P-32): a model — Claude Sonnet 4.6 — and nothing else: no prompt of its own, no MCP servers, no skills, no tools. The agent an `app.py` runs in its own process, with the application's instructions as its whole prompt; `loop apps init --python` starts from it — [agents](https://agentspecs.datalayer.tech/agents).

## 0.0.68

The four scenes of the catalogue rehearsed on Datalayer (STUDIO A-14) — [scenes](https://agentspecs.datalayer.tech/scenes).

- Event response asks one specialist at a time, never asks the audience back, and says in its request what is to be sent and to whom; Disaster Assessment never sends: it shows a sending as a choice to approve (*Send it*, *Not now*). Its flood beat is allowed 360 s, and the storm is routed by what it asks for.
- Month-end Close works the accruals out when the conversation holds none, charts at zero, and its post-accruals beat is allowed 180 s; its rehearsal on r1 passed four beats of four (`month-end-close/rehearsal.json`), Disaster Assessment's full run three of four (`disaster-assessment/rehearsal.json`).

## 0.0.67

- The rehearsal that was played (STUDIO A-14): a scene's last rehearsal is kept beside the specs in `<id>/rehearsal.json` — `ScenePlayed`: when, where, whether every beat `passed`, the verdict's sentence, each beat's verdict and the agent-runtimes that played it — written by `loop scenes rehearse --cloud`, read by `scene_played`, kept by `write_played`, refused in a sentence when it is not a rehearsal's result. A scene whose last rehearsal passed is *Live*; one that did not says so. The hand-written `verified` stays a person's word beside it — [scenes](https://agentspecs.datalayer.tech/scenes#the-rehearsal-that-was-played).

## 0.0.66

- Model prices (STUDIO R-09): 29 models of the catalogue carry `pricing`, each read from its provider's published page on 2026-10-08 and cited in its spec — every Bedrock Claude model at the US cross-region (geo) price its `us.` id is billed at (Sonnet 4.6 and 4.5 $3.30/$16.50, Sonnet 4 $3/$15, Opus 5, 4.8 and 4.6 $5.50/$27.50, Opus 4 $15/$75, Fable 5 $11/$55 per million input/output tokens), the Anthropic API models, the OpenAI models at the Standard tier, the five Azure OpenAI models at their Global Standard deployment's price — OpenAI's list price, as pydantic/genai-prices prices Azure (decided 2026-10-08) — and the Workers AI models at Cloudflare's per-token price. Until now only Jev had one, so ai-inference recorded Bedrock calls, the default, at no cost. Alibaba Model Studio (priced by region and prompt length) and Ollama carry none — [models](https://agentspecs.datalayer.tech/agents/models).
- `interface.accent` is optional, with no default: an application that names none wears the theme's own colours, and one that names an accent wears it over whichever theme it runs in, not over `loop` alone (decided 2026-10-07). An accent not among the six is refused. The schema says `null` by default. STUDIO T-05, T-30 — [reference](https://agentspecs.datalayer.tech/apps/reference).

## 0.0.65

- A file to download is a component of the catalog (STUDIO P-04): `Download` (*File to download*), its `name` and its `url` — an http(s) link, or the file itself as a `data:` URL — with its `media_type`, `size` and `description` said beside it; pressing it saves the file and sends its `download` event. An application's answer shows it (`session.ui.download(...)`), as the Canvas places it ([components](https://agentspecs.datalayer.tech/agents/ui-plugins/components#download)).
- The `earthdata` MCP server declares what its download's script reads in the code sandbox (STUDIO R-19): `sandbox_envvars`, `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` (new env-var specs). A runtime is given only the secrets its specs declare, so these reach the sandbox again when the account has them — never the server, and never required: searching is anonymous.

## 0.0.64

Components in the answers of the home page's scenes (STUDIO H-02, H-03).

- The outputs catalogue gives `components` (`application/json+a2ui`, A2UI's media type): an answer's components of the catalog, one A2UI surface per artifact. Accounting, Month-end close, Crop monitoring, Disaster assessment and Change detection name it in `interface.outputs`, after Markdown and the notebook.
- A scene's kinds of answer (`AnswerKind`) gain `sources` (cards that open), `choice` (buttons that answer the application) and `approval` (a choice whose option does more than read); a rehearsal line names them with or without an article (*Accounting: sources*, *an approval*).
- The four scenes have four beats each, each answered with a different kind — the sources, a table, a chart, an approval — the approval asked of a member that only reads (*Send a payment reminder…*, *Post the accruals…*, *Save the June 2026 granules…*, *Send the Valencia flood assessment…*); the entries' starters and the teams' suggestions are the new cues. Sales and Event response say how the person wants it shown in their request, and never that a thing was done unless the member says so.

## 0.0.63

- The environment variable specs live in `agentspecs/env-vars/` (was `envvars/`), hyphenated like `mcp-servers/`, `backend-tools/` and the other directories; the `envvars` field of an agent's or server's spec is unchanged.

## 0.0.62

- The `earthdata` MCP server reaches NASA's catalogue through the Datalayer MCP server's `earthdata` toolset (`mcp-remote`, `only=earthdata`, the person's `DATALAYER_API_KEY`), as `odoo-accounting` reaches the books: `earthdata-mcp-server` is a Python package, so `npx` never started it on a runtime (every Earthdata scene member failed with "Connection closed"). Searching is anonymous; a download on the sandbox still reads `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` there.

## 0.0.61

A scene has a spec of its own (LOOP A-11, A-13, decided 2026-10-07): `scenes/`, `schema: loop.scene/v1`. The team says who is on stage; the scene says what happens there. The four scenes of the home page written as scene specs.

Pages: [Scenes](https://agentspecs.datalayer.tech/scenes), [Scene spec reference](https://agentspecs.datalayer.tech/scenes/reference).

- `agentspecs.scenes`: `SceneSpec` — `name`, `description`, `icon` and `emoji` as an application has them (one face, checked the same way, the scene's own and never a member's); `team` (the team it stages) or an inline `cast` that makes one (`team_of()`), each cast member's `persona` (`name`, `face`, `line`) and `brief`; `setting` (`systems`, each an MCP server with the name it is shown `as` and what it `holds`; `frames`, `contents`, `period`, `language`, `assumes`); `script` (beats: `cue` — `say`, `schedule` or `event` — `narration`, `moves` — `who` asks whom `over` `a2a` or `mcp`, `what`, `tool`, `does`, `answers` a kind — `expect`, `shows`, `pace`, `branch` on a `decision`); `stage` (`positions`, `opens_first`, `transcript` — tools, narration, `withhold` — `inspectors`, `rests_after`, `pace`); `audience` (`who`: visitors, signed-in, nobody; `ceiling_per_ask`, `asks_a_day`); `rehearsal` (per beat the transcript's `lines`, `must_say`, `must_not_say`, `within`; a `recording` for when it cannot play live; `verified` as an application's tests); `deployment` (`account`, `page`, `addresses`: a member on a runtime to the variable its address is read from). `cast_of()` resolves every member with its persona filled from its application; `cues()` is what the audience may say; `parse_line` reads the transcript's grammar (`A → B`, `A → System: tool`, `A: a table`).
- `scene_problems`, in sentences: a cast member not in the team, or saying what it is when the team does; a beat's mover not in the cast; a system that moves; a move over `mcp` to one that is not a system, over `a2a` to a system, to a member the team does not have it talk to, to a system reached through no connection; a cue nobody answers; a tool no connection offers or the server does not have, a tool asked to `read` that writes; a system nobody reaches; a Frame or a server the catalogue does not have; visitors on a scene whose runtime member has no address; an address for a member in the browser; a rehearsal naming a beat not in the script or a name not on stage; a missing recording; a scene wearing a member's face. `scene_setup`: its members' applications' setup. `SCENE_CATALOGUE`, `get_scene`, `list_scenes`, `scenes_staging`, `dump_scene`, `load_scenes`.
- The four scenes: `sales-and-accounting` (🤝), `month-end-close` (📒), `crop-monitoring` (🛰️), `disaster-assessment` (🚨), each with its cast's personas and briefs, its setting (Odoo or Earthdata, `assumes` as the line under the title), three beats whose cues are the entry's starters, with their moves, what they show and their branches, stage directions, a visitor audience, a rehearsal of every beat, and the variables the page reads its addresses from (`DATALAYER_DEMO_SCENE_<TEAM>_<MEMBER>_A2A_URL`; Accounting keeps its own).
- JSON Schema (`scenes/loop.scene.schema.json`) and reference written by `python -m agentspecs.scenes`; the wheel carries both. Tests: `test_scenes.py`.

## 0.0.60

A scene is a team (LOOP A-04, decided 2026-10-07): one member allowed, none refused; each member its role, the team its shared context, each interaction its protocol. The three scenes the home page needs beside Sales and Accounting (A-08).

Pages: [Teams of applications](https://agentspecs.datalayer.tech/agent-teams/applications) (Scenes), [Members](https://agentspecs.datalayer.tech/agent-teams/members), [Execution](https://agentspecs.datalayer.tech/agent-teams/execution) (`context`).

- `TeamSpec.agents` holds one member at least: a team with none is refused (`has no member`). A single member is a scene of one agent and its data.
- `TeamSpec.context` (`TeamContext`): `sharing` (`TeamSharing`: `shared` unless said, `isolated`, `own-turns` — what `jupyter.yaml` wrote and the generators read) and `frames`, the Frames every member works under, in order, as a Cog names its own; a Frame named twice refused. `referenced_frames()`.
- `TeamMember.server`: a member that is an MCP server of the catalogue, a system of the scene the others reach over MCP, in place of `ref` and `app` (`is_server`, `display_name`); it has no `talks_to` and no `subagents`, and the team does not enter at it. `referenced_servers()`.
- `TeamProtocol.MCP`: `talks_to … over: mcp`, to a server member only; `a2a` to an agent or an application only. Refused in sentences: a link to one not in the team (both names said), to itself, over the protocol that does not fit who is asked, a server that asks, a scene entering at a server. `links()`: every interaction, (who asks, who is asked, over what).
- Scenes: `teams/month-end-close.yaml` (Month-end close alone, on a runtime, reading Odoo through `odoo-accounting`), `teams/crop-monitoring.yaml` (Crop monitoring alone, on a runtime, on `earthdata`), `teams/disaster-assessment.yaml` (Event response, in the browser, asks Disaster assessment and Change detection, each on a runtime over A2A, each on `earthdata`), each with its page words — a name, one line, the entry's starters as its suggestions.
- Applications: `apps/month-end-close.yaml` (`worker-month-end-close`, `odoo-accounting` at read), `apps/crop-monitoring.yaml` (`worker-crop-monitoring`), `apps/disaster-assessment.yaml` (`worker-disaster-assessment`), `apps/change-detection.yaml` (`worker-change-detection`), each on `earthdata` at read, and `apps/event-response.yaml` (`worker-event-response`, no connection: it asks and reports). What each needs is said as setup: the five workers are not enabled, `odoo-accounting` is not, `earthdata` is.
- `mcp-servers/earthdata.yaml` classes its three tools, read off its code: the two searches read, `download_earth_data_granules` writes (its `download` mode); at *Can read* the searches are done and the download is left to the person.
- Tests: `test_teams.py` (`TestScenes`), `test_apps.py`.

## 0.0.59

Components a developer writes (LOOP P-17): a component of one application only, declared in its spec and reviewed as the catalog's own.

Pages: [Applications](https://agentspecs.datalayer.tech/apps) (Components of its own), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `interface.custom_components` (`AppCustomComponent`): `name` (none of the catalog's), `description`, `props` (the JSON Schema of an object, its properties typed `string`, `integer`, `number`, `boolean`, `array`, `object` or an `enum` of words), `shows` and `sends` (bindings), `source` (a built ES module over `https://`, or `http://localhost`), `integrity` (a Subresource Integrity hash), `height`, `example`; `catalog_entry(version)` lists it as the catalog lists a component. Refused in sentences: a catalog component's name or one given twice, a module of the application's folder (P-29) or not over `https://`, a property of another type or one every component has, a binding that is also a property, a default or an example its schema refuses.
- `app_problems` reads an application's own components with the catalog's: in `interface.components`, on its surface (their properties checked: `custom_props_refused`) and as a widget's page's output (its value what it shows first).
- JSON Schema and reference regenerated. Tests: `test_apps.py`.

## 0.0.58

Widget applications (LOOP P-05): a widget's page written in its code — its inputs a form, its outputs values — run again as an input changes, its outputs shown in place.

Pages: [Applications](https://agentspecs.datalayer.tech/apps) (A widget's page), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `interface.page` (`AppPage`): `function`, the function of its code that runs it; `inputs`, the JSON Schema of a form (checked as the form `'page inputs'`), and `inputs_ui`; `outputs` (`AppPageOutput`), one at least, each a `name`, a `title`, a `component` among `PAGE_OUTPUT_COMPONENTS` — `Text` (unless said), `Image`, `Table`, `Chart` — and its other properties in `props`; `live` (`true` unless said). Refused in sentences: a page that is not a widget's, inputs that are not a form, two outputs of one name, an output's `props` saying its id or its value's property or lacking one its component needs, an input named as a setting.
- JSON Schema and reference regenerated. Tests: `test_apps.py`.

## 0.0.57

Who the user is, when it matters (LOOP D-21): an embedded application that acts in each user's name takes only a user the host's server signed.

Pages: [Applications](https://agentspecs.datalayer.tech/apps) (Who the user is, when it matters), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `deployment.embedded.host.user` (`HostUser`): `claimed` (unless said), what the page says; `signed`, only a token the host's server signed with the deployment's secret — HS256 (`HOST_USER_TOKEN_ALGORITHM`), `sub`, `name` and `exp` at most an hour away (`HOST_USER_TOKEN_MAX_SECONDS`) — the unsigned one refused. `HostBridge.signed_user`.
- JSON Schema and reference regenerated. Tests: `test_apps.py`.

## 0.0.56

Profiles and settings in full (LOOP P-20), and translation (P-26): several assistants in one application, starters per profile and by category, the nine setting inputs, and what a person reads of an application in their own language.

Pages: [Applications](https://agentspecs.datalayer.tech/apps) (The nine inputs, Profiles and starters, Translations), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference), [Components](https://agentspecs.datalayer.tech/agents/ui-plugins/components) (Form 1.1.0).

- `interface.starters[].category`: the heading a starter is offered under.
- `interface.profiles`: two at least, each an `id`, a `label`, a `description`, `instructions` told to the agent in every run, a `model` (a mode's wins over it) and `starters` in place of the application's. `AppInterface.profile`, `profile_choice`, `starters_for`; a profile's model is one of the catalogue's (`app_problems`).
- `interface.settings_ui`: how the settings' fields are drawn, a uiSchema by field name — `ui:widget` one of `FORM_WIDGETS`, each held to the fields it draws (`form_ui_problems`); `SETTING_INPUTS` names the nine inputs and the field and widget of each. A Form block takes the same `ui` (Form 1.1.0).
- `interface.language` (`en` unless said) and `interface.translations` by BCP 47 tag (`LANGUAGE_TAG`): name, description, welcome, starters by label, categories, settings' fields (title, description, enum values' names), commands' descriptions, modes and profiles. `pick_language(available, preferred)`, `AppInterface.translated(preferred)` and `AppSpec.translated(preferred)`. Refused: a tag that is not one, a translation into its own language or the same language twice, and a translation of what the application does not say.
- Support Desk: its starters by category, its product as radio buttons, and in French.
- JSON Schema, reference and components page regenerated. Tests: `test_apps.py`.

## 0.0.55

What a person sends (LOOP P-21): the kinds of file an application takes in its composer without asking, each with its largest size, and how many at once.

Pages: [Applications](https://agentspecs.datalayer.tech/apps) (What a person sends), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `interface.uploads`: `kinds` — each a `type`, a media type (`application/pdf`), a family (`image/*`, `audio/*`) or an extension (`.csv`), and its `max_mb` (10 unless said, 25 at most, `MAX_UPLOAD_MB`) — and `max_files` (5 unless said). None when unsaid: the composer offers no attachment, and a file sent with a message is refused.
- `AppUploads.kind_of`, `refusal` and `too_many` say which kind takes a file and why one is refused, in a sentence; `upload_kind_takes(kind, name, media_type)`.
- Refused: no kind, a kind said twice, a type that is none of the three, a size of 0 or over 25 MB, `max_files` under 1 or over 20.
- JSON Schema and reference regenerated. Tests: `test_apps.py`.

## 0.0.54

What an application's code declares (LOOP P-06): its own tools, its code's checks, and tests its code decides — in the spec, so that the Canvas shows them and validation runs them.

Pages: [Applications](https://agentspecs.datalayer.tech/apps) (Written in its code), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `tools`: tools of its own, written in its code (`@app.tool`) — a `name`, a `description` for the agent, `parameters` as the JSON Schema of an object, and what it `does` by class of action. `behaviour_for` decides a call by what it does, or by a rule that names it by its name alone; `app_problems` accepts such a rule. `AppSpec.tool(name)`.
- `checks.code`: checks written in its code (`@app.check`), each a `name`, where it runs (`on`: `answer` or `tool_call`, `CheckStage`) and a `description` in words.
- `tests.cases[].code`: the function of its code that decides a case; `expect` still says it in words.
- Refused: names that are not Python names, a name said twice, a tool named as a backend tool the application names, a tool that does not say what it does.
- JSON Schema and reference regenerated. Tests: `test_apps.py`.

## 0.0.53

Settings are a form (LOOP C-16, decided 2026-10-06: one form kind).

Pages: [Applications](https://agentspecs.datalayer.tech/apps) (Settings), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `interface.settings` is the JSON Schema of a form, an object of named fields, each with its `title` and its `default` — checked as a Form block's schema is (`form_problems`, as the form `'settings'`). Drawn with `@datalayer/primer-rjsf` beside the conversation and on a deployment's Ship card; the runtime checks what a run is given against it.
- **Breaking:** the list of settings (`id`, `type`, `label`, `options`, `default`, `min`, `max`) is refused, not read; `AppSetting` and `SettingType` are gone. The catalogue's applications with settings migrated: *Quote Calculator*, *Support Desk*, *Web Research*, *Customer Interview*, *Report from a File* (the last two built from their `app.py`, whose `app.setting(name, field)` takes a field's JSON Schema).
- JSON Schema and reference regenerated. Tests: `test_apps.py`, `test_app_surfaces.py`.

## 0.0.52

*Inbox Triage*'s recorded run said in a Maker's words (LOOP E-01): its sentence names Datalayer's own tests, not the package and test file they are in, since the gallery and the example's pages show it.

## 0.0.51

The examples' agents, enabled where they work (LOOP E-01, decided 2026-10-06).

Pages: [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `unavailable_because`: why an application is not offered today, in a sentence its page shows. An application with `enabled: false` says it, one that is offered does not; either way round is refused. JSON Schema and reference regenerated.
- Agents enabled, each with the models ai-inference serves beside its own (`model_additionals`): `jupyter-data-analyst`, `worker-document-qa`, `worker-customer-interviewer` and the Cog `cog-customer-interviewer`. What they need is enabled or built: no MCP server, the notebook and document tools, the documents tool on Contents, a Frame.
- Examples switched on: *Quote Calculator*, *Report from a File*, *Customer Interview*, *Support Desk* — and *Ship or Fix*, *Supplier Comparison*, *Data Quality*, *Model Choice*, whose agent is now enabled. Their `tests.verified` no longer say the agent is off; none has run live yet.
- Examples kept off, each saying why: *Inbox Triage* (the mailbox connection, W-02, is not built) and *Weekly Pipeline Report* (ten of its twelve Guards are not run yet, so the Gates before the board cannot pass).
- Tests: `test_apps.py`.

## 0.0.50

Commands and modes in the composer (LOOP P-19).

Pages: [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `interface.commands` (`AppCommand`): `name` (what follows the slash: lower-case letters, digits and hyphens, a letter first), `description`, and `prompt`, what picking it sends — `{input}` the words typed after it, the only placeholder; `command_prompt(command, words)` says it, and `AppInterface.command(name)` finds one. A name said twice is refused.
- `interface.modes` (`AppMode`, `AppModeOption`): a switch, `id`, `label`, `default`, and two options at least, each with `instructions` told to the agent in every run in that mode and optionally a `model` run in place of the application's. Ids said twice, a default not among the options, or two modes choosing the model are refused; a model the catalogue does not have is a problem (`app_problems`). `AppInterface.mode_choice(chosen)` is the option of every mode a run is in (an unknown mode or option refused), `mode_effect(chosen)` its instructions and model.
- A key a command, a mode or an option does not know is refused. JSON Schema and reference regenerated.
- Tests: `test_apps.py`.

## 0.0.49

The theme an application runs in by default (LOOP T-30).

Pages: [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `interface.theme` (`AppTheme`): `variant`, one of Appearance's themes (`ThemeVariant`: `datalayer`, `spatial`, `lovely`, `matrix`, `earth`, `sand`, `ivory`, `sun`, `loop`), and `mode` (`ThemeMode`: `light`, `dark`, `auto`), the person's own when unsaid. Unsaid, the application follows the person's theme. Its `accent` colours the `loop` theme only. A variant or a mode not listed is refused, as is a key it does not know.
- Tests: `test_apps.py`.

## 0.0.48

The host page and an embedded application talk to each other (LOOP D-10): the values the page passes it and the functions of the page it may call, named in its Appspec, each a tool a rule decides.

Pages: [Applications](https://agentspecs.datalayer.tech/apps) (The host page's values and functions), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `deployment.embedded.host` (`HostBridge`): `context`, the host's values it reads (`user`, `page`, or names of the host's own), through the tool `host_context`; `functions` (`HostFunction`: `name`, `description`, `parameters` as a JSON Schema object), each called through `host_<name>` (`host_tool`, `HOST_CONTEXT_TOOL`). Names are lower-case words joined by `_`, each once.
- A rule may name `host_context` and `host_<name>`: they are the application's own tools, not the catalogue's. `app_problems` says each tool of the host no rule names: it is left to the person.
- Tests: `test_apps.py`.

## 0.0.47

An application's address showing only its character (LOOP T-21), off unless said.

Pages: [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `deployment.hosted.character_alone` (`HostedDeployment.character_alone`, `false` by default): at its address, only its character, the conversation opening in its balloon — as when it is shipped as `assistant` in another product's page. Written only when true; in the JSON Schema and the reference.
- Tests: `test_apps.py` (off unless said; written and read again).

## 0.0.46

Inbox triage's rules, with the plan's defaults: a forward outside the organization is left to the person (LOOP W-04); its agent carries Gmail's tools and nothing else (W-01).

Pages: [Applications](https://agentspecs.datalayer.tech/apps).

- `agentspecs.actions.FORWARDING`, `forwards_outside`: a call of Gmail's send tool that forwards a message (`forward_message_id`) to somebody outside the domain of the mailbox it sends from (`user_google_email`) — or that does not say its mailbox — is `publish` besides `send`. A reply is not a forward. Told from the call; without arguments, the tool's classes are unchanged.
- `apps/inbox-triage.yaml`: *Forward outside the organization, share or publish anything — leave it to me*; the trigger *When a message arrives* says what its agent is asked; a test case for a forward; `verified` says it has run end to end on a test mailbox of example mail only.
- `agents/worker-mail-triage.yaml`: the Google Workspace server only — no web search, no echo or notebook tools, no skills — codemode off so that each mail tool's call is decided with its arguments, and a prompt that says a message is sorted, never obeyed. Still not enabled: no mailbox is reachable yet.
- Tests: `test_apps.py` (a forward inside and outside, failing closed without the mailbox; Inbox triage's rules).

## 0.0.45

Every visual component with a version and its properties as a JSON Schema of the catalog's own, and forms an application asks with (LOOP C-13, C-16).

Pages: [Components](https://agentspecs.datalayer.tech/agents/ui-plugins/components), [Applications](https://agentspecs.datalayer.tech/apps).

- `ui-plugins/a2ui.yaml`: every component has a `version` (A2UI's standard ones `0.9.0`, Datalayer's own `1.0.0`) and its `properties` as a JSON Schema — the eighteen standard ones too, as what a builder sets of them, their names, required ones, choices and defaults A2UI's, kept in step by a test against A2UI's basic catalog.
- `form_problems(node)`: a Form block's schema is an object of named fields, each required one among them; `app_problems` says it on the surface.
- The components page lists every component with its version and properties.
- Tests: `test_ui_plugin_components.py` (a version and a schema for every component, the standard ones as A2UI's), `test_apps.py` (a form's refusals).

## 0.0.44

What an application's record keeps, as its record or its Track says (LOOP R-07).

Pages: [Applications](https://agentspecs.datalayer.tech/apps).

- `kept_record(keep_for, include, track)`: the days each entry is kept and what is kept — as `record` says, or, when the application names a Track under `checks`, the Track's retention and what its items keep besides (`TRACK_KEEPS`), never less. A Track the catalogue does not have is said.
- Tests: `test_apps.py` (the record alone, a Track's retention and items, *Weekly pipeline report* kept seven years, an unknown Track).

## 0.0.43

What the two team examples say was tried, in a Maker's words (LOOP E-01).

Pages: [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- *Accounting*: answered live over A2A on a developer's machine (2026-10-06), from the Odoo books, read only — and said what did not pass: the list of invoices failed, and one column total was wrong.
- *Sales*: its sentence of what is not tried yet names no builder's word.
- The reference written again from *Accounting*.

## 0.0.42

The floating assistant's balloon: the whole conversation, or only what it says or does now (LOOP T-23).

Pages: [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- Appspec: `interface.balloon` — `history` (every message, scrolled, the composer last) or `current` (only what it says or does now: the answer being written, or the tool it calls). The page's own when unsaid: `history` for the floating chat, `current` for a team's members. `BalloonDisplay` in the JSON Schema.
- Refused: any other word (`interface.balloon`).
- Tests: `test_apps.py` (both displays round-tripped, the schema's enum, the refusals).

## 0.0.41

Output formats: what an application's answers come in, by media type (LOOP H-29).

Pages: [Applications, Outputs](https://agentspecs.datalayer.tech/apps#outputs), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- Appspec: `interface.outputs` — the media types its answers come in, words first (`text/plain` or `text/markdown`), then any other format, such as `application/x-ipynb+json` for a Jupyter notebook. Plain text alone when unsaid. Served over A2A, they are its agent card's output modes, and a caller accepts some of them with each request (`acceptedOutputModes`).
- Refused: an output that is not a media type (`type/subtype`, lowercase, no parameters), one named twice, outputs that do not start with words; and, among `app_problems`, an output the outputs catalogue does not give (`output_media_types()`, the catalogue's `mime_types`). The JSON Schema carries the pattern.
- Accounting answers in Markdown and in a Jupyter notebook (`text/markdown`, `application/x-ipynb+json`).
- Tests: `test_apps.py` (Accounting's outputs round-tripped, every refusal).

## 0.0.40

- The speech service is named `datalayer-speech` (on r1) in the voice catalogue and the licence register; nothing else changes.

## 0.0.39

- `agentspecs.speech.transcriber_for` prefers `moonshine-tiny-en` to `moonshine-base-en` for English: on the recorded fixtures it heard better (WER 3.3% against 4.9%, agent-runtimes `tests/voice`, 2026-10-05) at half the download (VOICE.md VO-05).

## 0.0.38

Voice, its foundations (VOICE.md, Phase V0): the voice catalogue, the licence register, and an application's voice.

Pages: [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `agentspecs/voices` (VO-40): three Kokoro voices for the first languages, English and French (decision 12) — `kokoro-af-heart` (en-US), `kokoro-bf-emma` (en-GB), `kokoro-ff-siwis` (fr-FR, with the SIWIS database's CC BY 4.0 attribution). Each names its engine, its model, the engine's own name for it, its languages (BCP 47), where it may run, the licence of its weights and of its data, and a sample.
- `agentspecs/speech-models` (VO-40, VO-03): `moonshine-tiny-en`, `moonshine-base-en` (MIT, the browser's English), `whisper-base` (MIT, the browser's French), `silero-vad` (MIT, as `@ricky0123/vad-web` 0.0.31 ships it) and `kokoro-82m` (Apache-2.0, on ai-agents). Every file pinned by its SHA-256 and its size, with the revision it was copied from, so that nothing is fetched from a third party's hub at run time.
- `agentspecs/speech-licences.yaml` (VO-01): the register — every library, model, voice and dataset weighed, the browser packages' dependencies among them, with its licence and source; `allowed` (MIT, Apache-2.0, BSD, 0BSD, ISC, CC0, CC BY 4.0) and `server_only` (GPL and LGPL, run on Datalayer's servers and never sent to a browser, decision 1). Not yet reviewed by counsel.
- `agentspecs.speech`: the catalogue, typed and checked when it loads — a voice or a model whose weights, data or code carry a licence on neither list is refused with a sentence (VO-04); `list_voices`, `get_voice`, `list_speech_models`, `transcriber_for` (Moonshine where it hears the language, Whisper otherwise, decision 3), `voice_problems`. Imports only pydantic and yaml, so the speech service reads it alone.
- Appspec: `interface.voice` (VO-41) — `enabled` (off unless said), `input` (`off`, `push_to_talk`, `hands_free`), `output` (`off`, `on_request`, `always`), `voice`, `language` (BCP 47) and `where` (`auto`, `device`, `server`); a voice not in the catalogue, or not speaking the language, is one of `app_problems`. `audio` as a record item (VO-42), kept only by an application that listens and refused for a public one.
- Tests: `test_speech.py` (non-commercial voices and models refused, GPL kept off the browser, every file pinned, English and French heard and spoken, the register naming everything used, the Appspec's voice round-tripped and checked).

## 0.0.37

A team of two applications working over A2A: *Sales*, in the person's browser, asks *Accounting*, on a runtime, for financial reports read from Odoo.

Pages: [Teams of applications](https://agentspecs.datalayer.tech/agent-teams/applications), [Members](https://agentspecs.datalayer.tech/agent-teams/members), [Execution](https://agentspecs.datalayer.tech/agent-teams/execution), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- Apps: `sales` (chat) takes a request for a financial report, asks Accounting with its `ask_accounting` tool (the team's A2A link) and hands over what Accounting answered. Its instructions say it never invents, estimates or completes a figure. It has no connection and no rule, and its assistant is the paper clip. `accounting` (chat) answers report requests from the Odoo books through `odoo-accounting` at *Can read*, in its owner's name, so no tool that writes is reached. Its rules read the books without asking (*Read the books*) and ask first before anything that would change them (*Change the books*: write, delete). Its instructions say it never writes to Odoo, and its assistant is the wizard.
- Teams: a member may be an application (`app`, in place of `ref`; not both), say where its loop turns (`runs_in`: `browser` or `runtime`) and whom it asks while it works (`talks_to`: `{member, over: a2a}`). A team says the member a person talks to (`entry`), and a supervisor may be an application (`app`). Links and the entry name members, and a member does not talk to itself; all of this is checked at load. `TeamSpec.referenced_apps()` lists the applications a team names. New enums and models: `TeamPlace`, `TeamProtocol`, `TeamLink`.
- Teams: `sales-and-accounting`, with Sales as its entry and supervisor (in the browser) and Accounting on a runtime, linked over A2A.
- The Appspec reference is written again; its examples now come from `accounting`, the first application in alphabetical order.

## 0.0.36

The `tools` catalogue is `backend-tools`, beside `frontend-tools`: the tools that run on the runtime, named as such.

Pages: [Backend Tools](https://agentspecs.datalayer.tech/agents/backend-tools), [Agents](https://agentspecs.datalayer.tech/agents), [Frames](https://agentspecs.datalayer.tech/frames), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `agentspecs/tools` is `agentspecs/backend-tools`. Every one of its nineteen tools runs on the runtime, in Python (`runtime.package`, `runtime.method`) — `display-recipe`, `generate-haiku` and the other `example-*` tools too, whose results the page draws but which the runtime runs — so none moved to `frontend-tools`.
- The field that names them is `backend_tools`, as `frontend_tools` names the page's: on an agent (146 agents), an application (`AppSpec.backend_tools`; *Decide*), a Frame (`FrameSpec.backend_tools`, `FrameContext.backend_tools`) and in composition (`LIST_FIELDS`, a Cog's Frames). No alias: `tools` is refused — by `resolve_spec` for an agent, a Cog or a fragment, by `FrameSpec`, and by the Appspec, which forbids an unknown field. A rule naming a tool by id looks it up in `backend-tools`; `agentspecs.actions` reads its classes there; the marks cover `backend-tools`. A team member's `tools` (the names of the tools a member is drawn with) is unchanged.
- The Appspec JSON Schema and reference written again; the README and the docs say `backend_tools`.

## 0.0.35

*Decide*, an example application that answers by asking Jev typed decisions.

LOOP boxes: E-01 — [Applications](https://agentspecs.datalayer.tech/apps).

- Apps: `decide` (chat): `example-simple` with the `decide` tool — yes or no (`noul`) with its probability, one of named options (`choice`) or a step on a scale (`score`), each with its confidence, asked of `cloudflare:wrk/typesafe/jev` through datalayer-ai-inference. Its instructions say it answers by asking a typed decision; its starters are decision questions; its one rule says deciding is a read, done without asking. The reference's `tools` example is now its own.

## 0.0.34

The `loops` catalogue is now `strategies`: its control-loop reasoning strategies (human-in-the-loop, OODA, plan → execute → critic, data analysis) no longer share a name with LOOP and its applications.

- `agentspecs.loops` → `agentspecs.strategies`: `StrategySpec`, `StrategyHuman`, `StrategyTermination`, `STRATEGY_CATALOGUE`, `Strategies`, `get_strategy`, `list_strategies`. The ids stay. No alias: `agentspecs.loops` is gone.

## 0.0.33

The examples' `tests.verified` sentences without a builder's word (LOOP E-14): *the past orders*, *a run already recorded*, *nothing has stopped for an approval*, *measured for it*.

LOOP boxes: E-14 — [Applications](https://agentspecs.datalayer.tech/apps).

## 0.0.32

What the examples say they verified, in a Maker's words (LOOP E-14).

LOOP boxes: E-14 — [Applications](https://agentspecs.datalayer.tech/apps).

- Apps: the `tests.verified` sentences of *Web Research*, *Customer Interview*, *Report from a File* and *Weekly Pipeline Report* say what a person reads on the Studio's examples — an agent, not a Cog; what it suggests you ask, not its starters; Datalayer's own tests.

## 0.0.31

Marks: every MCP server, skill, tool and frontend tool set has an icon that names its package, and an emoji; an Odoo accounting server through the Datalayer MCP server.

Pages: [MCP servers](https://agentspecs.datalayer.tech/agents/mcp-servers), [Skills](https://agentspecs.datalayer.tech/agents/skills), [Tools](https://agentspecs.datalayer.tech/agents/tools).

- Marks (`agentspecs.marks`): an `icon` is `<package>:<name>` — the package one of `@datalayer/icons-react` and `@primer/octicons-react`, the name in kebab case as that package names it (`@datalayer/icons-react:odoo`, `@primer/octicons-react:mark-github`) — so a page loads the icon from the right package. `MARKS_SCHEMA` (JSON Schema), `icon_problem`, `emoji_problem`, `marks_problems` and `parse_icon` say it; a bare name is refused. The 47 entries of `mcp-servers`, `skills`, `tools` and `frontend-tools` say theirs: the brands from the Datalayer icons (Datalayer, GitHub, Google, Kaggle, Slack, Odoo, Jupyter for the notebook tool sets), the rest octicons. `notebook` and `brain` were never octicons and are gone. A page draws the icon, the emoji where there is no icon, and nothing where there is neither.
- MCP servers: `odoo-accounting` is the Datalayer MCP server with its `odoo-accounting` toolset alone (`https://mcp.datalayer.run/mcp?only=odoo-accounting`, through `mcp-remote`, with `DATALAYER_API_KEY`): invoices, bills, journal entries, reconciliations, bank lines and tax returns. Its 49 tools classed as `datalayer` classes them; off by default; icon `@datalayer/icons-react:odoo`.
- Tools: every entry of `tools` runs on the runtime, in Python; the ones that run on the page are `frontend-tools`. The README and the Tools page say so.

## 0.0.30

Each example says what was verified, and how (LOOP E-14); *Report from a File* takes its file on its page (LOOP E-01).

LOOP boxes: E-14, E-01 — [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- Apps: `tests.verified` (`AppVerified`) says what was tried live, what runs on recorded data, and what is not verified yet, each in a sentence (`live`, `recorded`, `unverified`); empty unless said. The eleven examples say it — what their header comments said, now in the spec where the Studio's cards and pages read it. The Appspec JSON Schema and the reference are written again.
- Apps: *Report from a File*'s page has a File upload (`file`, a CSV, at `/files`): the file chosen goes to its session with the run and answers what its code asks.

## 0.0.29

The Datalayer MCP server's tools, classed: what an application's connection to Datalayer reaches through the gateway (LOOP I-12).

LOOP boxes: I-12, F-10 — [Applications](https://agentspecs.datalayer.tech/apps).

- MCP servers: `datalayer` classes each of the 144 tools the Datalayer MCP gateway serves (`checked: 2026-10-05`), read off the gateway's own table of what it serves, every toolset included: reading notebooks, Spaces, the library, Contents, Earthdata and Odoo is `read`; editing a notebook, running code, Odoo's records and the books are `write`; removing a cell, a record or a sandbox `delete`; launching a sandbox `buy`, a snapshot of one `write` and `buy`; sharing one `publish`. The gateway grants an application's connection to Datalayer the tools these classes allow at its level — a connection that reads, only the tools that only read — as the runtime gives them (`gives`).

## 0.0.28

An organization's Frames: its version of a catalogue Frame, and Frames of its own (LOOP U-31, U-32).

LOOP boxes: U-31, U-32 — [Frames](https://agentspecs.datalayer.tech/frames), [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- Frames: `frames_with_organization(versions, owner=...)` gives the catalogue as an organization reads it — the versions it keeps (Datalayer IAM's `frames`) — for `compose_frames`: its rules, terminology and style in place of a Frame's three as resolved, the Frame then standing alone (one that builds on it keeps the catalogue's version of what it inherits); and its own Frames, with an id starting with `org-` (`ORGANIZATION_FRAME_PREFIX`, `is_organization_frame`), a name and a description, for the whole organization. A version of the wrong shape, or an own Frame with no name, is refused; a version of a Frame the catalogue no longer has is left out.
- Frames: a catalogue Frame whose id starts with `org-` is refused when the catalogue loads.
- Apps: `app_problems(app, organization_frames=[...])` checks an `org-…` context against the Frames of the organization the application belongs to: one it does not have is refused (*Its organization has no context named …*), and so is any when no organization is said. The `context` field says so; the Appspec JSON Schema and the reference are written again.

## 0.0.27

An application's floating assistant may show a character a plugin contributes (LOOP T-24).

LOOP boxes: T-24 — [Applications](https://agentspecs.datalayer.tech/apps), [Appspec reference](https://agentspecs.datalayer.tech/apps/reference).

- `interface.assistant` takes any character id of the right shape — lowercase letters and digits, words joined by a hyphen, at most 64 characters — not only Datalayer's four: which characters exist is what the enabled plugins contribute to `loop.assistant.character`, known by the runtime and the page, which refuse an id no enabled plugin gives with a sentence. The `AssistantCharacter` enum is gone; `ASSISTANT_CHARACTER_ID` is the shape. The Appspec JSON Schema and the reference are written again.
- Said in the spec, the character wins over the one a person chose in their settings.

## 0.0.26

"Decision", never "judgment": the typed questions Jev answers are decisions, in the catalogue's words and on the wire; and *A Simple Agent* decides with Jev.

- Models: the capability `judgments` is `decisions` (Jev, `cloudflare:gtw/typesafe/jev` and `cloudflare:wrk/typesafe/jev`), and `judge` is `decider` (a chat model that may be asked the same typed questions: `gpt-oss-120b`, Claude Sonnet 4.6). A spec naming `judgments` or `judge` is refused when the catalogue loads: no alias is kept.
- Apps: a decision's `judgment_model` is `decision_model`; the four decision applications say it so. `app_problems` says "… to decide with" and "… does not answer typed decisions". The Appspec JSON Schema is written again.
- Apps: `record.suggest_tests` (LOOP V-16), off unless said: whether an application's conversations may be used to suggest tests to its builder — only those kept while it is on are sampled. Documented under Applications and in the reference.
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
