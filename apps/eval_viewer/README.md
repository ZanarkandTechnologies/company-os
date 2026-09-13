# Evaluation viewer

This first-class package turns one shared PM Daily/PM Weekly eval run into a
private, inspectable dossier.

```text
apps/eval_viewer/
├── build.py       # static HTML and model writer
├── model.py       # eval evidence-to-view-model projection
├── serve.py       # localhost-only development server
└── dist/          # ignored generated output
```

- Skill cases live in `skills/pm-*/evals/evals.json`; automation cases live in
  `automations/evals/evals.json`.
- The runner uses a fresh session per selected skill case, then writes one
  `eval-receipt.json`. Automation cases remain `NOT RUN` until their adapter exists.
- The viewer uses the run's frozen catalog, joins by `eval_id`, and puts
  `showcase` cases first within each group.
- Inspect JSON artifacts, assertion evidence, execution failures and unrun cases
  separately. A passing selected case does not mean the full system passed.

```bash
python3 -m apps.eval_viewer.build --out apps/eval_viewer/dist \
  --eval-run /absolute/private/path/to/eval-run
python3 -m apps.eval_viewer.serve
```

Generated files are private, owner-only artifacts. Provider mutations are
accepted only for a named isolated eval scope with successful read-back proof;
analysis-only receipts must record zero mutations.

Run the skill evals and open their dossier:

```bash
python3 setup.py doctor eval --profile-home /absolute/profile/path --open
```

Add repeatable `--case <eval-id>` arguments for a bounded skill replay. The
`doctor open` command opens the latest dossier without rerunning models.
