"""Visible subprocess boundary for interactive Hermes commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from apps.installer import runtime


def _print_diagnostic(text: str) -> None:
    """Print provider diagnostics without letting a legacy Windows code page crash setup."""
    encoding = sys.stdout.encoding or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding)
    print(safe_text, end="")


def run_visible(arguments: list[str], profile_home: Path) -> int:
    result = subprocess.run(
        arguments,
        check=False,
        env=runtime.profile_environment(profile_home),
    )
    return result.returncode


def run_mcp_test_visible(name: str, profile_home: Path) -> int:
    """Show Hermes MCP diagnostics and return failure from its proof markers."""
    result = subprocess.run(
        ["hermes", "mcp", "test", name],
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=runtime.profile_environment(profile_home),
    )
    if result.stdout:
        _print_diagnostic(result.stdout)
    if result.stderr:
        _print_diagnostic(result.stderr)
    return 0 if runtime.mcp_connection_ready(result) else 1
