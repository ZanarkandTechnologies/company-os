"""Hermes-native Discord delivery connector."""

from typing import Any


def register(*args: Any, **kwargs: Any) -> Any:
    """Register Discord's bounded, profile-scoped tools when installed."""
    from .adapter import register as register_adapter

    return register_adapter(*args, **kwargs)


__all__ = ["register"]
