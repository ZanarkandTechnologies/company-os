---
title: "Howie POC tickets"
status: active
owner: HermesCorp
---

# Howie POC tickets

The runtime ticket folder is the company manager's canonical board. It is
created inside the isolated Howie workspace, not in this source repository:

```text
workspaces/howie-ai/
  tickets/TASK-0001/{ticket.md,progress.md,artifacts/}
  tickets/archive/TASK-0001/
  people/employees.private.json
```

`ticket.md` owns the current task state. `progress.md` is append-only. The
manager process is the single writer; WhatsApp interactions call its bounded
commands rather than editing arbitrary files. Source fixtures and templates are
safe to commit; employee contact data and runtime tickets are ignored.
