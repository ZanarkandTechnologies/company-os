# Company OS Doctor

This operator-facing app owns three explicit proof modes:

- `setup.py doctor preflight`: read-only configured-source readiness.
- `setup.py doctor eval --open`: isolated PM Daily/Weekly skill eval and dossier.
- `setup.py doctor analysis`: installed-company analysis without delivery.

`run.py` remains the thin native-Hermes analysis launcher. `evaluation.py`
stages skill-owned fixtures in fresh per-case Hermes sessions and requires one
extraction JSON each. It withholds grading truth, records file changes and tool
traces, and judges against the supplied source evidence. Use repeatable `--case`
arguments for a bounded run. The viewer labels unselected cases `NOT RUN`.
The separate automation catalog includes end-to-end file contracts and
collection/render diagnostics but is not wired to this runner. See
`docs/evaluation.md` for the proof boundaries. Data readiness is owned by
`apps/installer/readiness_evals.py` because it consumes the selected provider
catalog. Doctor never implements provider delivery.
