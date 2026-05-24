<!--
  ~ Copyright (c) 2025-2026 Datalayer, Inc.
  ~
  ~ BSD 3-Clause License
-->

[![Datalayer](https://assets.datalayer.tech/datalayer-25.svg)](https://datalayer.ai)

[![Become a Sponsor](https://img.shields.io/static/v1?label=Become%20a%20Sponsor&message=%E2%9D%A4&logo=GitHub&style=flat&color=1ABC9C)](https://github.com/sponsors/datalayer)

# 🧾 Agentspecs

YAML-based specifications for AI agents, MCP servers, skills and more...

## Overview

This repository is the source of truth for declarative specs consumed by Agent Runtimes code generation.

The YAML files in [agentspecs/agentspecs](agentspecs) are compiled into Python and TypeScript catalogs used by runtime and UI layers.

## Current Repository Structure

```text
agentspecs/
├── agents/           # Agent specs
├── teams/            # Team orchestration specs
├── mcp-servers/      # MCP server specs
├── skills/           # Skill specs
├── tools/            # Runtime tool specs
├── envvars/          # Environment variable specs
├── models/           # Model specs
├── memory/           # Memory backend specs
├── guardrails/       # Guardrail policy specs
├── evals/            # Evaluator specs
├── benchmarks/       # Benchmark suite specs
├── triggers/         # Trigger specs
├── outputs/          # Output format specs
└── notifications/    # Notification channel specs
```

Current YAML file counts:

- Agents: 26
- Teams: 9
- MCP servers: 12
- Skills: 4
- Tools: 3
- Env vars: 10
- Models: 20
- Memory backends: 4
- Guardrails: 6
- Evals: 9
- Benchmarks: 8
- Triggers: 3
- Outputs: 8
- Notifications: 4

## Versioning

All specs are versioned.

### Required Version Field

Each spec includes:

- `id`: logical identifier
- `version`: semantic version string (currently `0.0.1` for all shipped specs)

Example:

```yaml
id: data-acquisition
version: 0.0.1
name: Data Acquisition Agent
```

### Versioned References

Cross-spec references should use `id:version` format.

Examples:

```yaml
mcp_servers:
  - tavily:0.0.1

skills:
  - github:0.0.1

envvars:
  - TAVILY_API_KEY:0.0.1

agent_spec_id: comprehensive-sales-analytics:0.0.1
```

### Runtime Catalog Aliases

Generated catalogs are keyed by unversioned id only (e.g. `data-acquisition`).

The `get_*` / `get*Spec` accessor functions accept both bare ids and versioned refs (`data-acquisition:0.0.1`), stripping the version suffix automatically.

Iterating catalog values (`.values()` / `Object.values()`) returns each spec exactly once — no deduplication is needed.

### Default Version During Codegen

Code generation enforces a default spec version of `0.0.1` if omitted (`scripts/codegen/versioning.py`).

In practice, specs in this repository should always declare `version` explicitly.

## Spec Types

### Agents (`agentspecs/agents`)

Defines agent behavior and runtime defaults.

Common fields:

- `id`, `version`, `name`, `description`, `enabled`
- `model`, `sandbox_variant`, `memory`
- `mcp_servers`, `skills`, `tools`
- `environment_name`
- `icon`, `emoji`, `color`
- `suggestions`, `welcome_message`, `welcome_notebook`, `welcome_document`
- `system_prompt`, `system_prompt_codemode_addons`
- Optional workflow fields such as `goal`, `trigger`, `guardrails`, `evals`, `output`, `notifications`, `advanced`

### Teams (`agentspecs/teams`)

Defines multi-agent orchestration over an underlying agent spec.

Common fields:

- `id`, `version`, `name`, `description`, `enabled`
- `agent_spec_id` (versioned)
- `orchestration_protocol`, `execution_mode`, `supervisor`
- `agents` (team members), `reaction_rules`, `health_monitoring`
- `notifications`, `output`

### MCP Servers (`agentspecs/mcp-servers`)

Defines MCP integrations and process startup configuration.

Common fields:

- `id`, `version`, `name`, `description`
- `command`, `args`, `transport`
- `env`, `envvars` (usually versioned)
- `tags`, `icon`, `emoji`

### Skills (`agentspecs/skills`)

Defines reusable skill modules.

Common fields:

- `id`, `version`, `name`, `description`, `module`
- `envvars`, `optional_env_vars`, `dependencies`
- `tags`, `icon`, `emoji`

### Tools (`agentspecs/tools`)

Defines runtime tool metadata and implementation binding.

Common fields:

- `id`, `version`, `name`, `description`, `enabled`
- `approval`
- `runtime.language`, `runtime.package`, `runtime.method`
- `tags`, `icon`, `emoji`

### Env Vars (`agentspecs/envvars`)

Defines environment variable metadata.

Common fields:

- `id`, `version`, `name`, `description`
- `registrationUrl`, `tags`, `icon`, `emoji`

### Models (`agentspecs/models`)

Defines model options available to specs.

Common fields:

- `id`, `version`, `name`, `description`, `provider`
- `default`
- `required_env_vars`

### Other Catalogs

- `memory`: memory backend options
- `guardrails`: security and policy profiles
- `evals`: evaluator definitions
- `benchmarks`: benchmark suites (with evaluator dependencies)
- `triggers`: reusable trigger templates
- `outputs`: output format templates/capabilities
- `notifications`: notification channel templates

## Adding or Updating Specs

1. Add or edit YAML in the relevant folder under [agentspecs/agentspecs](agentspecs).
2. Always set `id` and `version`.
3. Use versioned cross-references (`name:version`) in fields that reference other specs.
4. Keep IDs stable; bump `version` when introducing breaking changes.
5. Regenerate catalogs in Agent Runtimes (`make specs`) and validate consumers.

## Parameters (Launch-Time Inputs)

Agent specs support a `parameters` field using JSON Schema. This lets one spec
be reused across multiple launches while keeping runtime inputs validated and
explicit.

### What parameters provide

- **Validation**: enforce `type`, `enum`, `required`, and defaults.
- **Templating**: inject values into text fields using `{{parameter_name}}`.
- **Reusability**: same agent spec, different runtime contexts.

### Typical template targets

- `system_prompt`
- `welcome_message`
- `pre_hooks.sandbox`
- other template-aware text fields

### Example

```yaml
id: demo-parameters
version: 0.0.1

parameters:
  type: object
  properties:
    project:
      type: string
      default: Orbit
    role:
      type: string
      enum:
        - product analyst
        - engineering lead
        - support specialist
      default: product analyst
  required:
    - project

welcome_message: >
  This runtime was launched for project {{project}}.

system_prompt: >
  You are an assistant dedicated to {{project}}.

pre_hooks:
  sandbox:
    - |
      project_name = """{{project}}"""
```

### Validation notes

- Missing required parameters fail validation.
- Invalid enum values fail validation.
- Optional parameters use defaults when available.

## Best Practices

- Use kebab-case IDs for most specs (`analyze-support-tickets`).
- Use UPPER_SNAKE_CASE for env var IDs (`TAVILY_API_KEY`).
- Keep descriptions concise and action-oriented.
- Prefer explicit versioned references, even when alias lookup works.
- Maintain backward compatibility by preserving old versions when possible.

## License

Copyright (c) 2025-2026 Datalayer, Inc.

Distributed under the terms of the Modified BSD License.
