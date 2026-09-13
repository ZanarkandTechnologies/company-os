"""Read-only Discord context tools for Company OS automations.

This adapter reuses Hermes' native Discord client and deliberately exposes only
the discovery and history reads needed by Daily. Gateway delivery remains a
separate Hermes concern.
"""

from __future__ import annotations

import json
from typing import Any

from tools.discord_tool import (
    DiscordAPIError,
    _discord_request,
    _get_bot_token,
    check_discord_tool_requirements,
    discord_admin_handler,
)


READ_ACTIONS = (
    "list_guilds",
    "server_info",
    "list_channels",
    "channel_info",
    "fetch_messages",
    "list_pins",
    "list_active_threads",
    "list_archived_threads",
)


def _read(args: dict[str, Any] | None = None, **_: Any) -> str:
    values = dict(args or {})
    action = str(values.pop("action", ""))
    if action not in READ_ACTIONS:
        raise ValueError(f"unsupported Discord context action: {action}")
    if action in {"fetch_messages", "list_active_threads", "list_archived_threads"}:
        # Hermes' native loader drops plugin-defined action names. Read the
        # same configured allowlist without discarding these two read actions.
        from hermes_cli.config import load_config

        try:
            raw = (load_config().get("discord") or {}).get("server_actions")
        except Exception:
            return json.dumps({"error": "discord_configuration_unavailable"})
        if raw is None or raw == "":
            allowed = None
        elif isinstance(raw, str):
            allowed = [name.strip() for name in raw.split(",") if name.strip()]
        elif isinstance(raw, (list, tuple)):
            allowed = [str(name).strip() for name in raw]
        else:
            return json.dumps({"error": "Invalid discord.server_actions configuration"})
        if allowed is not None and action not in allowed:
            return json.dumps({"error": f"Action {action} is disabled by discord.server_actions"})
        token = _get_bot_token()
        if not token:
            return json.dumps({"error": "DISCORD_BOT_TOKEN not configured"})
        key = "guild_id" if action == "list_active_threads" else "channel_id"
        identifier = str(values.get(key, ""))
        if not identifier.isascii() or not identifier.isdecimal():
            return json.dumps({"error": f"A numeric {key} is required"})
        if action == "list_active_threads":
            path, params = f"/guilds/{identifier}/threads/active", None
        else:
            path = (f"/channels/{identifier}/messages" if action == "fetch_messages"
                    else f"/channels/{identifier}/threads/archived/public")
            try:
                limit = min(max(int(values.get("limit", 50 if action == "fetch_messages" else 100)), 1), 100)
            except (TypeError, ValueError, OverflowError):
                return json.dumps({"error": "discord_invalid_limit"})
            params = {"limit": str(limit)}
            if values.get("before"):
                params["before"] = str(values["before"])
            if action == "fetch_messages" and values.get("after"):
                params["after"] = str(values["after"])
        try:
            payload = _discord_request("GET", path, token, params=params)
            if action == "fetch_messages":
                if not isinstance(payload, list) or any(not isinstance(message, dict) or "id" not in message for message in payload):
                    return json.dumps({"error": "discord_output_invalid"})
                # Keep source bodies, embeds, replies, and attachment metadata.
                # Preserve the native envelope and readable author field.
                for message in payload:
                    author = message.get("author")
                    if isinstance(author, dict):
                        author.setdefault("display_name", author.get("global_name"))
                return json.dumps({"messages": payload, "count": len(payload)})
            return json.dumps(payload)
        except DiscordAPIError as error:
            result = {"error": "discord_read_failed", "http_status": error.status}
            try:
                details = json.loads(error.body)
            except (ValueError, TypeError):
                details = {}
            if isinstance(details, dict):
                for key in ("code", "retry_after"):
                    value = details.get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        result[key] = value
            return json.dumps(result)
        except (OSError, TimeoutError):
            return json.dumps({"error": "discord_transport_failed"})
        except (ValueError, TypeError):
            return json.dumps({"error": "discord_output_invalid"})
    return discord_admin_handler(action=action, **values)


def register(ctx) -> None:
    ctx.register_tool(
        name="discord_context_read",
        toolset="discord-context",
        handler=_read,
        check_fn=check_discord_tool_requirements,
        emoji="💬",
        schema={
            "name": "discord_context_read",
            "description": (
                "Read Discord server structure and bounded message history for "
                "Company OS context collection. This tool cannot mutate Discord."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": list(READ_ACTIONS)},
                    "guild_id": {"type": "string", "description": "Required for list_active_threads; discover it with channel_info on the forum."},
                    "channel_id": {"type": "string", "description": "Forum ID for list_archived_threads; thread ID for fetch_messages."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    "before": {
                        "type": "string",
                        "description": "Message ID for fetch_messages; oldest archive_timestamp for the next list_archived_threads page when has_more is true.",
                    },
                    "after": {"type": "string"},
                },
                "required": ["action"],
            },
        },
    )
