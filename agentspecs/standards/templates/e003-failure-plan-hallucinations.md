---
control: E003
title: AI failure plan for hallucinations
reviewed_every_months: 12
---

# AI failure plan for hallucinations

**Organization:** {{ organization }} · **Owner:** {{ owner }} · **Version:** {{ version }} · **Review by:** {{ review_on }}

What {{ organization }} does when an application states something false as a fact — a price, a term, a figure, a promise — and a person acts on it.

## How it is noticed

- A person's report on the answer, kept in the application's record.
- The tests that compare an answer with what the application knows, run before a version ships and when its drift is measured.
- A customer's claim.

## Who acts

| Role | Who | How to reach them |
| --- | --- | --- |
| Response lead | {{ response_lead }} | {{ response_lead_contact }} |
| Customer contact | {{ customer_contact }} | {{ customer_contact_contact }} |

## Within the first day

1. Read the conversation in the record: what was asked, what was answered, what the application had read.
2. Tell the person what was wrong and what is right.
3. Decide whether the organization makes good on what was promised ({{ remedy_rule }}).

## After

- A test added that asks the same and expects the right answer; the version shipped again once it passes.
- A review within {{ review_days }} days, kept with this plan.
