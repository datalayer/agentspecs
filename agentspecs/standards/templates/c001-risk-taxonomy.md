---
control: C001
title: AI risk taxonomy
reviewed_every_months: 12
---

# The risks the organization's applications carry, named

**Organization:** {{ organization }} · **Owner:** {{ owner }} · **Version:** {{ version }} · **Review by:** {{ review_on }}

Each risk is named once, with what would make it real, how bad it would be, and which rule, test or plan holds it. The conformance report reads this taxonomy as the organization's; the drills and the tests are the evidence against each row.

| Risk | How it happens | Harm | Held by |
| --- | --- | --- | --- |
| An action outside its rules | A prompt that steers the application | Data changed or sent wrongly | The organization's rules; *ask me first* on sending, buying, deleting; the record |
| A credential leaked | A key written into a conversation or a command | Access by others | Credentials kept by Datalayer, redacted at the row |
| A harmful answer | A question outside its scope | Harm to a person | The safety tests; the failure plan E002 |
| A false statement | A model's invention | A person acts on it | The tests against what it knows; the failure plan E003 |
{{ own_risks }}

## Out of scope

{{ out_of_scope }}
