# Company OS Agent Contract

HermesCorp is the source of truth for Hermes Company OS: opinionated company
onboarding, reusable operating skills, provider integrations, profile packages,
and proof that Hermes can work through real company tools.

## Product boundaries

- Treat `.hermes.md` as a concise company operating map, not agent memory or a
  copied company database.
- Keep source applications authoritative for their records and files.
- Keep provider credentials and transient connection health out of `.hermes.md`.
- Use root `skills/` packages as canonical reusable procedures. Profile copies
  are distribution artifacts and must remain synchronized with their root owner.
- Do not create one skill per Work, People, Knowledge, Communications, or
  Decisions surface. Add a skill only for a repeatable procedure or channel.
- Keep consequential external writes approval-gated.
- Never commit live company data, credentials, profile state, or generated run
  artifacts.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/company-os-onboarding/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/notion-webhook-onboarding/tests -p 'test_*.py' -v
python3 -m json.tool skills/company-os-onboarding/evals/evals.json >/dev/null
python3 -m json.tool skills/notion-webhook-onboarding/evals/evals.json >/dev/null
node scripts/sync-kamdar-notion-webhook.mjs \
  --target profiles/kamdar-ai --check
npm test
```
