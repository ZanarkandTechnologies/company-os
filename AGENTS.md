# Company OS Agent Contract

HermesCorp is the source of truth for the reusable Hermes Company OS template:
opinionated onboarding, operating skills, provider integrations, and generic
contract proof.

## Product boundaries

- Treat `.hermes.md` as a concise company operating map, not agent memory or a
  copied company database.
- Keep source applications authoritative for their records and files.
- Keep provider credentials and transient connection health out of `.hermes.md`.
- Use root `skills/` packages as canonical reusable procedures. Company
  profiles, workspaces, and company-specific eval suites belong in their
  dedicated project repositories, including sanitized versions.
- Do not create one skill per Work, People, Knowledge, Communications, or
  Decisions surface. Add a skill only for a repeatable procedure or channel.
- Keep consequential external writes approval-gated.
- Never commit live company data, credentials, profile state, or generated run
  artifacts.

## Repository placement gate

Apply this gate before creating or moving any file:

```text
place_artifact(artifact)
  -> HermesCorp when reusable and company-agnostic
  -> dedicated company project when bound to a company, profile, deployment, or eval
```

- Never create `profiles/`, `workspaces/`, `tenants/`, or `fixtures/evals/` in
  HermesCorp. Gitignored or untracked runtime material is still misplaced.
- Treat a company name, company-specific tool layout, rendered `.hermes.md`,
  deployable profile, private-example schema, company corpus, or company eval
  runner as decisive evidence that the dedicated company project owns it.
- Sanitization does not change ownership. A sanitized Howie or Kamdar profile
  remains HowieAI or KamdarAI material.
- Keep only minimal, fictional, company-agnostic fixtures needed to test a
  reusable HermesCorp contract. If the fixture validates one company's setup
  or agent behavior, move the fixture and its runners/tests to that project.
- When extracting misplaced material, preserve it in the dedicated project,
  update its internal paths, remove HermesCorp commands and tests that depend
  on it, and verify both sides. Do not leave a duplicated fallback copy.
- Before completion, confirm the working tree contains no company-owned
  profile/eval/runtime directories and that generic HermesCorp checks still
  pass.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/company-os-onboarding/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/notion-webhook-onboarding/tests -p 'test_*.py' -v
python3 -m json.tool skills/company-os-onboarding/evals/evals.json >/dev/null
python3 -m json.tool skills/notion-webhook-onboarding/evals/evals.json >/dev/null
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/daily-documentation-check/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/setup-company-workspace/tests -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tests -p 'test_create_company_project.py' -v
npm test
```
