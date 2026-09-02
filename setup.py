#!/usr/bin/env python3
"""Bootstrap the customer-facing Company OS setup command."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_ui_runtime() -> None:
    """Restart with Hermes' bundled Python when local UI dependencies are absent."""
    try:
        import prompt_toolkit  # noqa: F401
        import pydantic  # noqa: F401
        import rich  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    script = Path(__file__).resolve()
    hermes_roots = [script.parents[2]] if len(script.parents) > 2 else []
    hermes_roots.append(Path.home() / ".hermes")
    candidates = [
        Path(os.environ["HERMES_PYTHON"])
        if os.environ.get("HERMES_PYTHON")
        else None,
        *(root / "hermes-agent" / "venv" / "bin" / "python" for root in hermes_roots),
        *(
            root / "hermes-agent" / "venv" / "Scripts" / "python.exe"
            for root in hermes_roots
        ),
    ]
    for candidate in candidates:
        if (
            candidate
            and candidate.is_file()
            and candidate.resolve() != Path(sys.executable).resolve()
        ):
            os.execv(str(candidate), [str(candidate), str(script), *sys.argv[1:]])
    raise SystemExit(
        "Rich, prompt_toolkit, and Pydantic are bundled with Hermes, but its Python runtime "
        "could not be found."
    )


def main() -> int:
    _ensure_ui_runtime()
    from apps.installer.cli.app import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
