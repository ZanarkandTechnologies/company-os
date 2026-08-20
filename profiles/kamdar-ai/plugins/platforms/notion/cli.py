"""Operator commands for the Notion webhook handshake state."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .protocol import WebhookState


def _state() -> WebhookState:
    home = Path(os.getenv("HERMES_HOME") or Path.home() / ".hermes")
    return WebhookState(home / "state" / "notion-webhook.json")


def setup_cli(parser: argparse.ArgumentParser) -> None:
    commands = parser.add_subparsers(dest="notion_webhook_command", required=True)
    commands.add_parser("status", help="Show endpoint and whether the verification token was captured")
    commands.add_parser("token", help="Print the captured verification token for pasting into Notion")
    commands.add_parser("reset-token", help="Remove the captured token and delivery history before re-verification")


def run_cli(args: argparse.Namespace) -> int:
    command = args.notion_webhook_command
    state = _state()
    data = state.load()
    if command == "status":
        endpoint = (os.getenv("NOTION_WEBHOOK_PUBLIC_URL") or "not configured").strip()
        print(f"endpoint: {endpoint}")
        print(f"verification_token_captured: {'yes' if data['verification_token'] else 'no'}")
        print(f"workspace_id: {data['workspace_id'] or 'not captured'}")
        print(f"remembered_event_ids: {len(data['seen'])}")
        print(f"remembered_reply_targets: {len(data['reply_targets'])}")
        print(f"reply_observed: {'yes' if data['last_reply'].get('message_id') else 'no'}")
        return 0
    if command == "token":
        if not data["verification_token"]:
            print("No verification token has been captured.")
            return 1
        print(data["verification_token"])
        return 0
    if command == "reset-token":
        state.save({"verification_token": "", "workspace_id": "", "seen": {}, "reply_targets": {}, "last_reply": {}})
        print("Notion webhook verification state reset.")
        return 0
    return 2
