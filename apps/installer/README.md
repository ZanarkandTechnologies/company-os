# Company OS installer

This first-class package owns customer installation, configuration,
certification, maintenance, and setup verification. Product automations and
their skill-owned templates and evaluation cases remain outside its source
package; the workspace installer copies those runtime inputs. The evaluation
viewer remains a development app.

The normal flow is feature-first. It asks explained questions about memory,
Daily Review + Chase, and Weekly reporting. Project and Work sources support
multiple selections with configuration attached to each selected option. Answers are saved privately at
`config/setup-answers.json`. Edit the 26 questions, options and help text in
[questions.json](questions.json); edit prompt text and replacement tags in
`templates/`. Generation produces both
automations, both skills, selected support files and workspace context.
Hermes reads the generated contracts, not the answer JSON.

```text
apps/installer/
├── cli/                # guided commands and interactive flows
├── runtime.py          # deterministic profile operations and health checks
├── profile.py          # Hermes plugin and schedule reconciliation
├── workspace.py        # reviewed source-to-runtime installer
├── prompt_generation.py # template discovery and deterministic generation
├── questions.json     # editable questionnaire, options and help
├── templates/         # prompt tags, variants and skill packages
└── docs/               # customer and configuration documentation
```

The repository-root `setup.py` and `setup.cmd` are stable customer entry
points. They contain no installer workflow logic. `compose.yaml` remains at
the root because Docker Compose and the Windows launcher discover it there.

```bash
python3 setup.py --help
python3 setup.py features
python3 setup.py questions
python3 setup.py generate
python3 setup.py generate --apply
python3 setup.py generate --output-dir /path/to/output --apply
```

- `features` edits saved answers inline, resumes drafts and previews before saving.
- `generate` previews only; `--apply` writes the source bundle, not the live profile.
- `features --import-answers PATH` explicitly imports old/profile answers; schema-4 structured choices require review.
- Manual generated-file edits block replacement. `--adopt` explicitly accepts replacement with recoverable backups.
- Source answers remain authoritative; installation is a separate operation.
- `questions` prints the validated question list from `questions.json`; no template parsing or synchronization generates that list.
- The superseded `init`/`configure` context wizard is removed; use `features` so edits remain reproducible from answers.
- `--output-dir` chooses the generated package folder, not a Hermes profile activation or credential setup.
- Multi-selects allow repeated entries with independent targets and instructions; Ctrl+N adds an entry and Ctrl+X removes one.
- [Script inventory](../../docs/features/installer-script-inventory.md) records retained services and removed obsolete scripts.
- See [generation contract](../../docs/features/prompt-generation.md) and [verification](../../docs/features/prompt-generation-verification.md).
