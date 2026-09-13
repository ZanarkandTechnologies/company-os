"""Interactive profile-only setup for the bounded Discord owner route."""

from __future__ import annotations

from pathlib import Path

from rich.panel import Panel

from apps.installer import runtime
from apps.installer.feature_setup import write_batch
from apps.installer.cli.ui import CONSOLE, _prompt_secret, _prompt_text, confirm
from apps.installer.schemas.workspace import (
    CommunicationBinding,
    DeliveryBehavior,
    MANAGED_COMMUNICATIONS,
    MessageType,
    MessagingApp,
    parse_workspace_communications,
    render_workspace_communications,
)
from .api import DiscordApiError, DiscordClient, DiscordCredentialError


def _ensure_owner_report_binding(profile_home: Path, channel_name: str, channel_id: str) -> None:
    """Bind a newly configured private Discord route to one draft-only owner report."""
    workspace = profile_home / "workspace.hermes.md"
    try:
        content = workspace.read_text(encoding="utf-8")
        existing = parse_workspace_communications(content).communications
    except OSError as error:
        raise runtime.RuntimeSetupError("discord_workspace_not_installed") from error
    except ValueError as error:
        raise runtime.RuntimeSetupError("discord_workspace_communications_invalid") from error

    send_to = f"#{channel_name}" if channel_name else f"channel:{channel_id}"
    owner_rows = [
        row for row in existing
        if row.message in {MessageType.OWNER_REPORT, MessageType.OWNER_ALERT}
    ]
    if owner_rows:
        same_route = all(
            row.app is MessagingApp.DISCORD and row.send_to == send_to
            for row in owner_rows
        )
        if not same_route:
            raise runtime.RuntimeSetupError("discord_owner_route_conflicts_with_existing_workspace_route")
        return

    binding = CommunicationBinding(
        message=MessageType.OWNER_REPORT,
        app=MessagingApp.DISCORD,
        send_to=send_to,
        behavior=DeliveryBehavior.PREPARE_DRAFTS,
    )
    rendered = render_workspace_communications([*existing, binding])
    updated, count = MANAGED_COMMUNICATIONS.subn(
        "<!-- hermes:managed communications -->\n"
        + rendered
        + "\n<!-- /hermes:managed communications -->",
        content,
        count=1,
    )
    if count != 1:
        raise runtime.RuntimeSetupError("discord_workspace_communications_missing")
    write_batch(
        {
            workspace: updated,
            profile_home / "workspace" / ".hermes.md": updated,
        }
    )


def configure_owner_route(profile_home: Path) -> None:
    """Validate and store one bot token plus one existing private text channel."""
    if not (profile_home / "distribution.yaml").is_file():
        raise runtime.RuntimeSetupError(
            "discord_profile_not_installed:run_setup_cmd_before_discord_setup"
        )
    CONSOLE.print(Panel.fit(
        "[bold]Connect Discord[/bold]\n"
        "Enter a customer-owned bot token and choose an existing private text channel. "
        "The installer will never create channels or request Administrator permission.",
        border_style="cyan",
    ))
    while True:
        token = _prompt_secret("Discord bot token (hidden): ")
        try:
            client = DiscordClient(token)
            client.validate_token()
            break
        except DiscordCredentialError:
            CONSOLE.print(
                "[yellow]Discord rejected that token. Make sure you copied the Bot Token "
                "from the Developer Portal, not the Application ID or Bot ID, then try again.[/yellow]"
            )
        except DiscordApiError as error:
            CONSOLE.print(
                "[yellow]Discord could not be reached. Check your connection and try again. "
                f"({error})[/yellow]"
            )
    try:
        guild_id = _prompt_text("Discord server ID", console=CONSOLE)
        channel_id = _prompt_text("Existing private text-channel ID", console=CONSOLE)
        target = client.resolve_target(guild_id, channel_id)
    except (DiscordApiError, ValueError) as error:
        raise runtime.RuntimeSetupError(str(error)) from error
    _ensure_owner_report_binding(
        profile_home, target.channel_name or "", target.channel_id
    )
    runtime.save_profile_secret(profile_home, "DISCORD_BOT_TOKEN", token)
    runtime.save_profile_secret(profile_home, "DISCORD_OWNER_GUILD_ID", target.guild_id)
    runtime.save_profile_secret(profile_home, "DISCORD_OWNER_CHANNEL_ID", target.channel_id)
    runtime.save_profile_secret(profile_home, "DISCORD_ENABLE_WRITES", "false")
    assistant = confirm(
        "Enable mention-only Hermes replies in this Discord channel?",
        default=False,
    )
    runtime.save_profile_secret(
        profile_home, "DISCORD_ASSISTANT_ENABLED", "true" if assistant else "false"
    )
    # Hermes' shared gateway authorization is fail-closed. This platform-wide
    # grant is safe here because the adapter discards every DM, guild, channel,
    # unmentioned message, and bot-authored message before gateway dispatch.
    runtime.save_profile_secret(
        profile_home, "DISCORD_ALLOW_ALL_USERS", "true" if assistant else "false"
    )
    if assistant:
        runtime.run_command(
            ["hermes", "plugins", "enable", "platforms/discord", "--no-allow-tool-override"],
            profile_home,
        )
        runtime.run_command(
            ["hermes", "config", "set", "platforms.discord.enabled", "true"],
            profile_home,
        )
        for key, value in (
            ("platforms.discord.home_channel.platform", "discord"),
            ("platforms.discord.home_channel.chat_id", target.channel_id),
            ("platforms.discord.home_channel.name", f"#{target.channel_name or target.channel_id}"),
            ("platforms.discord.home_channel.scope_id", target.guild_id),
        ):
            runtime.run_command(["hermes", "config", "set", key, value], profile_home)
    CONSOLE.print(
        f"[green]Discord route saved:[/green] #{target.channel_name or target.channel_id}. "
        "Writes remain disabled until the connection test is confirmed."
    )
