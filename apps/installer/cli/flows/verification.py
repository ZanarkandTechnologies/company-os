"""Static and live installation verification flow."""

from __future__ import annotations

import argparse
import sys

from rich.panel import Panel
from rich.table import Table

from apps.installer import runtime
from apps.installer.cli.flows.connections import certify_command
from apps.installer.cli.paths import profile_home as resolve_profile_home, receipt_reference
from apps.installer.cli.ui import CONSOLE, confirm, pause


def verify_command(args: argparse.Namespace) -> int:
    profile_home = resolve_profile_home(args.profile_home)
    if args.test_connections or (
        args.live
        and not args.skip_connections
        and sys.stdin.isatty()
        and confirm(
            "Retest configured integrations before health verification?",
            default=False,
        )
    ):
        connection_args = argparse.Namespace(
            profile_home=profile_home,
            allow_side_effects=args.allow_side_effects,
        )
        certify_command(connection_args)
    comment_after: float | None = None
    webhook_verified = True
    live_webhook = args.live and runtime.webhook_enabled(profile_home) and sys.stdin.isatty()
    if live_webhook:
        from plugins.platforms.notion.onboarding import (
            _guide_webhook_verification,
            _last_reply_time,
            _wait_for_new_reply,
        )

        webhook_verified = _guide_webhook_verification(profile_home, args.wait)
    if live_webhook and webhook_verified:
        trigger = runtime.read_profile_secret(
            profile_home,
            "NOTION_COMMENT_TRIGGER",
        ) or "@hermes"
        comment_after = _last_reply_time(profile_home)
        CONSOLE.print(
            Panel.fit(
                "[bold]Live Notion comment test[/bold]\n"
                f"On an isolated setup test ticket, add: [cyan]{trigger} setup healthcheck[/cyan]\n"
                "Setup will wait for one new threaded reply.",
                border_style="cyan",
            )
        )
        pause("Press Enter after posting the comment")
        with CONSOLE.status(
            f"[cyan]Waiting for one new threaded reply (up to {args.wait} seconds)…[/cyan]"
        ):
            _wait_for_new_reply(profile_home, comment_after, args.wait)

    receipt = runtime.verify_profile(
        profile_home,
        live=args.live,
        comment_after=comment_after,
    )
    table = Table(title="Installation verification")
    table.add_column("Lane")
    table.add_column("Result")
    table.add_column("Meaning")
    colors = {"pass": "green", "skip": "yellow", "fail": "red"}
    for lane in receipt["lanes"]:
        color_name = colors.get(str(lane["status"]), "white")
        table.add_row(
            str(lane["name"]),
            f"[{color_name}]{lane['status']}[/{color_name}]",
            str(lane["detail"]),
        )
    CONSOLE.print(table)
    receipt_path = runtime.write_receipt(profile_home, receipt)
    status = str(receipt["status"])
    color_name = {"ready": "green", "partial": "yellow", "blocked": "red"}.get(status, "white")
    CONSOLE.print(
        Panel.fit(
            f"[bold {color_name}]{status.upper()}[/bold {color_name}]\n"
            f"Support receipt: {receipt_reference(profile_home, receipt_path)}",
            border_style=color_name,
        )
    )
    return {"ready": 0, "partial": 1}.get(status, 2)
