---
name: company-directory
description: Resolve an employee role from the private directory without exposing phone targets or route policy.
metadata:
  hermes:
    requires_toolsets:
      - file
---

# Company directory

Use this skill to match a ticket's missing input or review to one employee
role. The private directory is policy data, not a contact book or task system.

## Skill signature

```text
company_directory(requirement, private_directory)
  -> SafeDirectoryEntry | blocked
reads: people/employees.private.json
writes: employee ID and role only where the ticket requires accountable ownership
proof: no phone target or route-policy field appears in output, ticket, or progress
```

The private JSON has `schema_version: 1` and an `employees` array. Resolve only
an unambiguous employee with an ID, display name, role/accountability, and
timezone. It may carry private transport fields such as `telegram_target`,
route permission, and test opt-in; those fields are never returned, copied, or
summarized by this skill.

```json
{
  "schema_version": 1,
  "employees": [{
    "id": "finance-lead",
    "display_name": "Finance Lead",
    "role": "Finance Lead",
    "accountable_for": "funding terms and model assumptions",
    "timezone": "Asia/Kuala_Lumpur",
    "telegram_target": "<private>",
    "inbound_allowed": true,
    "outbound_allowed": true,
    "test_opt_in": true,
    "route_enabled": true
  }]
}
```

## Todo

1. Read `people/employees.private.json` only when an exact ticket requirement
   needs an accountable role or named reviewer. Do not scan unrelated employee
   records.
2. Confirm schema version, one matching employee ID/role, active route policy,
   and test opt-in. If the role is absent, ambiguous, disabled, or not opted in,
   keep the requirement blocked.
3. Return only the safe projection: `employee_id`, display name, role,
   accountability, and timezone. Never include `telegram_target`, raw contact
   data, outbound/inbound flags, delivery credentials, or the full directory.
4. Put the resolved employee ID on the matching requirement/review assignment.
   A delivery draft remains draft-only; the controlled delivery worker performs
   its own private target, cooldown, and idempotency checks.

## Gates and completion

- Never create, edit, synchronize, or expose the private directory.
- Do not resolve an employee from a guessed name, a general company label, or a
  prior chat. The directory record is the only authority for role routing.
- Completion is one safe role projection or a recorded blocker. It never means
  that a message was sent.

## Output

```yaml
employee_id: "finance-lead"
display_name: "Finance Lead"
role: "Finance Lead"
accountable_for: "funding terms and model assumptions"
timezone: "Asia/Kuala_Lumpur"
```
