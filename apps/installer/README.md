# Company OS installer

This first-class package owns customer installation, configuration,
certification, maintenance, and setup verification. Product automations and
their skill-owned templates and evaluation cases remain outside its source
package; the workspace installer copies those runtime inputs. The evaluation
viewer remains a development app.

The normal flow is feature-first. It asks explained questions about memory,
Daily Review + Chase, and Weekly reporting. Answers are saved privately at
`config/setup-answers.json`, then compiled into named slots inside the Daily
and Weekly Markdown. Hermes reads those rendered contracts directly and never
loads the answer JSON at runtime. See [design.md](design.md).

```text
apps/installer/
├── cli/                # guided commands and interactive flows
├── runtime.py          # deterministic profile operations and health checks
├── profile.py          # Hermes plugin and schedule reconciliation
├── workspace.py        # reviewed source-to-runtime installer
├── e2e.py              # isolated Docker installer proof
├── compose.e2e.yaml    # isolated E2E override
├── docs/               # customer and configuration documentation
└── tests/              # installer-owned proof
```

The repository-root `setup.py` and `setup.cmd` are stable customer entry
points. They contain no installer workflow logic. `compose.yaml` remains at
the root because Docker Compose and the Windows launcher discover it there.

```bash
python3 setup.py --help
python3 setup.py features
python3 -m unittest apps.installer.tests.test_architecture apps.installer.tests.test_init -v
```
