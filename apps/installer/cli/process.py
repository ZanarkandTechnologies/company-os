"""Visible subprocess boundary for interactive Hermes commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from apps.installer import runtime


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
        capture_output=True,
        env=runtime.profile_environment(profile_home),
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    return 0 if runtime.mcp_connection_ready(result) else 1
