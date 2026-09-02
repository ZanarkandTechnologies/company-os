"""Parse one model JSON object without trusting surrounding CLI presentation."""

from __future__ import annotations

import json
import re
from typing import Any


FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)


def json_object(raw: str, error: Exception) -> dict[str, Any]:
    """Return the last complete object, preferring fenced model output."""
    fenced = FENCED_JSON.findall(raw)
    for candidate in reversed(fenced):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        value = None
    if isinstance(value, dict):
        return value
    decoder = json.JSONDecoder()
    objects: list[tuple[int, int, dict[str, Any]]] = []
    for position, character in enumerate(raw):
        if character != "{":
            continue
        try:
            value, consumed = decoder.raw_decode(raw[position:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            objects.append((position + consumed, consumed, value))
    if objects:
        return max(objects, key=lambda item: (item[0], item[1]))[2]
    raise error
