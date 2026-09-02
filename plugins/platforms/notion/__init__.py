"""Hermes-native Notion platform plugin."""

from typing import Any


def register(*args: Any, **kwargs: Any) -> Any:
    """Load the Hermes gateway dependency only when the plugin is registered."""
    from .adapter import register as register_adapter

    return register_adapter(*args, **kwargs)


__all__ = ["register"]
