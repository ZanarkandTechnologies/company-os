---
template_id: company-os-meeting
template_version: "0.3.1"
name: "{{MEETING_NAME}}"
work_item_id: "{{MEETING_ID}}"
project: "{{PROJECT}}"
department: "{{DEPARTMENT}}"
owner: "{{OWNER}}"
type: "Meeting"
status: "{{STATUS}}"
ai_review: "{{AI_REVIEW}}"
priority: "{{PRIORITY}}"
start_date: "{{START_DATE}}"
due_date: "{{DUE_DATE}}"
progress: "{{PROGRESS}}"
last_meaningful_update: "{{LAST_MEANINGFUL_UPDATE}}"
date: "{{DATE}}"
attendees: "{{ATTENDEES}}"
facilitator: "{{FACILITATOR}}"
---

# {{MEETING_NAME}}

## Purpose and agenda

<!-- Questions or decisions this meeting is intended to resolve.

GOLDEN EXAMPLE — replace every fact below; it demonstrates useful detail.
Resolve whether the three-store count pilot can expand next week, confirm the
variance threshold owner, and assign the missing evidence follow-up.
END GOLDEN EXAMPLE -->

{{PURPOSE_AND_AGENDA}}

## Notes

<!-- Factual discussion notes, source links, and explicit uncertainty. -->

{{NOTES}}

## Decisions

{{DECISIONS_VIEW_OR_LIST — prefer a native linked database filtered to Decisions
created from this Meeting; otherwise render decision, approver, and source.}}

## Commitments

{{COMMITMENTS_VIEW_OR_LIST — prefer a native linked database filtered to Work
created from this Meeting; otherwise render commitment, owner, due date, and source.}}

## Follow-up

<!-- Next meeting, unanswered question, or explicit statement that no follow-up is needed. -->

{{FOLLOW_UP}}
