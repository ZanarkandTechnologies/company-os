---
title: Company OS
status: active
owner: Zanarkand Technologies
---

# Company OS

Company OS helps Hermes understand an SME's existing tools through one
workspace-scoped `.hermes.md`. Conversational onboarding maps company Work,
People, Knowledge, Communications, and Decisions to the skills, CLIs, MCPs,
source links, and structures the company already uses.

The first reusable package is
[`company-onboard`](skills/company-onboard/SKILL.md). Its versioned
[`company-workspace.hermes.md`](skills/company-onboard/assets/templates/company-workspace.hermes.md)
template is filled during onboarding and installed as `.hermes.md` in the
company's dedicated Hermes workspace. Connection health remains in a separate
setup receipt.

## Use the skill

Copy the complete package into another project's skill directory:

```bash
mkdir -p <target-project>/skills
cp -R skills/company-onboard <target-project>/skills/
```

Then ask Codex or Hermes to use `company-onboard` to onboard the company's
current stack.

## Verify

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/company-onboard/tests -p 'test_*.py' -v

python3 -m json.tool skills/company-onboard/evals/evals.json >/dev/null
python3 -m json.tool skills/company-onboard/evals/deferred.json >/dev/null
```

See [the onboarding guide](docs/hermes-company-os-onboarding.md) for the runtime
ownership and connector-check flow.
