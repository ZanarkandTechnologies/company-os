"""Explicit Discord route setup, status, and one-message connection test."""

from __future__ import annotations

import hashlib
from pathlib import Path

from apps.installer import runtime
from apps.installer.cli.ui import CONSOLE, confirm
from apps.installer.schemas.workspace import (
    MessageType,
    MessagingApp,
    MessagingTestReceipt,
    configuration_hash,
    parse_workspace_communications,
)
from plugins.platforms.discord import api, onboarding


def _bindings(profile_home: Path):
    path = profile_home / "workspace.hermes.md"
    try:
        rows = parse_workspace_communications(path.read_text(encoding="utf-8")).communications
    except OSError as error:
        raise runtime.RuntimeSetupError("discord_workspace_not_installed") from error
    selected = [row for row in rows if row.app is MessagingApp.DISCORD and row.message in {MessageType.OWNER_REPORT, MessageType.OWNER_ALERT}]
    if not selected:
        raise runtime.RuntimeSetupError("discord_owner_route_not_configured")
    return selected


def configure_command(profile_home: Path) -> int:
    onboarding.configure_owner_route(profile_home)
    return 0


def status_command(profile_home: Path) -> int:
    configured = runtime.configured_secret_names(profile_home)
    required = {"DISCORD_BOT_TOKEN", "DISCORD_OWNER_GUILD_ID", "DISCORD_OWNER_CHANNEL_ID"}
    CONSOLE.print("Discord route: " + ("configured" if required <= configured else "not configured"))
    return 0 if required <= configured else 1


def test_command(profile_home: Path) -> int:
    bindings = _bindings(profile_home)
    binding = bindings[0]
    token = runtime.read_profile_secret(profile_home, "DISCORD_BOT_TOKEN") or ""
    try:
        client = api.DiscordClient(token)
        target = client.resolve_target(
            runtime.read_profile_secret(profile_home, "DISCORD_OWNER_GUILD_ID") or "",
            runtime.read_profile_secret(profile_home, "DISCORD_OWNER_CHANNEL_ID") or "",
        )
    except (api.DiscordApiError, api.DiscordCredentialError, ValueError) as error:
        raise runtime.RuntimeSetupError(str(error)) from error
    if not confirm(f"Send one visible connection test to #{target.channel_name or target.channel_id}?", default=False):
        return 1
    result = client.send_message(target, f"Hermes connection test for {binding.send_to}. This does not enable employee messages.")
    confirmed = confirm(f"Did {binding.send_to} receive that exact test message?", default=False)
    receipt = MessagingTestReceipt(
        configuration_sha256=configuration_hash(bindings), app=MessagingApp.DISCORD,
        recipient_sha256=hashlib.sha256(binding.send_to.casefold().encode()).hexdigest(),
        status="passed" if confirmed else "failed", recipient_confirmed=confirmed,
        exact_target=target.exact_target,
        target_sha256=hashlib.sha256(target.exact_target.encode()).hexdigest(),
        message_id=result["message_id"],
    )
    runtime.write_messaging_test_receipt(profile_home, receipt.model_dump(mode="json"))
    CONSOLE.print("[green]Discord connection confirmed.[/green]" if confirmed else "[yellow]Discord test was not confirmed; writes remain disabled.[/yellow]")
    return 0 if confirmed else 2
