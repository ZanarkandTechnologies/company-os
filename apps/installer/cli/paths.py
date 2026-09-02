"""Stable source and profile paths shared by setup flows."""

from __future__ import annotations

from pathlib import Path

from apps.installer import runtime


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE = ROOT / "workspace.hermes.template.md"
DEFAULT_WORKSPACE = ROOT / "workspace.hermes.md"


def profile_home(value: Path | None) -> Path:
    return (value or runtime.default_profile_home()).expanduser().resolve()


def receipt_reference(profile: Path, receipt_path: Path) -> str:
    """Return a stable support reference instead of a container-only path."""
    try:
        return str(receipt_path.relative_to(profile))
    except ValueError:
        return receipt_path.name
