"""Parse and dispatch the stable Company OS setup command surface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from apps.installer import runtime
from apps.installer.cli.flows.connections import certify_command
from apps.installer.cli.flows.lifecycle import install_command, launch_command, update_command
from apps.installer.cli.flows.verification import verify_command
from apps.installer.cli.flows.workspace import configure_workspace
from apps.installer.cli.flows.features import configure_features
from apps.installer.cli.paths import DEFAULT_TEMPLATE, DEFAULT_WORKSPACE, profile_home
from apps.installer.cli.ui import CONSOLE


DESCRIPTION = (
    "Configure Company OS features and manage its installed Hermes profile. "
    "The feature wizard saves resumable answers and renders self-contained automations. "
    "Runtime commands delegate filesystem, credential, and health-check operations "
    "to deterministic setup backends."
)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=DESCRIPTION)
    subcommands = command.add_subparsers(dest="command")

    for name in ("init", "configure"):
        workspace = subcommands.add_parser(name)
        workspace.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
        workspace.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)

    features = subcommands.add_parser("features")
    features.add_argument("--root", type=Path, default=Path.cwd())

    launch = subcommands.add_parser("launch")
    launch.add_argument("--profile-home", type=Path)
    launch.add_argument("--installed", action="store_true", help=argparse.SUPPRESS)
    launch.add_argument("--non-interactive", action="store_true", help=argparse.SUPPRESS)

    install = subcommands.add_parser("install")
    install.add_argument("--profile-home", type=Path)
    install.add_argument("--installed", action="store_true", help=argparse.SUPPRESS)
    install.add_argument("--non-interactive", action="store_true", help=argparse.SUPPRESS)

    update = subcommands.add_parser("update")
    update.add_argument("--profile-home", type=Path)

    verify = subcommands.add_parser("verify")
    verify.add_argument("--profile-home", type=Path)
    verify.add_argument("--live", action="store_true")
    verify.add_argument("--wait", type=int, default=120)
    verify.add_argument("--test-connections", action="store_true")
    verify.add_argument("--skip-connections", action="store_true")
    verify.add_argument("--allow-side-effects", action="store_true")

    certify = subcommands.add_parser("certify")
    certify.add_argument("--profile-home", type=Path)
    certify.add_argument("--allow-side-effects", action="store_true")

    doctor = subcommands.add_parser("doctor")
    doctor_modes = doctor.add_subparsers(dest="doctor_mode", required=True)

    preflight = doctor_modes.add_parser("preflight")
    preflight.add_argument("--profile-home", type=Path)
    preflight.add_argument("--timeout", type=int, default=180)

    evaluate = doctor_modes.add_parser("eval")
    evaluate.add_argument("--profile-home", type=Path)
    evaluate.add_argument("--timeout", type=int, default=900)
    evaluate.add_argument("--open", action="store_true")

    open_dossier = doctor_modes.add_parser("open")
    open_dossier.add_argument("--profile-home", type=Path)

    activate = doctor_modes.add_parser("activate")
    activate.add_argument("--profile-home", type=Path)

    analyze = doctor_modes.add_parser("analysis")
    analyze.add_argument("--profile-home", type=Path)
    analyze.add_argument(
        "--cadence",
        dest="cadences",
        action="append",
        choices=("daily", "weekly"),
    )

    for name in ("webhook-enabled", "webhook-commit", "webhook-rollback"):
        subcommands.add_parser(name).add_argument("--profile-home", type=Path)
    ingress = subcommands.add_parser("webhook-ingress-ready")
    ingress.add_argument("--profile-home", type=Path)
    ingress.add_argument("--wait", type=int, default=30)
    return command


def main(arguments: list[str] | None = None) -> int:
    try:
        selected_arguments = arguments if arguments is not None else (sys.argv[1:] or ["launch"])
        args = parser().parse_args(selected_arguments)
        selected = args.command
        if selected in {"init", "configure"}:
            return configure_workspace(
                selected,
                args.workspace.expanduser().resolve(),
                args.template.expanduser().resolve(),
            )
        if selected == "features":
            return configure_features(args.root.expanduser().resolve())
        if selected == "launch":
            return launch_command(args)
        if selected == "install":
            return install_command(args)
        if selected == "update":
            return update_command(args)
        if selected == "verify":
            return verify_command(args)
        if selected == "certify":
            return certify_command(args)
        if selected == "doctor":
            from apps.installer.cli.flows import doctor

            if args.doctor_mode == "preflight":
                return doctor.preflight_command(args)
            if args.doctor_mode == "eval":
                return doctor.evaluation_command(args)
            if args.doctor_mode == "open":
                return doctor.open_dossier_command(args)
            if args.doctor_mode == "activate":
                return doctor.activate_command(args)
            return doctor.analysis_command(args)
        if selected == "webhook-enabled":
            return 0 if runtime.webhook_enabled(profile_home(args.profile_home)) else 1
        if selected == "webhook-ingress-ready":
            return 0 if runtime.wait_for_webhook_ingress(
                profile_home(args.profile_home), args.wait
            ) else 1
        if selected == "webhook-commit":
            runtime.commit_ngrok_update(profile_home(args.profile_home))
            return 0
        if selected == "webhook-rollback":
            runtime.rollback_ngrok_update(profile_home(args.profile_home))
            return 0
        return 2
    except (KeyboardInterrupt, EOFError):
        CONSOLE.print(
            "\n[yellow]Stopped safely. No additional setup changes were made.[/yellow]"
        )
        return 130
