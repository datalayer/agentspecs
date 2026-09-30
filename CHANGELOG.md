<!--
  ~ Copyright (c) 2025-2026 Datalayer, Inc.
  ~
  ~ BSD 3-Clause License
-->

# Changelog

## 0.0.8

- Models: Cloudflare Workers AI as a provider — `cloudflare:openai/gpt-oss-120b` and
  `cloudflare:meta/llama-3.3-70b-instruct-fp8-fast`, hosted through datalayer-ai-inference.
- An id with a vendor segment (`cloudflare:openai/gpt-oss-120b`) gets an enum name of its own
  (`CLOUDFLARE_OPENAI_GPT_OSS_120B`): the slash is replaced like the colon.
