---
title: "Howie POC dashboard design contract"
ticket_id: TASK-0001
status: accepted
---

# Howie POC dashboard design contract

## Audience and job

Howie opens this dashboard after a weekly meeting to answer three questions in
under a minute: what is blocked, who needs a chase, and what is ready for his
review. It is an operations cockpit, not a developer console.

## Design language

Dense executive operations board: warm off-white canvas, charcoal/navy ink,
blue for live action, amber for dependency waits, emerald for reviewed work,
and restrained red only for overdue escalation. Use compact labels, tabular
numbers, and generous grouping—not dense paragraphs.

## Declared screens and states

1. **Ready state** — empty company board with a single “Scan meeting notes”
   action and no developer setup text.
2. **Meeting imported** — four blocked tickets, explicit owner/reviewer,
   evidence request, next chase time, and a Gantt timeline.
3. **Pulse complete** — activity stream shows one permitted chase and the task
   card shows its updated count and next permitted time.
4. **Unblocked geo report** — reply plus scoped mock Drive source changes the
   card to in progress, displays the artifact template/drive reference, and
   keeps Kenji review visible.
5. **Weekly closeout** — reviewed/archived task contributes to the weekly
   report; admin panel shows employee message eligibility separately from a
   real Drive ACL.

## Layout assertions

```text
desktop (1440px): header 6–12% viewport height; summary strip below;
main board/gantt consumes 58–75% width; sidebar/detail 25–40% width.
narrow (375px): all sections stack; primary actions remain at least 44px high;
no horizontal scrolling; timeline is scrollable inside its own labelled region.
```

Primary action: the currently valid next scenario action in the header or task
detail. It must show visible success/failure feedback without a page reload.

## Non-goals

- No pretend production authentication, Drive ACL editing, WhatsApp sending, or
  agent-control settings.
- No exposed local commands, secrets, or implementation plumbing in the normal
  dashboard surface.
