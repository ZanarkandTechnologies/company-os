---
name: meeting-intake
description: Turn a company meeting summary into accountable canonical tickets and the first permitted actions.
metadata:
  hermes:
    requires_toolsets:
      - file
---

# Meeting intake

Read the uploaded `meetings/<meeting-id>/transcript.md` before making any ticket. Extract decisions,
deliverables, owners, reviewers, due dates, dependencies, and missing inputs.
Use `company-directory` only to resolve a safe accountable role projection. A
commitment that needs Drive evidence must first use `drive-company-files`; a
compliance commitment must name `compliance-report`, verified source evidence,
and a compliance reviewer.

For each commitment:

1. Create `tickets/TASK-XXXX/ticket.md` and append the meeting event to
   `progress.md`.
2. Start it in the same turn when all required inputs are available.
3. Otherwise record each missing human input with a separate follow-up
   schedule. A follow-up identifies one role, one question, last attempt, next
   permitted chase, and attempt count.
4. In the owner update, say what was created, what began, what is blocked, who
   will be asked, and when the next chase is due.

Do not invent a second board, change employee data, or claim a message was
sent unless a delivery receipt exists in that ticket's progress log.
