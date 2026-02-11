# 🤖👷‍♂️ Agent Specs

YAML-based specifications for AI agents, MCP servers, skills, and environment variables.

## Overview

This repository contains declarative specifications in YAML format that define:

### Specification Types
- **Agent Specs** (`agentspecs/agents/`) - Agent configurations organized by category (code-ai/, codemode-paper/, datalayer-ai/)
- **MCP Server Specs** (`agentspecs/mcp-servers/`) - MCP server commands and environment variables
- **Skill Specs** (`agentspecs/skills/`) - Agent skills with dependencies and env vars
- **Envvar Specs** (`agentspecs/envvars/`) - Environment variable definitions with registration URLs

These YAML specifications serve as the single source of truth for agent configurations and can be consumed by any system that implements the schema.

## Directory Structure

```
agentspecs/
├── agents/                          # Agent specifications (organized by category)
│   ├── code-ai/                     # Code-focused agents
│   │   ├── coder.yaml
│   │   ├── simple.yaml
│   │   └── tux.yaml
│   ├── codemode-paper/              # Research paper agents
│   │   ├── crawler-mcp.yaml
│   │   ├── financial-viz.yaml
│   │   ├── information-routing.yaml
│   │   └── task-decomposition.yaml
│   └── datalayer-ai/                # Data-focused agents
│       ├── data-acquisition.yaml
│       ├── github-agent.yaml
│       ├── simple.yaml
│       └── web-search.yaml
├── mcp-servers/                     # MCP server specifications
│   ├── kaggle.yaml
│   ├── github.yaml
│   ├── filesystem.yaml
│   ├── tavily.yaml
│   └── ...
├── skills/                          # Skill specifications
│   ├── data-analysis.yaml
│   └── ...
├── envvars/                         # Environment variable specifications
│   ├── KAGGLE_TOKEN.yaml
│   ├── GITHUB_TOKEN.yaml
│   ├── TAVILY_API_KEY.yaml
│   └── ...
├── agent-spec.schema.yaml           # JSON Schema for validation
└── README.md                        # This file
```

## Agent Specifications

Agent IDs are automatically prefixed with their folder name, ensuring uniqueness across categories.
For example, an agent in `code-ai/simple.yaml` will have ID `"code-ai/simple"`, while `datalayer-ai/simple.yaml` has ID `"datalayer-ai/simple"`.

### Required Fields
- **`id`** (string): Unique identifier within folder (kebab-case). The full ID becomes `folder/id` (e.g., `code-ai/simple`)
- **`name`** (string): Display name
- **`description`** (string): Agent capabilities description

### Optional Fields
- **`tags`** (list): Categorization tags
- **`enabled`** (boolean): Whether agent is active (default: `true`)
- **`mcp_servers`** (list): MCP server IDs to use
- **`skills`** (list): Agent skills
- **`environment_name`** (string): Runtime environment (default: `"ai-agents"`)
- **`icon`** (string): UI icon identifier
- **`emoji`** (string): UI emoji identifier (e.g., `"📊"`)
- **`color`** (string): Hex color code (e.g., `"#3B82F6"`)
- **`suggestions`** (list): Chat examples
- **`welcome_message`** (string): Greeting message
- **`system_prompt`** (string): Base system prompt for the agent
- **`system_prompt_codemode_addons`** (string): Additional instructions for Code Mode execution environment
- **`welcome_notebook`** (string): Jupyter notebook path
- **`welcome_document`** (string): Lexical document path

### Agent Organization

Agents are organized in subfolders by category:
- **`code-ai/`**: Code-focused agents (coder, simple, tux)
- **`codemode-paper/`**: Research paper agents (crawler-mcp, financial-viz, information-routing, task-decomposition)
- **`datalayer-ai/`**: Data-focused agents (data-acquisition, github-agent, simple, web-search)

This folder structure:
1. **Prevents ID conflicts**: Multiple agents can have the same base ID (e.g., "simple") in different folders
2. **Improves organization**: Related agents are grouped together
3. **Enables categorization**: Frontend can display agents by category
4. **Maintains clarity**: Full IDs like "code-ai/simple" clearly show the agent's purpose

### Example
```yaml
# File: agentspecs/agents/codemode-paper/financial-viz.yaml
# Full ID will be: "codemode-paper/financial-viz"
id: financial-viz
name: Financial Visualization Agent (Viz)
description: >
  Analyzes financial market data and creates visualizations and charts.

tags:
  - finance
  - stocks
  - visualization

enabled: true

mcp_servers:
  - alphavantage
  - chart

skills: []

environment_name: ai-agents-env

icon: trending-up
emoji: 📈
color: "#F59E0B"

suggestions:
  - Show me the stock price history for AAPL
  - Create a chart comparing MSFT and GOOGL over the last year
  - Analyze the trading volume trends for Tesla

welcome_message: >
  Welcome! I'm the Financial Visualization Agent. I can help you analyze
  stock market data, track financial instruments, and create charts to
  visualize market trends.

system_prompt: >
  You are a financial market analyst with access to Alpha Vantage market data and chart generation tools.
  You can fetch stock prices, analyze trading volumes, create visualizations, and track market trends.
  Provide clear insights with relevant data points and generate charts to illustrate patterns.

system_prompt_codemode_addons: >
  ## IMPORTANT: Be Honest About Your Capabilities
  NEVER claim to have tools or capabilities you haven't verified.

  ## Core Codemode Tools
  Use these 4 tools to accomplish any task:
  1. **list_servers** - List available MCP servers
  2. **search_tools** - Progressive tool discovery by natural language query
  3. **get_tool_details** - Get full tool schema and documentation
  4. **execute_code** - Run Python code that composes multiple tools

  ## Recommended Workflow
  1. **Discover**: Use list_servers and search_tools to find relevant tools
  2. **Understand**: Use get_tool_details to check parameters
  3. **Execute**: Use execute_code to perform multi-step tasks
```

## MCP Server Specifications

### Required Fields
- **`id`** (string): Unique identifier (kebab-case)
- **`name`** (string): Display name
- **`description`** (string): Server capabilities description
- **`command`** (string): Executable command (e.g., `"npx"`, `"python"`)
- **`args`** (list): Command arguments

### Optional Fields
- **`transport`** (string): Transport protocol (`"stdio"`, `"remote"`)
- **`envvars`** (list): References to environment variable specification IDs
- **`env`** (dict): Environment variables to set for the server process
- **`tags`** (list): Categorization tags

### Environment Variables
Use `${VAR_NAME}` syntax in args for environment variable expansion:
```yaml
args:
  - "-m"
  - "mcp_remote"
  - "--Authorization"
  - "Bearer ${KAGGLE_TOKEN}"
```

### Example
```yaml
id: kaggle
name: Kaggle MCP Server
description: Access Kaggle datasets, competitions, and kernels

command: python
args:
  - "-m"
  - "mcp_remote"
  - "--Authorization"
  - "Bearer ${KAGGLE_TOKEN}"
  - "--accept"
  - "application/json"
  - "--"
  - "https://mcp.kaggle.com"

transport: remote

envvars:
  - KAGGLE_TOKEN

tags:
  - data
  - kaggle
  - datasets
```

## Skill Specifications

### Required Fields
- **`id`** (string): Unique identifier (kebab-case)
- **`name`** (string): Display name
- **`description`** (string): Skill capabilities description
- **`module`** (string): Python module path (e.g., `"agent_skills.data_analysis"`)

### Optional Fields
- **`envvars`** (list): References to environment variable specification IDs
- **`optional_env_vars`** (list): Optional environment variables
- **`dependencies`** (list): Required Python packages
- **`tags`** (list): Categorization tags

### Example
```yaml
id: data-analysis
name: Data Analysis Skill
description: Perform statistical analysis and data visualization

module: agent_skills.data_analysis

envvars:
  - OPENAI_API_KEY

optional_env_vars:
  - PLOT_DPI
  - CHART_THEME

dependencies:
  - pandas>=2.0.0
  - matplotlib>=3.7.0
  - seaborn>=0.12.0
  - numpy>=1.24.0

tags:
  - data
  - analysis
  - visualization
```

## Environment Variable Specifications

### Required Fields
- **`id`** (string): Unique identifier (UPPER_SNAKE_CASE, e.g., `"KAGGLE_TOKEN"`)
- **`name`** (string): Display name
- **`description`** (string): Purpose and usage description

### Optional Fields
- **`registrationUrl`** (string): URL where users can obtain the variable (e.g., API key registration page)
- **`tags`** (list): Categorization tags

### Linking to Specs
Environment variables are linked to MCP servers and skills through the `envvars` field:

```yaml
# In MCP server or skill spec
envvars:
  - KAGGLE_TOKEN
  - GITHUB_TOKEN
```

### Example
```yaml
id: KAGGLE_TOKEN
name: Kaggle API Token
description: >
  API token for accessing Kaggle datasets, competitions, notebooks, and models.
  Required for Kaggle MCP server authentication.
registrationUrl: https://www.kaggle.com/settings/account

tags:
  - authentication
  - api-key
  - kaggle
  - data
```

### Available Environment Variables
See `specs/envvars/` for all defined environment variables:
- **KAGGLE_TOKEN**: Kaggle API authentication
- **GITHUB_TOKEN**: GitHub authentication for MCP server and skills
- **TAVILY_API_KEY**: Tavily search and web crawling
- **ALPHAVANTAGE_API_KEY**: Alpha Vantage financial data
- **SLACK_BOT_TOKEN**: Slack bot authentication
- **SLACK_TEAM_ID**: Slack workspace identifier
- **SLACK_CHANNEL_IDS**: Slack channel access list
- **GOOGLE_OAUTH_CLIENT_ID**: Google Workspace OAuth client ID
- **GOOGLE_OAUTH_CLIENT_SECRET**: Google Workspace OAuth secret

## Schema Validation

All YAML specifications are validated against the JSON Schema defined in `agent-spec.schema.yaml`.

The schema validates:
- Required fields are present
- ID format (kebab-case for most, UPPER_SNAKE_CASE for envvars)
- Color format (hex codes like `#3B82F6`)
- List and object structures
- Field types and constraints



## Creating New Specifications

### Adding a New Agent
1. Choose the appropriate folder: `code-ai/`, `codemode-paper/`, or `datalayer-ai/`
2. Create `agentspecs/agents/<folder>/my-agent.yaml`
3. The agent ID will automatically become `<folder>/my-agent`
4. Follow the Agent Specification format described above

### Adding a New MCP Server
1. Create `agentspecs/mcp-servers/my-server.yaml`
2. Follow the MCP Server Specification format described above

### Adding a New Skill
1. Create `agentspecs/skills/my-skill.yaml`
2. Follow the Skill Specification format described above

### Adding a New Environment Variable
1. Create `agentspecs/envvars/MY_VAR.yaml`
2. Use UPPER_SNAKE_CASE for the filename and `id` field
3. Follow the Environment Variable Specification format described above

## Environment Variable References

MCP servers and skills can reference environment variables defined in the `envvars/` directory:

- **`envvars`**: List of environment variable IDs that are required
- **`optional_env_vars`**: List of environment variable IDs that are optional
- **`env`**: Dictionary of environment variables to set for the server process
- **Variable Expansion**: Use `${VAR_NAME}` syntax in args for runtime expansion

Example:
```yaml
# MCP server with auth token
args:
  - "--Authorization"
  - "Bearer ${KAGGLE_TOKEN}"

envvars:
  - KAGGLE_TOKEN
```

The `${KAGGLE_TOKEN}` will be expanded at runtime by consuming systems.

## Best Practices

1. **Naming**: Use kebab-case for IDs (`data-acquisition`, not `data_acquisition`). Exception: envvars use UPPER_SNAKE_CASE.
2. **Descriptions**: Be specific about capabilities and use cases
3. **Tags**: Use consistent tags across related specs for better categorization
4. **Environment Variables**: Always define envvars in `envvars/` directory and reference them by ID
5. **Dependencies**: Pin major versions for skills (`pandas>=2.0.0`) to avoid breaking changes
6. **Colors**: Use hex color codes consistently (e.g., `#3B82F6` for blue)
7. **Suggestions**: Provide 3-5 clear, actionable example prompts
8. **System Prompts**: Keep base `system_prompt` general, use `system_prompt_codemode_addons` for execution-specific instructions
9. **Organization**: Place agents in appropriate subfolders (code-ai/, codemode-paper/, datalayer-ai/) based on their purpose

## YAML Guidelines

### Valid YAML
- Use 2 spaces for indentation (not tabs)
- Quote strings that contain special characters
- Use `>` or `|` for multi-line strings
- Ensure all required fields are present

### Common Issues
- **Invalid indentation**: Use 2 spaces consistently
- **Missing required fields**: Check schema for required fields (id, name, description)
- **Invalid ID format**: Use kebab-case (lowercase with hyphens)
- **Invalid color codes**: Use 6-digit hex codes starting with # (e.g., `#3B82F6`)
- **Broken references**: Ensure referenced envvars, skills, or mcp_servers exist

## Contributing

When adding new specifications:
1. Follow the YAML schema format defined in `agent-spec.schema.yaml`
2. Add appropriate tags for categorization
3. Define environment variables in `envvars/` directory
4. Use consistent naming conventions (kebab-case for most, UPPER_SNAKE_CASE for envvars)
5. Provide clear descriptions and examples
6. Update this README if adding new patterns or conventions

## Available MCP Servers

The following MCP servers are defined in `agentspecs/mcp-servers/`:

- `tavily` - Web search via Tavily API
- `filesystem` - Local filesystem operations
- `github` - GitHub repository operations
- `google-workspace` - Google Workspace integration
- `slack` - Slack messaging
- `kaggle` - Kaggle datasets and competitions
- `alphavantage` - Financial market data
- `chart` - Chart generation

Reference these server IDs in the `mcp_servers` field of agent specifications.

## Best Practices

### Naming
- **ID**: kebab-case (`data-acquisition`)
- **Name**: Title Case with "Agent" suffix
- **Constants**: Auto-generated as `SCREAMING_SNAKE_CASE_AGENT_SPEC`

### Colors
- **Blue** (`#3B82F6`): Data and information
- **Green** (`#10B981`): Web and networking
- **Indigo** (`#6366F1`): Development and code
- **Amber** (`#F59E0B`): Finance and analytics
- **Pink** (`#EC4899`): Communication and workflow

### Content Guidelines
- **Descriptions**: 1-2 sentences, present tense
- **Suggestions**: 3-5 concrete examples with action verbs
- **Tags**: 2-5 relevant categorization keywords

## Design Principles

1. **Single Source of Truth**: YAML files are the authoritative specification
2. **Declarative**: Define what agents can do, not how they do it
3. **Composable**: Agents reference MCP servers and skills by ID
4. **Validated**: JSON Schema ensures consistency and correctness
5. **Extensible**: Easy to add new fields or specification types
6. **Human-Readable**: YAML format is easy to read and edit

## Specification Structure

### Agent Hierarchy
```
Agent Specification
├── Basic Info (id, name, description, tags)
├── Configuration (enabled, environment_name)
├── Capabilities
│   ├── MCP Servers (references to mcp-servers/*.yaml)
│   └── Skills (references to skills/*.yaml)
├── UI Customization (icon, emoji, color)
├── User Guidance (suggestions, welcome_message)
└── Prompts
    ├── system_prompt (base instructions)
    └── system_prompt_codemode_addons (execution mode instructions)
```

### MCP Server Specification
```
MCP Server Specification
├── Basic Info (id, name, description, tags)
├── Execution (command, args, transport)
├── Environment
│   ├── envvars (required environment variables)
│   └── env (variables to set for the process)
└── UI (icon, emoji)
```

### Skill Specification
```
Skill Specification
├── Basic Info (id, name, description, tags)
├── Implementation (module)
├── Environment
│   ├── envvars (required environment variables)
│   └── optional_env_vars (optional variables)
├── Dependencies (Python packages)
└── UI (icon, emoji)
```

### Environment Variable Specification
```
Environment Variable Specification
├── Basic Info (id, name, description)
├── Registration (registrationUrl)
├── Categorization (tags)
└── UI (icon, emoji)
```

## License

Copyright (c) 2025-2026 Datalayer, Inc.
Distributed under the terms of the Modified BSD License.
