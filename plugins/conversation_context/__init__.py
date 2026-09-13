"""Read-only Hermes access to explicitly configured private conversation intake."""

from __future__ import annotations

import json
import os
from typing import Any

from .intake import IntakeError, read_project


def read_conversations(args: dict[str, Any] | None = None, **_: Any) -> str:
    root = os.environ.get("COMPANY_OS_CONVERSATION_INTAKE", "").strip()
    if not root:
        return json.dumps({"status": "disabled", "conversations": [], "coverage": []})
    try:
        values = args or {}
        result = read_project(root, values["project_id"], values["week"], values.get("sources"))
    except IntakeError as error:
        result = {"status": "blocked", "error": str(error)}
    except (OSError, ValueError, KeyError, TypeError):
        result = {"status": "blocked", "error": "conversation_intake_invalid"}
    return json.dumps(result, ensure_ascii=False)


def register(ctx) -> None:
    ctx.register_tool(
        name="conversation_read_project_week", toolset="conversation_context",
        handler=read_conversations, check_fn=lambda: True, emoji="💬",
        schema={"name": "conversation_read_project_week",
                "description": "Read bounded, untrusted conversation evidence for one authorized Project and ISO week. No writes or network.",
                "parameters": {"type": "object", "additionalProperties": False,
                               "properties": {"project_id": {"type": "string"}, "week": {"type": "string"},
                                              "sources": {"type": "array", "minItems": 1, "uniqueItems": True,
                                                          "items": {"type": "string", "enum": ["chatgpt_manual", "codex_manual", "codex_local"]}}},
                               "required": ["project_id", "week"]}},
    )
