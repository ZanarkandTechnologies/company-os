# Evaluation viewer

This first-class package turns one shared PM Daily/PM Weekly eval run into a
private, inspectable dossier.

```text
apps/eval_viewer/
├── build.py       # static HTML and model writer
├── model.py       # eval evidence-to-view-model projection
├── serve.py       # localhost-only development server
├── tests/         # viewer behavior and safety tests
└── dist/          # ignored generated output
```

Farplane-compliant capability checks live in each
`skills/pm-*/evals/evals.json`. The runner executes each automation once and
then writes all `eval_results` into one `eval-receipt.json`; it never invokes an
automation once per eval row. The viewer joins those results by `eval_id`, puts
rows tagged `showcase` first while preserving source order, and renders the
authored title, description, resultant artifacts, and assertion evidence.

```bash
python3 -m apps.eval_viewer.build --out apps/eval_viewer/dist \
  --eval-run /absolute/private/path/to/eval-run
python3 -m apps.eval_viewer.serve
python3 -m unittest apps.eval_viewer.tests.test_viewer -v
```

Generated files are private, owner-only artifacts. Provider mutations are
accepted only for a named isolated eval scope with successful read-back proof;
analysis-only receipts must record zero mutations.

The customer command that creates and opens this input end to end is:

```bash
python3 setup.py doctor eval --profile-home /absolute/profile/path --open
```
