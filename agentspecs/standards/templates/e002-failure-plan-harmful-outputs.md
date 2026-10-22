---
control: E002
title: AI failure plan for harmful outputs
reviewed_every_months: 12
---

# AI failure plan for harmful outputs

**Organization:** {{ organization }} · **Owner:** {{ owner }} · **Version:** {{ version }} · **Review by:** {{ review_on }}

What {{ organization }} does when an application answers something harmful — dangerous advice, abuse, content against the law or against the organization's acceptable use — to a customer or to the public.

## How it is noticed

- A person's thumb down or report on the answer, kept in the application's record and read on its Activity.
- The safety tests every application runs before it ships, and the drills the Shield runs.
- A customer, a partner or the press.

## Who acts

| Role | Who | How to reach them |
| --- | --- | --- |
| Response lead | {{ response_lead }} | {{ response_lead_contact }} |
| Communications | {{ communications_contact }} | {{ communications_contact_contact }} |

## Within the first hour

1. Pause the application or the conversation it happened in; keep the record.
2. Read what was asked and what it answered, and which rules decided the actions around it.
3. Tell the person it was said to, when they can be reached.

## Within the first day

- Decide whether the answer is one the application can give again: a rule or a context changed, a test added that would have caught it.
- Decide who else must be told ({{ who_is_told }}).

## After

- The version shipped again only once the new test passes.
- A review within {{ review_days }} days, kept with this plan.
