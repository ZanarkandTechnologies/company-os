"""Interactive ngrok ingress and Notion webhook onboarding flows."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from rich.panel import Panel

from apps.installer import runtime
from apps.installer.cli.ui import CONSOLE, _prompt_secret, _prompt_text, pause
from plugins.platforms.notion import api as notion_api


def _configure_notion_token(profile_home: Path) -> None:
    """Keep the saved token until a candidate has passed Notion validation."""
    saved = runtime.read_profile_secret(profile_home, "NOTION_TOKEN")
    candidate = saved
    while True:
        if not candidate:
            candidate = _prompt_secret("Notion integration token (hidden): ")
        try:
            notion_api.validate_token(candidate)
        except notion_api.NotionCredentialError as error:
            if str(error) != "notion_token_invalid":
                raise runtime.RuntimeSetupError(str(error)) from error
            CONSOLE.print(
                "[yellow]Notion rejected that integration token. Copy a current "
                "token from the Notion integration settings and try again.[/yellow]"
            )
            candidate = None
            continue
        if candidate != saved:
            runtime.save_profile_secret(profile_home, "NOTION_TOKEN", candidate)
        return


def _configure_webhook(profile_home: Path) -> None:
    CONSOLE.print(
        Panel.fit(
            "[bold]Real-time Notion comments[/bold]\n"
            "Before continuing, create a free ngrok account and copy:\n\n"
            "  [cyan]Your agent authtoken[/cyan]\n"
            "  [cyan]Your assigned HTTPS development domain[/cyan]\n\n"
            "Do not run the ngrok Docker command; this setup owns that container.\n"
            "Guide: [link=https://ngrok.com/docs/getting-started/]"
            "ngrok.com/docs/getting-started[/link]",
            border_style="cyan",
        )
    )
    _configure_notion_token(profile_home)
    saved_trigger = runtime.read_profile_secret(profile_home, "NOTION_COMMENT_TRIGGER")
    while True:
        trigger = _prompt_text(
            "Agent trigger keyword",
            default=saved_trigger or notion_api.DEFAULT_TRIGGER,
            console=CONSOLE,
        )
        if re.fullmatch(r"@[A-Za-z0-9_]{2,32}", trigger):
            runtime.save_profile_secret(profile_home, "NOTION_COMMENT_TRIGGER", trigger)
            break
        CONSOLE.print(
            "[yellow]Use one @keyword with letters, numbers, or underscores, "
            "for example @companyos.[/yellow]"
        )
    ngrok_authtoken = _prompt_secret("ngrok agent authtoken (hidden): ")
    while True:
        public_url = _prompt_text(
            "Assigned ngrok HTTPS domain",
            console=CONSOLE,
        )
        try:
            endpoint = runtime.normalize_webhook_url(public_url)
            runtime.begin_ngrok_update(profile_home)
            try:
                runtime.configure_notion_webhook(profile_home, endpoint)
                runtime.save_ngrok_config(profile_home, ngrok_authtoken, endpoint)
            except Exception:
                runtime.rollback_ngrok_update(profile_home)
                raise
            break
        except runtime.RuntimeSetupError as error:
            if not str(error).startswith("webhook_url_"):
                raise
            CONSOLE.print(
                "[yellow]Use the stable HTTPS development domain assigned to "
                "your ngrok account, with no path, query, or fragment, for example "
                "https://example-name.ngrok-free.app.[/yellow]"
            )


def _last_reply_time(profile_home: Path) -> float:
    try:
        state = json.loads(
            (profile_home / "state" / "notion-webhook.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return 0.0
    last = state.get("last_reply", {}) if isinstance(state, dict) else {}
    value = last.get("sent_at") if isinstance(last, dict) else None
    return float(value) if isinstance(value, (int, float)) else 0.0


def _wait_for_new_reply(profile_home: Path, after: float, timeout: int) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _last_reply_time(profile_home) > after:
            return True
        time.sleep(2)
    return False


def _wait_for_webhook_token(profile_home: Path, timeout: int) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        token = runtime.webhook_verification_token(profile_home)
        if token:
            return token
        time.sleep(2)
    return ""


def _guide_webhook_verification(profile_home: Path, timeout: int) -> bool:
    token = runtime.webhook_verification_token(profile_home)
    if token:
        return True
    endpoint = runtime.webhook_public_url(profile_home)
    CONSOLE.print(
        Panel.fit(
            "[bold]Verify the Notion webhook[/bold]\n"
            "In the same Notion internal connection, open [bold]Webhooks[/bold] "
            "and create a subscription:\n\n"
            f"  URL: [cyan]{endpoint or 'configured stable webhook URL'}[/cyan]\n"
            "  Event: [cyan]comment.created[/cyan]\n\n"
            "Enable Read content, Read comments, and Insert comments. Notion will send a "
            "one-time verification request; setup will detect it.",
            border_style="cyan",
        )
    )
    pause("Press Enter after creating the subscription")
    wait_seconds = min(timeout, 60)
    with CONSOLE.status(
        f"[cyan]Waiting for Notion verification request (up to {wait_seconds} seconds)…[/cyan]"
    ):
        token = _wait_for_webhook_token(profile_home, wait_seconds)
    if not token:
        CONSOLE.print(
            "[yellow]No verification request arrived. Check the ngrok container "
            "and rerun setup to retry.[/yellow]"
        )
        return False
    CONSOLE.print(
        Panel.fit(
            "[bold green]Verification request received[/bold green]\n"
            "Paste this one-time token into Notion and select Verify:\n\n"
            f"[cyan]{token}[/cyan]\n\n"
            "This token is shown only for the browser handshake and is not written "
            "to the setup receipt.",
            border_style="green",
        )
    )
    pause("Press Enter after Notion reports the subscription is verified")
    return True
