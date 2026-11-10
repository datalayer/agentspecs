---
sidebar_position: 2
title: Protocol Tools
---

# Protocol Tool Specifications

A protocol tools spec is the table of what each tool of one agent protocol
does to the world. An agent protocol's tools are a toolset of Datalayer's MCP
gateway reached through a protocol connection (`pap:<domain>`,
`pact:<brand>`), or the operations of a protocol client (`ucp:`, `acp:`); a
tool's name does not say what it does, so each one is given an **action
class** here, the same way an MCP server of `agentspecs/mcp-servers` says the
classes of its tools under `actions`. The catalogue is
`agentspecs/protocol-tools/`, one YAML per table.

The classes are those of `agentspecs.actions`:

- `read` — looks, and changes nothing;
- `write` — creates or changes something that can be changed back;
- `send` — puts something in front of another person (a mail, a message);
- `buy` — spends money, or commits to;
- `delete` — removes something;
- `publish` — makes something reachable by people who could not reach it.

A tool that does several of these carries several, and is treated as the most
restricted of them. **A tool a table does not name is unknown, and unknown is
the most restricted**: it is never taken for a reader. This is what lets a
Rule written by a person — *ask me before it sends anything* — decide a
protocol's tool with no code of that protocol.

## Fields

| Field | Meaning |
| --- | --- |
| `id`, `name`, `description` | Its id, the name of the protocol, and what its tools are for. |
| `connection` | The prefix of the connections its tools are reached through: a connection's `server` is `<connection>:<domain>`. |
| `actions.checked` | The day the tool names were read off the running toolset. |
| `actions.note` | Why each tool has the class it has, in prose. |
| `actions.tools` | Each tool by name, with its class, or a list of classes. |

```yaml
# protocol-tools/agentic-commerce.yaml
id: agentic-commerce
name: Agentic Commerce Protocol
description: Checking out at a seller over ACP.
connection: acp

actions:
  checked: "2026-10-13"
  note: >-
    Completing a session pays: the exact purchase is always asked of the
    person first, and made at most once.
  tools:
    acp_get_checkout: read
    acp_create_checkout: write
    acp_update_checkout: write
    acp_cancel_checkout: write
    acp_complete: buy
```

## How it is referred to

A [protocol spec](./) names its tables in `protocol_tools`, by id; a table
that does not exist is refused when the catalogue loads. When a tool is called
through a connection, its classes are looked up by the connection's prefix
(`connection_tool_classes()`): a `server` of the form `<prefix>:<domain>`
belongs to the table whose `connection` is that prefix; any other `server` is
an MCP server of the catalogue.

## The catalogue

| Table | Protocol | Connection | Tools and their classes | What it is |
| --- | --- | --- | --- | --- |
| `agentic-commerce` | `acp` | `acp` | `acp_get_checkout` read; `acp_create_checkout`, `acp_update_checkout`, `acp_cancel_checkout` write; `acp_complete` buy | Checking out at a seller over ACP. |
| `pact` | `pact` | `pact` | `pact_brand`, `pact_ask`, `pact_sign_in`, `pact_sign_in_status` read; `pact_ask_for_person`, `pact_disconnect` write | A personal agent at a business's agent, through Datalayer's MCP gateway. |
| `pap` | `pap` | `pap` | `pap_company`, `pap_sign_in`, `pap_sign_in_status`, `pap_read`, `pap_mcp_tools` read; `pap_propose`, `pap_mcp_call`, `pap_disconnect` write; `pap_ask`, `pap_handoff`, `pap_feedback` send; `pap_confirm` write and buy | A person's agent at a company, through Datalayer's MCP gateway. |
| `signed-fetch` | `web-bot-auth` | `signed-fetch` | `signed_fetch` read | Reading a page at a site the application names, signed, through Datalayer's MCP gateway. |
| `ucp` | `ucp` | `ucp` | `ucp_search`, `ucp_get_checkout`, `ucp_get_order` read; `ucp_create_checkout`, `ucp_update_checkout`, `ucp_cancel_checkout` write; `ucp_complete` buy | Shopping at a merchant over UCP. |
