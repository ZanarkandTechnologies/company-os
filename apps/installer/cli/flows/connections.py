"""Provider authorization and configured-integration certification flows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from apps.installer import provider_catalog as catalog_api
from apps.installer import runtime
from apps.installer.provider_catalog import CatalogError
from apps.installer.feature_setup import bindings_for_workspace
from apps.installer.cli.paths import profile_home as resolve_profile_home
from apps.installer.cli.process import run_mcp_test_visible, run_visible
from apps.installer.cli.ui import (
    CONSOLE,
    _prompt_secret,
    choose as choose_option,
    confirm,
    pause,
)


def _selected_bindings(workspace: Path) -> list[dict]:
    catalog = catalog_api.load_catalog()
    return bindings_for_workspace(workspace, catalog)


def _configure_connections(
    profile_home: Path,
    bindings: list[dict],
    *,
    non_interactive: bool,
) -> None:
    """Install and authorize each unique Hermes-owned MCP exactly once."""
    providers = [binding["provider"] for binding in bindings]
    catalog_unique: dict[str, dict] = {}
    for provider in providers:
        if provider["mcp"]["source"] == "hermes_catalog":
            catalog_unique[catalog_api.connection_key(provider)] = provider
    catalog_providers = list(catalog_unique.values())
    composio_providers = [
        provider
        for provider in providers
        if provider["mcp"]["source"] == "composio_session"
    ]
    for provider in catalog_providers:
        name = str(provider["mcp"]["name"])
        runtime.install_catalog_mcp(profile_home, name)
        if non_interactive:
            continue
        CONSOLE.print(
            Panel.fit(
                f"[bold]Connect {provider['label']}[/bold]\n"
                "Hermes owns this MCP connection, browser authorization, and tokens.",
                border_style="cyan",
            )
        )
        if confirm(
            f"Authorize {provider['label']} in your browser now?",
            default=True,
        ):
            if run_visible(["hermes", "mcp", "login", name], profile_home):
                raise runtime.RuntimeSetupError(f"mcp_authorization_incomplete:{name}")
            if run_mcp_test_visible(name, profile_home):
                raise runtime.RuntimeSetupError(f"mcp_connection_test_failed:{name}")
    if composio_providers:
        _configure_composio_connection(
            profile_home,
            composio_providers,
            non_interactive=non_interactive,
        )


def _configure_composio_connection(
    profile_home: Path,
    providers: list[dict],
    *,
    non_interactive: bool,
) -> None:
    """Provision one fixed-tool Composio session without installing its CLI."""
    from apps.installer import composio_session

    api_key = runtime.read_profile_secret(profile_home, "COMPOSIO_API_KEY")
    save_after_validation = False
    if not api_key:
        if non_interactive:
            raise runtime.RuntimeSetupError("composio_api_key_requires_input")
        api_key = _prompt_secret("Composio project API key (hidden): ")
        save_after_validation = True
    try:
        state = composio_session.ensure_session(profile_home, providers, api_key)
    except composio_session.ComposioSessionError as error:
        rejected_saved_key = (
            not save_after_validation
            and str(error) in {"composio_http_401", "composio_http_403"}
        )
        if non_interactive or not rejected_saved_key:
            raise runtime.RuntimeSetupError(str(error)) from error
        api_key = _prompt_secret("Replacement Composio project API key (hidden): ")
        save_after_validation = True
        try:
            state = composio_session.ensure_session(profile_home, providers, api_key)
        except composio_session.ComposioSessionError as replacement_error:
            raise runtime.RuntimeSetupError(
                str(replacement_error)
            ) from replacement_error

    if save_after_validation:
        runtime.save_profile_secret(profile_home, "COMPOSIO_API_KEY", api_key)
    try:
        runtime.configure_remote_mcp(
            profile_home,
            str(providers[0]["mcp"]["name"]),
            str(state["mcp_url"]),
            headers={"x-api-key": "${COMPOSIO_API_KEY}"},
        )
        if non_interactive:
            return
        connected = composio_session.connected_toolkits(state, api_key)
        labels = {"gmail": "Gmail", "googledrive": "Google Drive"}
        for toolkit in sorted(state["toolkits"]):
            if toolkit in connected:
                continue
            url = composio_session.create_connect_link(state, toolkit, api_key)
            label = labels.get(toolkit, toolkit)
            CONSOLE.print(
                Panel.fit(
                    f"[bold]Connect {label}[/bold]\n"
                    f"Open this secure Composio link and finish Google OAuth:\n"
                    f"[link={url}]{url}[/link]\n\n"
                    "Composio stores and refreshes the Google credential; Hermes "
                    "stores only this profile's restricted MCP session.",
                    border_style="cyan",
                )
            )
            pause(f"Press Enter after {label} is connected")
        connected = composio_session.connected_toolkits(state, api_key)
        missing = sorted(set(state["toolkits"]) - connected)
        if missing:
            raise runtime.RuntimeSetupError(
                "composio_connections_incomplete:" + ",".join(missing)
            )
        if run_mcp_test_visible(str(providers[0]["mcp"]["name"]), profile_home):
            raise runtime.RuntimeSetupError("composio_mcp_connection_test_failed")
    except composio_session.ComposioSessionError as error:
        raise runtime.RuntimeSetupError(str(error)) from error


def _connection_eval_confirmation(bindings: list[dict]) -> bool:
    risky = [
        binding
        for binding in bindings
        if binding["provider"]["test"]["requires_confirmation"]
    ]
    if risky:
        rows = "\n".join(
            f"  • {binding['case_id']} ({binding['provider']['test']['risk']})"
            for binding in risky
        )
        CONSOLE.print(
            Panel.fit(
                "[bold]Test configured integrations[/bold]\n"
                "Hermes will run the configured checks concurrently. Listed tests "
                "may create external records; reversible tests clean up their test "
                "records, while irreversible tests leave their declared result:\n\n"
                f"[cyan]{rows}[/cyan]\n\n"
                "No existing provider record should be changed.",
                border_style="yellow",
            )
        )
    return confirm("Run configured integration tests now?", default=True)


def _run_connection_evals(
    profile_home: Path,
    workspace: Path,
    *,
    allow_side_effects: bool,
) -> dict:
    from apps.installer import connection_evals as run_connection_evals

    with CONSOLE.status("[cyan]Testing configured integrations…[/cyan]"):
        receipt = run_connection_evals.run_connection_evals(
            profile_home,
            workspace,
            allow_side_effects=allow_side_effects,
        )
        run_connection_evals.write_receipt(profile_home, receipt)
    return receipt


def _render_connection_eval(receipt: dict) -> None:
    table = Table(title="Configured integration tests")
    table.add_column("Data source")
    table.add_column("Provider")
    table.add_column("Result")
    judged = {
        row["case_id"]: row
        for row in (receipt.get("judgment") or {}).get("cases", [])
        if isinstance(row, dict)
    }
    for case in receipt.get("cases", []):
        verdict = judged.get(case["case_id"], {})
        status = verdict.get("status", "failed")
        color = "green" if status == "passed" else "red"
        reason = str(verdict.get("reason") or case.get("error") or "")
        table.add_row(
            str(case["data_source"]),
            str(case["provider"]),
            f"[{color}]{status}[/{color}]" + (f" — {reason}" if reason else ""),
        )
    for case in receipt.get("blocked", []):
        table.add_row(
            str(case["data_source"]),
            str(case["provider"]),
            "[yellow]human required[/yellow]",
        )
    CONSOLE.print(table)
    status = str(receipt.get("status", "failed"))
    color = {"passed": "green", "human_required": "yellow"}.get(status, "red")
    CONSOLE.print(f"[{color}]Integration certification: {status}[/{color}]")


def _defer_connection_evals(
    profile_home: Path,
    workspace: Path,
    *,
    previous: dict | None = None,
) -> dict:
    from apps.installer import connection_evals as run_connection_evals

    return run_connection_evals.defer_connection_evals(
        profile_home,
        workspace,
        previous=previous,
    )


def _certify_with_recovery(
    profile_home: Path,
    workspace: Path,
    *,
    allow_side_effects: bool,
    interactive: bool,
) -> dict:
    """Retry failed certification in place or record an explicit defer choice."""
    from apps.installer import connection_evals as run_connection_evals

    deferred = False

    def choose_action() -> str:
        return choose_option(
            "Certification did not pass. Retry now or defer until later?",
            choices=["retry", "defer"],
            default="retry",
        )

    def defer(receipt: dict) -> dict:
        nonlocal deferred
        deferred = True
        return _defer_connection_evals(profile_home, workspace, previous=receipt)

    receipt = run_connection_evals.resolve_certification(
        lambda: _run_connection_evals(
            profile_home,
            workspace,
            allow_side_effects=allow_side_effects,
        ),
        _render_connection_eval,
        choose_action,
        defer,
        interactive=interactive,
    )
    if deferred:
        CONSOLE.print(
            "[yellow]Certification deferred. Setup is preserved; choose Test "
            "integrations from setup.cmd when you are ready.[/yellow]"
        )
    return receipt


def certify_command(args: argparse.Namespace) -> int:
    """Run configured provider evals and render one consolidated verdict."""
    profile_home = resolve_profile_home(args.profile_home)
    workspace = profile_home / "workspace.hermes.md"
    try:
        bindings = _selected_bindings(workspace)
        if not bindings:
            CONSOLE.print("[yellow]No configured catalog providers to test.[/yellow]")
            return 0
        allow_side_effects = bool(args.allow_side_effects)
        if sys.stdin.isatty() and not allow_side_effects:
            allow_side_effects = _connection_eval_confirmation(bindings)
            if not allow_side_effects:
                _defer_connection_evals(profile_home, workspace)
                CONSOLE.print("[yellow]Integration certification deferred.[/yellow]")
                return 1
        receipt = _certify_with_recovery(
            profile_home,
            workspace,
            allow_side_effects=allow_side_effects,
            interactive=sys.stdin.isatty(),
        )
        return {"passed": 0, "deferred": 1, "human_required": 1}.get(
            str(receipt["status"]), 2
        )
    except (runtime.RuntimeSetupError, CatalogError) as error:
        CONSOLE.print(
            Panel.fit(
                "[bold red]Integration certification failed[/bold red]\n"
                f"{error}",
                border_style="red",
            )
        )
        return 2
