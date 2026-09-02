---
automation_id: company-os-weekly-meeting-ticket
automation_version: "1.0.0"
kind: company-os-automation
cadence: weekly
company_timezone: Asia/Kuala_Lumpur
---

# Weekly meeting ticket

## Purpose

Create at most one ready-to-use weekly meeting ticket.

## Authority

Create only the ticket configured below. Never infer another workspace,
project, assignee, date, or destination.

## Todo List

- [ ] **1 — Resolve this week's ticket.**

  Use the company timezone and current ISO week.

  <!-- setup:weekly_meeting.template -->
  Title the ticket `Weekly operating review — YYYY-Www`. Include links or
  paths to the weekly reports, unresolved risks, decisions needed, owners, and
  next-week commitments.
  <!-- /setup:weekly_meeting.template -->

- [ ] **2 — Check and create.**

  <!-- setup:weekly_meeting.destination -->
  Do not create a weekly meeting ticket. Record `skipped_disabled` and call no
  task integration.
  <!-- /setup:weekly_meeting.destination -->

  If enabled, list issues in the exact configured workspace and project. Read
  pages of 100 with increasing offsets until the title is found or a page
  returns fewer than 100 issues. If an issue has the exact rendered weekly
  title, record `duplicate` and stop.
  Otherwise create one issue with that title and body. Read the returned issue,
  require an exact title match, and record its ID and identifier.

- [ ] **3 — Write the receipt.**

  Write `weekly/receipts/meeting-ticket-YYYY-Www.json` with the title, exact
  destination, status (`applied`, `duplicate`, `skipped_disabled`, `blocked`,
  or `failed`), and returned issue ID. Do not copy credentials into the receipt.
