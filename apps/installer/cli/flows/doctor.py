"""Interactive rendering and dispatch for Doctor proof stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from apps.doctor import evaluation
from apps.doctor import run as analysis
from apps.installer import profile as profile_setup
from apps.installer import provider_catalog, readiness_evals, runtime
from apps.installer.cli.paths import profile_home as resolve_profile_home, receipt_reference
from apps.installer.cli.ui import CONSOLE


def _render_readiness(receipt: dict) -> None:
    table = Table(title="Data readiness preflight")
    table.add_column("Data source")
    table.add_column("State")
    table.add_column("Result")
    table.add_column("Action")
    for case in receipt.get("cases", []):
        status = str(case.get("status") or "failed")
        color = {"passed": "green", "needs_setup": "yellow"}.get(status, "red")
        issues = [str(item).replace("_", " ") for item in case.get("issues", [])]
        warnings = [str(item).replace("_", " ") for item in case.get("warnings", [])]
        action = "; ".join(issues or warnings) or "Ready"
        table.add_row(
            str(case.get("data_source") or "unknown").replace("_", " ").title(),
            str(case.get("source_state") or "unknown").replace("_", " "),
            f"[{color}]{status.replace('_', ' ')}[/{color}]",
            action,
        )
    CONSOLE.print(table)


def preflight_command(args: argparse.Namespace) -> int:
    profile = resolve_profile_home(args.profile_home)
    workspace = profile / "workspace.hermes.md"
    try:
        receipt = readiness_evals.run_readiness_evals(
            profile,
            workspace,
            timeout=args.timeout,
        )
        path = readiness_evals.write_receipt(profile, receipt)
        _render_readiness(receipt)
        status = str(receipt["status"])
        color = {"passed": "green", "needs_setup": "yellow"}.get(status, "red")
        CONSOLE.print(
            Panel.fit(
                f"[bold {color}]{status.replace('_', ' ').upper()}[/bold {color}]\n"
                f"Receipt: {receipt_reference(profile, path)}",
                border_style=color,
            )
        )
        return {"passed": 0, "needs_setup": 1}.get(status, 2)
    except (
        readiness_evals.ReadinessEvalError,
        provider_catalog.CatalogError,
        runtime.RuntimeSetupError,
    ) as error:
        CONSOLE.print(
            Panel.fit(
                "[bold red]Data readiness failed[/bold red]\n" + str(error),
                border_style="red",
            )
        )
        return 2


def evaluation_command(args: argparse.Namespace) -> int:
    profile = resolve_profile_home(args.profile_home)
    try:
        receipt = evaluation.run_evaluation(profile, timeout=args.timeout)
        if args.open:
            evaluation.open_latest_dossier(profile)
        status = str(receipt["status"])
        color = "green" if status == "passed" else "red"
        run = profile / evaluation.STATE_DIRECTORY / str(receipt["run_id"])
        CONSOLE.print(
            Panel.fit(
                f"[bold {color}]FULL EVAL {status.upper()}[/bold {color}]\n"
                f"Run: {run}\n"
                f"Dossier: {run / 'dossier' / 'index.html'}",
                border_style=color,
            )
        )
        return 0 if status == "passed" else 1
    except (evaluation.EvaluationError, runtime.RuntimeSetupError) as error:
        CONSOLE.print(
            Panel.fit(
                "[bold red]Full evaluation failed[/bold red]\n" + str(error),
                border_style="red",
            )
        )
        return 2


def open_dossier_command(args: argparse.Namespace) -> int:
    profile = resolve_profile_home(args.profile_home)
    try:
        uri = evaluation.open_latest_dossier(profile)
        CONSOLE.print(f"[green]Opened latest eval dossier:[/green] {uri}")
        return 0
    except evaluation.EvaluationError as error:
        CONSOLE.print(
            Panel.fit(
                "[bold red]No valid eval dossier could be opened[/bold red]\n" + str(error),
                border_style="red",
            )
        )
        return 2


def analysis_command(args: argparse.Namespace) -> int:
    args.profile_home = resolve_profile_home(args.profile_home)
    return analysis.operate(args)


def _latest_live_health(profile: Path) -> Path:
    candidates = sorted(
        (profile / runtime.RECEIPT_DIRECTORY).glob("setup-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(value, dict) and value.get("live") is True:
            if value.get("status") == "ready":
                return path
            raise profile_setup.ProfileSetupError(
                f"live_health_receipt_not_ready:{value.get('status') or 'unknown'}"
            )
    raise profile_setup.ProfileSetupError("live_health_receipt_missing")


def activate_command(args: argparse.Namespace) -> int:
    """Activate schedules only after all first-install proof receipts pass."""
    profile = resolve_profile_home(args.profile_home)
    try:
        health = _latest_live_health(profile)
        _, readiness = readiness_evals.latest_valid_passed_receipt(
            profile, profile / "workspace.hermes.md"
        )
        index = evaluation.latest_valid_index(profile)
        receipt = profile_setup.activate_managed_schedules(
            profile,
            {
                "live_health": health.name,
                "readiness_run_id": readiness.get("run_id"),
                "eval_run_id": index.parents[1].name,
            },
        )
        CONSOLE.print(
            Panel.fit(
                "[bold green]AUTOMATIONS ACTIVATED[/bold green]\n"
                f"Proof receipt: {receipt_reference(profile, receipt)}",
                border_style="green",
            )
        )
        return 0
    except (
        OSError,
        ValueError,
        evaluation.EvaluationError,
        profile_setup.ProfileSetupError,
        readiness_evals.ReadinessEvalError,
        provider_catalog.CatalogError,
    ) as error:
        CONSOLE.print(
            Panel.fit(
                "[bold red]Automations remain paused[/bold red]\n" + str(error),
                border_style="red",
            )
        )
        return 2
