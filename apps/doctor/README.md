# Company OS Doctor

This operator-facing app owns three explicit proof modes:

- `setup.py doctor preflight`: read-only configured-source readiness.
- `setup.py doctor eval --open`: isolated PM Daily/Weekly capability eval and dossier.
- `setup.py doctor analysis`: installed-company analysis without delivery.

`run.py` remains the thin native-Hermes analysis launcher. `evaluation.py`
stages the skill-owned eval catalogs and fixtures, runs each cadence once, and
enforces receipt and tool-safety invariants. Data readiness is owned by
`apps/installer/readiness_evals.py` because it consumes the selected provider
catalog. Doctor never implements provider delivery.
