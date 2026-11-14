---
control: E011
title: Record of processing locations
reviewed_every_months: 12
---

# Where the organization's applications process data

**Organization:** {{ organization }} · **Owner:** {{ owner }} · **Version:** {{ version }} · **Review by:** {{ review_on }}

Where the data an application reads, writes and sends is processed and kept.

## Datalayer

| Where | Location | What runs there |
| --- | --- | --- |
{{ datalayer_locations }}

## Model providers

Each model an application calls is served where its provider serves it; the provider's own pages say where (see the vendor due diligence, E006). {{ model_locations }}

## The organization's own systems

| System | Location | What it holds |
| --- | --- | --- |
{{ own_systems }}

## Transfers

{{ transfers }}
