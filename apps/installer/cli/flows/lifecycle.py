"""Install, resume, update, and maintenance-menu lifecycle flows."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from apps.installer import provider_catalog as catalog_api
from apps.installer import runtime
from apps.installer.feature_setup import FeatureSetupError, load_state, render_files, selected_bindings, with_optional_defaults
from apps.installer.provider_catalog import CatalogError
from apps.installer.cli.flows.connections import (
    _certify_with_recovery,
    _configure_connections,
    _connection_eval_confirmation,
    _defer_connection_evals,
)
from apps.installer.cli.flows.features import configure_features
from apps.installer.cli.paths import ROOT, profile_home as resolve_profile_home, receipt_reference
from apps.installer.cli.process import run_visible
from apps.installer.cli.ui import CONSOLE, _friendly_runtime_error, choose, confirm


LAUNCH_FULL_VERIFY = 10
LAUNCH_STATIC_VERIFY = 11
LAUNCH_LIVE_HEALTH = 12
LAUNCH_DASHBOARD = 13
LAUNCH_CERTIFY = 14
LAUNCH_PREFLIGHT = 15
LAUNCH_EVAL = 16
LAUNCH_DOSSIER = 17
FRESH_START_MARKER = ".company-os-fresh-start"
DISTRIBUTION_SOURCE_ENV = "COMPANY_OS_DISTRIBUTION_SOURCE"


def _run_profile_setup(
    profile_home: Path,
    *,
    webhook: bool,
    multica: bool,
    apply: bool,
) -> dict:
    source_root = (
        profile_home
        if (profile_home / "distribution.yaml").is_file()
        else ROOT
    )
    script = source_root / "apps" / "installer" / "profile.py"
    arguments = [sys.executable, str(script), "--profile-home", str(profile_home)]
    if apply:
        arguments.append("--apply")
    if webhook:
        arguments.append("--enable-notion-webhook")
    if multica:
        arguments.append("--enable-multica")
    result = runtime.run_command(arguments, profile_home)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise runtime.RuntimeSetupError("profile_setup_receipt_unreadable") from error
    if not isinstance(payload, dict):
        raise runtime.RuntimeSetupError("profile_setup_receipt_invalid")
    return payload


def _installation_state(profile_home: Path) -> str:
    """Classify only the lifecycle state needed to choose the next UX."""
    if (profile_home / FRESH_START_MARKER).is_file():
        return "new"
    if not (profile_home / "distribution.yaml").is_file():
        return "new"
    required = (
        profile_home / "workspace.hermes.md",
        profile_home / "workspace" / ".hermes.md",
        profile_home / "cron" / "jobs.json",
    )
    if any(not path.is_file() for path in required):
        return "incomplete"
    if not runtime.model_auth_configured(profile_home):
        return "incomplete"
    try:
        jobs_payload = json.loads(
            (profile_home / "cron" / "jobs.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return "incomplete"
    jobs = jobs_payload.get("jobs", []) if isinstance(jobs_payload, dict) else []
    active_names = {
        str(job.get("name"))
        for job in jobs
        if isinstance(job, dict) and job.get("enabled", True) is not False
    }
    # A previously complete two-job profile must reach the update menu instead
    # of being mislabeled as an interrupted install. Full verification still
    # requires every current schedule in runtime.EXPECTED_CRON_NAMES.
    if not runtime.CORE_CRON_NAMES.issubset(active_names):
        return "incomplete"
    return "existing"


def _fresh_start(profile_home: Path) -> int:
    """Archive the incomplete profile and relaunch from a clean installed copy."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = profile_home.with_name(f"{profile_home.name}.incomplete-{timestamp}")
    suffix = 1
    while backup.exists():
        backup = profile_home.with_name(
            f"{profile_home.name}.incomplete-{timestamp}-{suffix}"
        )
        suffix += 1

    profile_home.rename(backup)
    try:
        source = Path(os.environ.get(DISTRIBUTION_SOURCE_ENV, str(backup)))
        runtime.install_or_update_distribution(source, profile_home)
        (profile_home / "workspace.hermes.md").unlink(missing_ok=True)
        (profile_home / FRESH_START_MARKER).write_text(
            f"backup={backup}\n", encoding="utf-8"
        )
    except Exception:
        if profile_home.exists():
            shutil.rmtree(profile_home, ignore_errors=True)
        backup.rename(profile_home)
        raise

    CONSOLE.print(
        Panel.fit(
            "[bold green]Fresh setup ready[/bold green]\n"
            f"The incomplete profile was preserved at:\n{backup}\n"
            "Starting the workspace questions again.",
            border_style="green",
        )
    )
    installed_setup = profile_home / "setup.py"
    environment = runtime.profile_environment(profile_home)
    environment[DISTRIBUTION_SOURCE_ENV] = str(source.resolve())
    return subprocess.run(
        [
            sys.executable,
            str(installed_setup),
            "launch",
            "--profile-home",
            str(profile_home),
            "--installed",
        ],
        check=False,
        env=environment,
    ).returncode


def _workspace_update(profile_home: Path) -> int:
    """Edit feature answers, render automations, and apply the installed copy."""
    workspace = profile_home / "workspace.hermes.md"
    CONSOLE.print(
        Panel.fit(
            "[bold]Update Company OS features[/bold]\n"
            "Current answers are preserved as defaults. Setup will preview the "
            "rendered automation changes before writing them.",
            border_style="cyan",
        )
    )
    try:
        if configure_features(profile_home):
            CONSOLE.print("[yellow]Feature configuration was not changed.[/yellow]")
            return 1
        state = load_state(profile_home / "config" / "setup-answers.json")
        bindings = selected_bindings(
            state.answers,
            catalog_api.load_catalog(),
            state.provider_requirements,
            state.provider_targets,
        )
        _configure_connections(profile_home, bindings, non_interactive=False)
        _configure_telegram_if_needed(
            profile_home,
            state.provider_requirements,
            non_interactive=False,
        )
        _configure_whatsapp_if_needed(
            profile_home,
            state.provider_requirements,
            non_interactive=False,
        )
        _configure_messaging_tools_if_needed(
            profile_home, state.provider_requirements
        )
        runtime.approve_workspace_context(workspace)
        receipt = _run_profile_setup(
            profile_home,
            webhook=runtime.webhook_enabled(profile_home),
            multica="multica" in {
                provider for values in state.provider_requirements.values() for provider in values
            },
            apply=True,
        )
        receipt["entry_point"] = "setup.py workspace"
        receipt_path = runtime.write_receipt(profile_home, receipt)
        CONSOLE.print(
            Panel.fit(
                "[bold green]Feature configuration applied[/bold green]\n"
                "Required provider connections were reconciled.\n"
                f"Support receipt: {receipt_reference(profile_home, receipt_path)}",
                border_style="green",
            )
        )
        return 0
    except (runtime.RuntimeSetupError, FeatureSetupError, CatalogError) as error:
        CONSOLE.print(
            Panel.fit(
                "[bold red]Workspace update stopped safely[/bold red]\n"
                + _friendly_runtime_error(error),
                border_style="red",
            )
        )
        return 2


def launch_command(args: argparse.Namespace) -> int:
    """Own the customer interaction and request one bounded launcher follow-up."""
    profile_home = resolve_profile_home(args.profile_home)
    state = _installation_state(profile_home)
    if state == "new":
        CONSOLE.print(
            Panel.fit(
                "[bold]Welcome to the Company OS[/bold]\n"
                "New installation detected. Setup will create a private persistent "
                "profile and guide the required authorization.\n"
                "You do not need Python, WSL commands, or configuration files.",
                border_style="cyan",
            )
        )
        return LAUNCH_FULL_VERIFY if install_command(args) == 0 else 2

    if state == "incomplete":
        CONSOLE.print(
            Panel.fit(
                "[bold]Resume Company OS setup[/bold]\n"
                "An incomplete installation was found. Existing workspace choices "
                "and saved credentials are safe. Setup will reconcile missing steps.",
                border_style="yellow",
            )
        )
        action = choose(
            "Incomplete setup",
            choices=["resume", "start-over", "exit"],
            default="resume",
        )
        if action == "start-over":
            if not confirm(
                "Start over and preserve the current incomplete profile as a backup?",
                default=False,
            ):
                CONSOLE.print("[yellow]No setup changes were made.[/yellow]")
                return 0
            return _fresh_start(profile_home)
        if action == "exit":
            CONSOLE.print("[yellow]No setup changes were made.[/yellow]")
            return 0
        return LAUNCH_FULL_VERIFY if install_command(args) == 0 else 2

    CONSOLE.print(
        Panel.fit(
            "[bold]Company OS[/bold]\nExisting installation found.",
            border_style="cyan",
        )
    )
    CONSOLE.print("  [cyan]1.[/cyan] Update Company OS features")
    CONSOLE.print("  [cyan]2.[/cyan] Update Company OS software")
    CONSOLE.print("  [cyan]3.[/cyan] Test integrations")
    CONSOLE.print("  [cyan]4.[/cyan] Check data readiness")
    CONSOLE.print("  [cyan]5.[/cyan] Run full eval and open dossier")
    CONSOLE.print("  [cyan]6.[/cyan] Run full health check")
    CONSOLE.print("  [cyan]7.[/cyan] Repair setup")
    CONSOLE.print("  [cyan]8.[/cyan] Open latest eval dossier")
    CONSOLE.print("  [cyan]9.[/cyan] Open dashboard")
    CONSOLE.print("  [cyan]10.[/cyan] Exit")
    choice = choose(
        "Select",
        choices=[str(index) for index in range(1, 11)],
        default="1",
    )
    if choice == "1":
        result = _workspace_update(profile_home)
        if result == 0:
            return LAUNCH_STATIC_VERIFY
        return 0 if result == 1 else 2
    if choice == "2":
        return LAUNCH_STATIC_VERIFY if update_command(args) == 0 else 2
    if choice == "3":
        return LAUNCH_CERTIFY
    if choice == "4":
        return LAUNCH_PREFLIGHT
    if choice == "5":
        return LAUNCH_EVAL
    if choice == "6":
        return LAUNCH_LIVE_HEALTH
    if choice == "7":
        if runtime.webhook_enabled(profile_home) and confirm(
            "Revalidate or replace the saved Notion/ngrok webhook credentials?",
            default=False,
        ):
            from plugins.platforms.notion.onboarding import _configure_webhook

            _configure_webhook(profile_home)
        return LAUNCH_FULL_VERIFY if install_command(args) == 0 else 2
    if choice == "8":
        return LAUNCH_DOSSIER
    if choice == "9":
        return LAUNCH_DASHBOARD
    CONSOLE.print("[dim]No changes made.[/dim]")
    return 0


def _bootstrap_installed_copy(
    profile_home: Path,
    command: str,
    *,
    non_interactive: bool = False,
) -> int | None:
    if ROOT.resolve() == profile_home.resolve():
        return None
    action = runtime.install_or_update_distribution(ROOT, profile_home)
    installed_setup = profile_home / "setup.py"
    if not installed_setup.is_file():
        raise runtime.RuntimeSetupError("installed_setup_missing")
    CONSOLE.print(f"[green]Distribution {action}.[/green] Continuing from the persistent profile…")
    arguments = [
        sys.executable,
        str(installed_setup),
        command,
        "--profile-home",
        str(profile_home),
        "--installed",
    ]
    if non_interactive:
        arguments.append("--non-interactive")
    environment = runtime.profile_environment(profile_home)
    environment[DISTRIBUTION_SOURCE_ENV] = str(ROOT.resolve())
    return subprocess.run(
        arguments,
        check=False,
        env=environment,
    ).returncode


def _prepare_workspace_configuration(*, non_interactive: bool) -> Path:
    """Collect feature answers and render self-contained automation contracts."""
    workspace = ROOT / "workspace.hermes.md"
    answers = ROOT / "config" / "setup-answers.json"
    if non_interactive and not answers.is_file():
        raise runtime.RuntimeSetupError("workspace_configuration_requires_input")
    should_configure = not answers.is_file()
    if answers.is_file() and not non_interactive:
        should_configure = confirm(
            "Review or change the existing Company OS feature setup?",
            default=False,
        )
    if should_configure and configure_features(ROOT):
        raise runtime.RuntimeSetupError("workspace_configuration_cancelled")
    if not should_configure:
        saved = with_optional_defaults(load_state(answers).answers)
        render_files(
            tuple(
                ROOT / "automations" / name
                for name in (
                    "daily-operating-update.md",
                    "weekly-operating-review.md",
                    "weekly-meeting-ticket.md",
                )
            ),
            saved,
        )
    return workspace


def _choose_webhook(
    profile_home: Path,
    *,
    notion_selected: bool,
    non_interactive: bool,
) -> bool:
    """Return the existing or explicitly selected comment-webhook state."""
    enabled = runtime.webhook_enabled(profile_home)
    if enabled or not notion_selected or non_interactive:
        return enabled
    CONSOLE.print(
        Panel.fit(
            "[bold]Real-time Notion comments[/bold]\n"
            "Optional: enable @hermes comments with a dedicated Notion connection "
            "and your ngrok account's stable HTTPS development domain.",
            border_style="cyan",
        )
    )
    return confirm("Enable real-time Notion comments?", default=False)


def _confirm_install_plan(
    profile_home: Path,
    *,
    bindings: list[dict],
    webhook: bool,
    non_interactive: bool,
) -> bool:
    """Show every planned owner surface before setup performs writes."""
    review = Table(title="Review setup plan")
    review.add_column("Surface")
    review.add_column("Planned state")
    review.add_row(
        "Runtime",
        "Host Hermes with Docker terminal backend",
    )
    review.add_row("Profile", str(profile_home))
    review.add_row("Storage", "Persistent Hermes profile")
    connections = sorted(
        {catalog_api.connection_key(binding["provider"]) for binding in bindings}
    )
    review.add_row("Provider MCPs", ", ".join(connections) if connections else "None")
    review.add_row("Behavior", "Rendered directly into Daily, Weekly, and meeting-ticket automations")
    review.add_row("Real-time comments", "Configure" if webhook else "Set up later")
    review.add_row("Automations", "Daily + Weekly + weekly meeting ticket")
    review.add_row("Report template", "Reviewed repository template")
    review.add_row("Deletion", "Nothing")
    CONSOLE.print(review)
    if non_interactive:
        return True
    return confirm("Apply this setup plan?", default=True)


def _configure_model(profile_home: Path, *, non_interactive: bool) -> None:
    """Run Hermes' own model authorization without handling credentials here."""
    CONSOLE.print(
        Panel.fit(
            "[bold]AI model[/bold]\n"
            "Hermes owns the model credential and stores it in this profile.",
            border_style="cyan",
        )
    )
    if runtime.model_auth_configured(profile_home):
        return
    if non_interactive:
        raise runtime.RuntimeSetupError("model_auth_requires_input")
    CONSOLE.print("[dim]Opening Hermes' model provider chooser inside this setup…[/dim]")
    result = run_visible(["hermes", "setup", "model"], profile_home)
    if result or not runtime.model_auth_configured(profile_home):
        raise runtime.RuntimeSetupError("model_auth_incomplete")


def _configure_telegram_if_needed(
    profile_home: Path,
    provider_requirements: dict[str, tuple[str, ...]],
    *,
    non_interactive: bool,
) -> None:
    required = {provider for values in provider_requirements.values() for provider in values}
    if "telegram" not in required:
        return
    if runtime.telegram_gateway_configured(profile_home):
        return
    if non_interactive:
        raise runtime.RuntimeSetupError("telegram_gateway_requires_input")
    CONSOLE.print(
        Panel.fit(
            "[bold]Connect Telegram[/bold]\n"
            "The selected automation behavior requires Hermes messaging. "
            "Credentials remain in the Hermes profile.",
            border_style="cyan",
        )
    )
    if run_visible(["hermes", "gateway", "setup"], profile_home):
        raise runtime.RuntimeSetupError("telegram_gateway_setup_incomplete")
    if not runtime.telegram_gateway_configured(profile_home):
        raise runtime.RuntimeSetupError("telegram_gateway_setup_incomplete")


def _configure_whatsapp_if_needed(
    profile_home: Path,
    provider_requirements: dict[str, tuple[str, ...]],
    *,
    non_interactive: bool,
) -> None:
    required = {provider for values in provider_requirements.values() for provider in values}
    if "whatsapp" not in required or runtime.whatsapp_gateway_configured(profile_home):
        return
    if non_interactive:
        raise runtime.RuntimeSetupError("whatsapp_gateway_requires_input")
    CONSOLE.print(Panel.fit(
        "[bold]Connect WhatsApp[/bold]\n"
        "The selected automation behavior requires Hermes messaging. "
        "Pairing data remains in the Hermes profile.",
        border_style="cyan",
    ))
    if run_visible(["hermes", "whatsapp"], profile_home):
        raise runtime.RuntimeSetupError("whatsapp_gateway_setup_incomplete")
    if not runtime.whatsapp_gateway_configured(profile_home):
        raise runtime.RuntimeSetupError("whatsapp_gateway_setup_incomplete")


def _configure_messaging_tools_if_needed(
    profile_home: Path,
    provider_requirements: dict[str, tuple[str, ...]],
) -> None:
    required = {provider for values in provider_requirements.values() for provider in values}
    if {"telegram", "whatsapp"} & required:
        runtime.configure_messaging_mcp(profile_home)


def _install_profile(
    profile_home: Path,
    *,
    bindings: list[dict],
    webhook: bool,
    multica: bool,
) -> Path:
    """Apply the reviewed profile plan and write its redacted receipt."""
    CONSOLE.rule("[bold cyan]Install[/bold cyan]")
    CONSOLE.print("[cyan]•[/cyan] Installing workspace, plugins, and schedules…")
    receipt = _run_profile_setup(
        profile_home, webhook=webhook, multica=multica, apply=True
    )
    receipt.update(
        {
            "entry_point": "setup.py install",
            "provider_connections": sorted(
                {catalog_api.connection_key(binding["provider"]) for binding in bindings}
            ),
            "notion_webhook_configured": webhook,
        }
    )
    return runtime.write_receipt(profile_home, receipt)


def install_command(args: argparse.Namespace) -> int:
    profile_home = resolve_profile_home(args.profile_home)
    try:
        if not args.installed:
            delegated = _bootstrap_installed_copy(
                profile_home,
                "install",
                non_interactive=args.non_interactive,
            )
            if delegated is not None:
                return delegated
        profile_home.mkdir(parents=True, exist_ok=True)
        workspace_config = _prepare_workspace_configuration(
            non_interactive=args.non_interactive
        )
        state = load_state(ROOT / "config" / "setup-answers.json")
        required_providers = {
            provider for values in state.provider_requirements.values() for provider in values
        }
        bindings = selected_bindings(
            state.answers,
            catalog_api.load_catalog(),
            state.provider_requirements,
            state.provider_targets,
        )
        notion_selected = any(
            binding["provider"]["id"] == "notion" for binding in bindings
        )
        webhook = _choose_webhook(
            profile_home,
            notion_selected=notion_selected,
            non_interactive=args.non_interactive,
        )
        if not _confirm_install_plan(
            profile_home,
            bindings=bindings,
            webhook=webhook,
            non_interactive=args.non_interactive,
        ):
            CONSOLE.print(
                "[yellow]No runtime services or credentials changed. "
                "The saved workspace draft is preserved.[/yellow]"
            )
            return 1

        _configure_model(profile_home, non_interactive=args.non_interactive)
        _configure_connections(
            profile_home,
            bindings,
            non_interactive=args.non_interactive,
        )
        _configure_telegram_if_needed(
            profile_home,
            state.provider_requirements,
            non_interactive=args.non_interactive,
        )
        _configure_whatsapp_if_needed(
            profile_home,
            state.provider_requirements,
            non_interactive=args.non_interactive,
        )
        _configure_messaging_tools_if_needed(
            profile_home, state.provider_requirements
        )
        if webhook and not runtime.webhook_enabled(profile_home):
            from plugins.platforms.notion.onboarding import _configure_webhook

            _configure_webhook(profile_home)

        runtime.approve_workspace_context(workspace_config)

        receipt_path = _install_profile(
            profile_home,
            bindings=bindings,
            webhook=webhook,
            multica="multica" in required_providers,
        )
        (profile_home / FRESH_START_MARKER).unlink(missing_ok=True)
        connection_status = "not_run"
        if bindings and not args.non_interactive:
            if _connection_eval_confirmation(bindings):
                connection_receipt = _certify_with_recovery(
                    profile_home,
                    workspace_config,
                    allow_side_effects=True,
                    interactive=True,
                )
            else:
                connection_receipt = _defer_connection_evals(
                    profile_home,
                    workspace_config,
                )
            connection_status = str(connection_receipt["status"])
        CONSOLE.print(
            Panel.fit(
                (
                    "[bold green]Configuration installed[/bold green]\n"
                    if connection_status in {"not_run", "passed"}
                    else "[bold yellow]Configuration saved; integration proof is incomplete[/bold yellow]\n"
                )
                + f"Support receipt: {receipt_reference(profile_home, receipt_path)}\n"
                f"Integration certification: {connection_status}\n"
                + (
                    "The launcher will now start Hermes and run verification."
                    if connection_status in {"not_run", "passed"}
                    else "Rerun setup and choose Test integrations before continuing."
                ),
                border_style=(
                    "green" if connection_status in {"not_run", "passed"} else "yellow"
                ),
            )
        )
        return 0 if connection_status in {"not_run", "passed"} else 2
    except (runtime.RuntimeSetupError, FeatureSetupError, CatalogError) as error:
        CONSOLE.print(
            Panel.fit(
                "[bold red]Setup stopped safely[/bold red]\n"
                + _friendly_runtime_error(error),
                border_style="red",
            )
        )
        return 2


def update_command(args: argparse.Namespace) -> int:
    profile_home = resolve_profile_home(args.profile_home)
    try:
        answers_path = profile_home / "config" / "setup-answers.json"
        if (
            ROOT.resolve() != profile_home.resolve()
            and (profile_home / "distribution.yaml").is_file()
            and not answers_path.is_file()
        ):
            raise runtime.RuntimeSetupError("feature_setup_migration_required")
        if ROOT.resolve() != profile_home.resolve():
            runtime.install_or_update_distribution(ROOT, profile_home)
        multica = False
        if answers_path.is_file():
            state = load_state(answers_path)
            saved = with_optional_defaults(state.answers)
            multica = "multica" in {
                provider
                for values in state.provider_requirements.values()
                for provider in values
            }
            render_files(
                tuple(
                    profile_home / "automations" / name
                    for name in (
                        "daily-operating-update.md",
                        "weekly-operating-review.md",
                        "weekly-meeting-ticket.md",
                    )
                ),
                saved,
            )
        webhook = runtime.webhook_enabled(profile_home)
        receipt = _run_profile_setup(
            profile_home, webhook=webhook, multica=multica, apply=True
        )
        receipt["entry_point"] = "setup.py update"
        receipt_path = runtime.write_receipt(profile_home, receipt)
        CONSOLE.print(
            "[green]Update installed.[/green] "
            f"Support receipt: {receipt_reference(profile_home, receipt_path)}"
        )
        return 0
    except (runtime.RuntimeSetupError, FeatureSetupError, CatalogError) as error:
        CONSOLE.print(
            Panel.fit(
                "[bold red]Update stopped safely[/bold red]\n"
                + _friendly_runtime_error(error),
                border_style="red",
            )
        )
        return 2
