# Howie AI schedule policy

This file is policy, not cron configuration. Synchronizing the profile must
never register, import, copy, or enable a Hermes cron job.

## Default: disabled

There is no automatic pulse. Before any manual proof, Howie must complete the
activation gates in `profile.manifest.json`: profile creation, private employee
directory, reviewed rendered configuration, a private runtime configuration,
and one controlled opted-in test employee. Telegram remains unpaired and the
gateway remains stopped while this policy is only source-controlled.

## After controlled activation

| Trigger | Cadence | Permitted result |
| --- | --- | --- |
| Meeting summary | Manual self-chat event | Native file editing creates only missing canonical `tickets/TASK-XXXX/` folders in the dedicated company workspace. |
| Reply or artifact event | Manual self-chat event | Native file editing accepts only a matching ticket/requirement and appends its canonical progress event. |
| Follow-up draft | Manual deterministic run | A due human requirement receives one append-only `telegram_delivery_draft`; no message is sent. |
| Delivery worker | Manual, explicit gate | Dry-run is the default. `--send` and `HOWIE_POC_ENABLE_SEND=1` are both required before the worker may invoke `hermes send`. |

## Delivery and stop conditions

- The delivery worker validates the private employee directory's known ID,
  inbound/outbound permission, opt-in, target, timezone, cooldown, idempotency,
  and explicit send gate before it calls Hermes. The profile itself never reads
  that directory or sends a chase.
- A blocked ticket records its missing input/review and each requirement's own
  next permitted chase; it never infers a resolution from a vague reply.
- Unknown contacts, malformed ticket state, unavailable scoped Drive input, or
  any direct-send path outside the worker fail closed.
- Native file editing is allowed only by declared-workspace convention; it is
  not sandboxed. Do not run this proof against a customer workspace or machine.
- Every activation, gateway start, Drive login, and Telegram pairing is a
  manual operator action outside this repository and outside the sync script.
