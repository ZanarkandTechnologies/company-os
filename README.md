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
[`hermes-company-os`](.agents/skills/hermes-company-os/SKILL.md). Its versioned
[`company-workspace.hermes.md`](.agents/skills/hermes-company-os/assets/templates/company-workspace.hermes.md)
template is filled during onboarding and installed as `.hermes.md` in the
company's dedicated Hermes workspace. Connection health remains in a separate
setup receipt.

## Use the skill

Copy the complete package into another project's skill directory:

```bash
mkdir -p <target-project>/.agents/skills
cp -R .agents/skills/hermes-company-os <target-project>/.agents/skills/
```

Then ask Codex or Hermes to use `hermes-company-os` to onboard the company's
current stack.

## Verify

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s .agents/skills/hermes-company-os/tests -p 'test_*.py' -v

python3 -m json.tool .agents/skills/hermes-company-os/evals/evals.json >/dev/null
python3 -m json.tool .agents/skills/hermes-company-os/evals/deferred.json >/dev/null
```

See [the onboarding guide](docs/hermes-company-os-onboarding.md) for the runtime
ownership and connector-check flow.
