"""Hermes-owned messaging connection and explicit test flow."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from apps.installer.schemas.workspace import (
    CommunicationBinding,
    DeliveryBehavior,
    MANAGED_COMMUNICATIONS,
    MessagingTestReceipt,
    configuration_hash,
    render_workspace_communications,
)
from apps.installer import runtime
from apps.installer.cli.process import run_visible


@dataclass(frozen=True)
class MessagingSetupResult:
    status: str
    bindings: list[CommunicationBinding]
    apply: bool


def _json_result(stdout: str) -> dict:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = None
        for line in reversed(stdout.splitlines()):
            try:
                payload = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    return payload if isinstance(payload, dict) else {}


def send_connection_test(
    profile_home: Path,
    binding: CommunicationBinding,
    bindings: list[CommunicationBinding],
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = runtime.run_command,
) -> tuple[MessagingTestReceipt, bool]:
    """Send exactly one bounded message; caller records recipient confirmation."""
    message = (
        f"Hermes connection test for {binding.send_to}. "
        "This test does not enable employee messages or automatic sending."
    )
    result = command_runner(
        ["hermes", "send", "--to", binding.app.value, "--json", message],
        profile_home,
        check=False,
    )
    payload = _json_result(result.stdout)
    provider_success = result.returncode == 0 and payload.get("success") is True
    chat_id = str(payload.get("chat_id") or "").strip()
    exact_target = f"{binding.app.value}:{chat_id}" if chat_id else None
    receipt = MessagingTestReceipt(
        configuration_sha256=configuration_hash(bindings),
        app=binding.app,
        recipient_sha256=hashlib.sha256(binding.send_to.casefold().encode()).hexdigest(),
        status="failed",
        recipient_confirmed=False,
        exact_target=exact_target,
        target_sha256=(
            hashlib.sha256(exact_target.encode()).hexdigest() if exact_target else None
        ),
        message_id=(
            str(payload["message_id"])
            if provider_success and payload.get("message_id") is not None
            else None
        ),
    )
    return receipt, provider_success


def _save_bindings(workspace: Path, bindings: list[CommunicationBinding]) -> None:
    content = workspace.read_text(encoding="utf-8")
    table = render_workspace_communications(bindings)
    updated = MANAGED_COMMUNICATIONS.sub(
        "<!-- hermes:managed communications -->\n"
        + table
        + "\n<!-- /hermes:managed communications -->",
        content,
        count=1,
    )
    descriptor, temporary = tempfile.mkstemp(prefix=".messaging-choice-", dir=workspace.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.replace(temporary, workspace)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _review(bindings: list[CommunicationBinding], status: str, message_id: str | None) -> None:
    from rich.table import Table
    from apps.installer.cli.ui import CONSOLE

    table = Table(title="Review messaging setup")
    table.add_column("Message")
    table.add_column("App")
    table.add_column("Recipient")
    table.add_column("Behavior")
    for binding in bindings:
        behavior = (
            "Drafts in private workspace"
            if binding.behavior is DeliveryBehavior.PREPARE_DRAFTS
            else "Send automatically"
        )
        table.add_row(
            binding.message.value,
            binding.app.value.title(),
            binding.send_to,
            behavior,
        )
    table.add_row("Employee follow-up", "—", "—", "Not enabled")
    CONSOLE.print(table)
    CONSOLE.print(f"Connection test: {status.replace('_', ' ').title()}")
    if message_id:
        CONSOLE.print(f"Message ID: {message_id}")


def configure_messaging(
    profile_home: Path,
    bindings: list[CommunicationBinding],
    *,
    workspace: Path,
    non_interactive: bool,
) -> MessagingSetupResult:
    """Use Hermes setup, test one exact route, then review before apply."""
    from rich.panel import Panel
    from apps.installer.cli.ui import CONSOLE, choose, confirm

    owner_bindings = [
        binding for binding in bindings if binding.recipient_rule.value == "named owner"
    ]
    if not owner_bindings:
        return MessagingSetupResult("not_configured", bindings, True)
    binding = owner_bindings[0]
    if non_interactive:
        return MessagingSetupResult("deferred", bindings, True)

    receipt: MessagingTestReceipt | None = None
    status = "passed" if runtime.messaging_test_current(profile_home, bindings) else "deferred"
    if status != "passed":
        CONSOLE.print(
            Panel.fit(
                f"[bold]Connect {binding.app.value.title()}[/bold]\n"
                "Setup will open Hermes' secure messaging configuration. "
                "Passwords and tokens are not saved in this workspace.",
                border_style="cyan",
            )
        )
        if confirm("Open Hermes messaging setup?", default=True):
            if run_visible(["hermes", "gateway", "setup"], profile_home):
                CONSOLE.print(
                    "[yellow]Hermes messaging setup did not finish. "
                    "Draft preparation remains available.[/yellow]"
                )

        while True:
            CONSOLE.print(
                Panel.fit(
                    "[bold]Check the connection[/bold]\n"
                    f"Send one test message to {binding.send_to} on "
                    f"{binding.app.value.title()}?\n"
                    "This only checks this owner route. It will not contact employees "
                    "or enable automatic messages.",
                    border_style="cyan",
                )
            )
            if not confirm("Send one test message?", default=False):
                status = "skipped"
            else:
                receipt, provider_success = send_connection_test(
                    profile_home, binding, bindings
                )
                recipient_confirmed = (
                    provider_success
                    and bool(receipt.exact_target)
                    and confirm(
                        f"Did {binding.send_to} receive the test message?",
                        default=False,
                    )
                )
                receipt = receipt.model_copy(
                    update={
                        "recipient_confirmed": recipient_confirmed,
                        "status": "passed" if recipient_confirmed else "failed",
                    }
                )
                runtime.write_messaging_test_receipt(
                    profile_home, receipt.model_dump(mode="json")
                )
                status = receipt.status
            if status == "passed" or not requires_confirmed_test(bindings):
                break
            recovery = choose(
                "The route is not confirmed [retry = Try again; drafts = Save as drafts only]",
                choices=["retry", "drafts"],
                default="drafts",
            )
            if recovery == "retry":
                continue
            bindings = [
                item.model_copy(
                    update={"behavior": DeliveryBehavior.PREPARE_DRAFTS}
                )
                for item in bindings
            ]
            _save_bindings(workspace, bindings)
            status = "drafts_only"
            break

    _review(bindings, status, receipt.message_id if receipt else None)
    apply = confirm("Apply this messaging setup?", default=True)
    if not apply:
        CONSOLE.print(
            "[yellow]Messaging was not installed. The reviewed workspace choices remain saved.[/yellow]"
        )
    return MessagingSetupResult(status, bindings, apply)


def requires_confirmed_test(bindings: list[CommunicationBinding]) -> bool:
    return any(
        binding.behavior is DeliveryBehavior.SEND_AUTOMATICALLY
        for binding in bindings
    )
