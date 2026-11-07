---
control: E001
title: AI failure plan for security breaches
reviewed_every_months: 12
---

# AI failure plan for security breaches

**Organization:** {{ organization }} · **Owner:** {{ owner }} · **Version:** {{ version }} · **Review by:** {{ review_on }}

This plan says what {{ organization }} does when an application built on Datalayer, or the data it reaches, is breached: who is told, within what time, what is stopped, and how it is recorded.

## What counts as a breach

A credential of the application or of a person used by someone it was not given to; an action of the application outside its rules that reached data or a system it should not have; a connection reached through the application by an attacker; data of a customer read, changed or sent to the wrong party.

## Who acts

| Role | Who | How to reach them |
| --- | --- | --- |
| Incident lead | {{ incident_lead }} | {{ incident_lead_contact }} |
| Security contact | {{ security_contact }} | {{ security_contact_contact }} |
| Legal and notifications | {{ legal_contact }} | {{ legal_contact_contact }} |

## Within the first hour

1. Pause the application: in the Studio, every shipped version of it is paused by its owner or by the organization, and its record keeps what it did until then.
2. Take back the credentials it held: the application's own key through Datalayer's IAM, the connections' credentials at the connections.
3. Keep the record: the application's activity on Datalayer is the record of what was done; nothing is deleted while the incident is open.

## Within the first day

- Read the record: which sessions, which actions, which rules decided them and who approved what.
- Decide who must be told — customers, authorities, Datalayer — and by when ({{ notification_deadlines }}).
- Write the first account of what happened, for the people above.

## After

- The cause fixed, the rules of the application tightened where they let it happen, and the version shipped again only once its tests pass.
- A review within {{ review_days }} days, kept with this plan, saying what changed.

## Rehearsal

This plan is rehearsed every {{ rehearsal_months }} months; the last rehearsal was on {{ last_rehearsal }}.
