# Company OS Agent Contract

This repository is the source of truth for reusable Company OS skills and
workspace templates.

## Rules

- Keep provider credentials and transient connection health out of `.hermes.md`.
- Provider skills, CLIs, and MCPs own authentication and API mechanics.
- Keep company operating context as a concise index of routes, links,
  structures, and authority boundaries; do not copy source-system content.
- Do not reintroduce intermediary Work, People, Knowledge, Communications, or
  Decisions configuration skills. Add a skill only for a repeatable procedure.
- Update the owning skill, template, tests, evals, and guide together when the
  onboarding contract changes.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/company-onboard/tests -p 'test_*.py' -v
python3 -m json.tool skills/company-onboard/evals/evals.json >/dev/null
python3 -m json.tool skills/company-onboard/evals/deferred.json >/dev/null
```
