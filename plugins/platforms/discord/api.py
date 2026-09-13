"""Bounded Discord Bot API client for the Company OS owner-delivery route."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


API_ROOT = "https://discord.com/api/v10"
MAX_MESSAGE_LENGTH = 2_000
MAX_MESSAGE_CHUNKS = 50
TEXT_CHANNEL_TYPE = 0
_SNOWFLAKE = re.compile(r"^[0-9]{17,20}$")
_DELIVERY_TOKEN = re.compile(r"^[a-f0-9]{64}$")
Opener = Callable[..., Any]


class DiscordCredentialError(RuntimeError):
    """A redacted token-validation failure safe for setup output."""


class DiscordApiError(RuntimeError):
    """A redacted Discord API failure that never includes token material."""


def _setting(name: str, default: str = "") -> str:
    """Read profile-scoped values without borrowing another profile's env."""
    try:
        from agent.secret_scope import UnscopedSecretError, get_secret
    except ModuleNotFoundError:  # Direct unit tests outside the Hermes runtime.
        return str(os.getenv(name, default) or default).strip()
    try:
        value = get_secret(name, default)
    except UnscopedSecretError:
        value = os.getenv(name, default)
    return str(value or default).strip()


def _snowflake(value: str, label: str) -> str:
    cleaned = str(value or "").strip()
    if not _SNOWFLAKE.fullmatch(cleaned):
        raise ValueError(f"{label}_must_be_a_discord_snowflake")
    return cleaned


def neutralize_mentions(content: str) -> str:
    """Prevent all Discord mentions, including role and broadcast mentions."""
    return content.replace("@", "@\u200b")


def _message_content(content: str) -> str:
    cleaned = neutralize_mentions(str(content or "").strip())
    if not cleaned:
        raise ValueError("discord_message_content_required")
    return cleaned


def split_delivery(content: str, delivery_token: str) -> list[str]:
    """Return receipt-friendly Discord chunks with stable, safe headers."""
    if not _DELIVERY_TOKEN.fullmatch(delivery_token):
        raise ValueError("discord_delivery_token_invalid")
    body = _message_content(content)
    # Reserve space for the longest allowed header before calculating chunk count.
    reserved = len(f"[company-os:{delivery_token}:part {MAX_MESSAGE_CHUNKS}/{MAX_MESSAGE_CHUNKS}]\n")
    body_size = MAX_MESSAGE_LENGTH - reserved
    if body_size < 1:
        raise ValueError("discord_delivery_header_too_long")
    parts = [body[index : index + body_size] for index in range(0, len(body), body_size)]
    if len(parts) > MAX_MESSAGE_CHUNKS:
        raise ValueError("discord_message_too_long")
    return [
        f"[company-os:{delivery_token}:part {index}/{len(parts)}]\n{part}"
        for index, part in enumerate(parts, start=1)
    ]


@dataclass(frozen=True)
class DiscordTarget:
    """One exact, approved guild text-channel route."""

    guild_id: str
    channel_id: str
    channel_name: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "guild_id", _snowflake(self.guild_id, "discord_guild_id"))
        object.__setattr__(self, "channel_id", _snowflake(self.channel_id, "discord_channel_id"))

    @property
    def exact_target(self) -> str:
        return f"discord:{self.guild_id}:{self.channel_id}"


class DiscordClient:
    """Small direct client; callers must resolve one target before writes."""

    def __init__(self, token: str, *, opener: Opener = urllib.request.urlopen) -> None:
        self.token = str(token or "").strip()
        if not self.token:
            raise DiscordCredentialError("discord_bot_token_missing")
        self.opener = opener

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        payload = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            API_ROOT + path,
            data=payload,
            method=method,
            headers={
                "Authorization": f"Bot {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "company-os-discord-platform/0.1",
            },
        )
        try:
            with self.opener(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                raise DiscordCredentialError("discord_bot_token_or_permission_invalid") from error
            if error.code == 404:
                raise DiscordApiError("discord_target_not_found") from error
            if error.code == 429:
                raise DiscordApiError("discord_rate_limited") from error
            raise DiscordApiError("discord_api_request_failed") from error
        except (OSError, UnicodeDecodeError, urllib.error.URLError) as error:
            raise DiscordApiError("discord_unavailable") from error
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as error:
            raise DiscordApiError("discord_api_response_invalid") from error
        if not isinstance(parsed, (dict, list)):
            raise DiscordApiError("discord_api_response_invalid")
        return parsed

    def validate_token(self) -> dict[str, str]:
        payload = self._request("GET", "/users/@me")
        if not isinstance(payload, dict) or not _SNOWFLAKE.fullmatch(str(payload.get("id") or "")):
            raise DiscordCredentialError("discord_bot_token_or_permission_invalid")
        return {"id": str(payload["id"]), "username": str(payload.get("username") or "")}

    def bot_role_ids(self, guild_id: str, bot_id: str) -> set[str]:
        """Return only roles Discord reports as assigned to this bot in the guild."""
        expected_guild = _snowflake(guild_id, "discord_guild_id")
        expected_bot = _snowflake(bot_id, "discord_bot_id")
        payload = self._request("GET", f"/guilds/{expected_guild}/members/{expected_bot}")
        if not isinstance(payload, dict) or not isinstance(payload.get("roles"), list):
            raise DiscordApiError("discord_bot_member_invalid")
        return {
            str(role_id) for role_id in payload["roles"]
            if _SNOWFLAKE.fullmatch(str(role_id))
        }

    def resolve_target(self, guild_id: str, channel_id: str) -> DiscordTarget:
        expected_guild = _snowflake(guild_id, "discord_guild_id")
        expected_channel = _snowflake(channel_id, "discord_channel_id")
        guild = self._request("GET", f"/guilds/{expected_guild}")
        channel = self._request("GET", f"/channels/{expected_channel}")
        if not isinstance(guild, dict) or str(guild.get("id") or "") != expected_guild:
            raise DiscordApiError("discord_guild_not_available")
        if not isinstance(channel, dict):
            raise DiscordApiError("discord_channel_invalid")
        if str(channel.get("id") or "") != expected_channel:
            raise DiscordApiError("discord_channel_invalid")
        if str(channel.get("guild_id") or "") != expected_guild:
            raise DiscordApiError("discord_channel_outside_approved_guild")
        if channel.get("type") != TEXT_CHANNEL_TYPE:
            raise DiscordApiError("discord_channel_must_be_text")
        return DiscordTarget(
            guild_id=expected_guild,
            channel_id=expected_channel,
            channel_name=str(channel.get("name") or ""),
        )

    def list_messages(self, target: DiscordTarget, *, limit: int = 50) -> list[dict[str, str]]:
        if limit < 1 or limit > 100:
            raise ValueError("discord_message_limit_must_be_between_1_and_100")
        response = self._request(
            "GET",
            f"/channels/{target.channel_id}/messages?{urllib.parse.urlencode({'limit': limit})}",
        )
        if not isinstance(response, list):
            raise DiscordApiError("discord_messages_response_invalid")
        return [
            {
                "id": str(item.get("id") or ""),
                "channel_id": str(item.get("channel_id") or ""),
                "content": str(item.get("content") or ""),
            }
            for item in response
            if isinstance(item, dict) and str(item.get("channel_id") or "") == target.channel_id
        ]

    def send_message(self, target: DiscordTarget, content: str, *, reply_to: str | None = None) -> dict[str, str]:
        message = _message_content(content)
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError("discord_message_exceeds_2000_characters")
        body: dict[str, Any] = {
            "content": message,
            "allowed_mentions": {"parse": [], "replied_user": False},
        }
        if reply_to and _SNOWFLAKE.fullmatch(reply_to):
            body["message_reference"] = {"message_id": reply_to, "channel_id": target.channel_id}
        response = self._request(
            "POST",
            f"/channels/{target.channel_id}/messages",
            body,
        )
        if not isinstance(response, dict) or not str(response.get("id") or ""):
            raise DiscordApiError("discord_send_response_invalid")
        if str(response.get("channel_id") or "") != target.channel_id:
            raise DiscordApiError("discord_send_target_mismatch")
        return {
            "message_id": str(response["id"]),
            "channel_id": target.channel_id,
            "exact_target": target.exact_target,
        }


def configured_client() -> DiscordClient:
    return DiscordClient(_setting("DISCORD_BOT_TOKEN"))


def configured_target(client: DiscordClient | None = None) -> DiscordTarget:
    resolved = client or configured_client()
    return resolved.resolve_target(
        _setting("DISCORD_OWNER_GUILD_ID"),
        _setting("DISCORD_OWNER_CHANNEL_ID"),
    )


def _write_enabled() -> bool:
    return _setting("DISCORD_ENABLE_WRITES").casefold() == "true"


def discord_get_channel(args: dict | None = None, **kwargs: Any) -> str:
    del args, kwargs
    target = configured_target()
    return json.dumps(
        {
            "guild_id": target.guild_id,
            "channel_id": target.channel_id,
            "channel_name": target.channel_name,
            "exact_target": target.exact_target,
        },
        separators=(",", ":"),
    )


def discord_list_messages(args: dict | None = None, **kwargs: Any) -> str:
    values = args or kwargs
    limit = int(values.get("limit") or 50)
    client = configured_client()
    return json.dumps(client.list_messages(configured_target(client), limit=limit), separators=(",", ":"))


def discord_send_message(args: dict | None = None, **kwargs: Any) -> str:
    values = args or kwargs
    if not _write_enabled():
        raise RuntimeError("Discord writes are disabled; set DISCORD_ENABLE_WRITES=true explicitly")
    client = configured_client()
    return json.dumps(
        client.send_message(configured_target(client), str(values.get("content") or "")),
        separators=(",", ":"),
    )
