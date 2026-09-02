#!/usr/bin/env python3
"""Install a Company OS workspace and reconcile its native Hermes jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path(__file__).resolve().parents[2]
SETUP_WORKSPACE = SOURCE_ROOT / "apps" / "installer" / "workspace.py"
ACTIVATION_RECEIPT = Path("state/setup-proof.json")
NOTION_PLUGIN_NAME = "notion-platform"
NOTION_PLUGIN_KEY = "platforms/notion"
MULTICA_PLUGIN_NAME = "multica"
MULTICA_PLUGIN_KEY = "multica"

SCHEDULES = (
    {
        "name": "Company OS Daily Operating Update",
        "legacy_names": ("Company OS Daily Operating Update",),
        "schedule": "0 8 * * 1-5",
        "contract": "automations/daily-operating-update.md",
        "cadence": "Daily",
    },
    {
        "name": "Company OS Weekly Operating Review",
        "legacy_names": ("Company OS Weekly Operating Review",),
        "schedule": "0 18 * * 5",
        "contract": "automations/weekly-operating-review.md",
        "cadence": "Weekly",
    },
    {
        "name": "Company OS Weekly Meeting Ticket",
        "legacy_names": (),
        "schedule": "0 9 * * 1",
        "contract": "automations/weekly-meeting-ticket.md",
        "cadence": "Weekly meeting-ticket",
    },
)


class ProfileSetupError(Exception):
    """A safe, operator-actionable profile setup failure."""


def emit(state: str, **values: object) -> None:
    print(json.dumps({"state": state, **values}, sort_keys=True))


def command_env(profile_home: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["HERMES_HOME"] = str(profile_home)
    environment.pop("HERMES_PROFILE", None)
    return environment


def run_command(arguments: list[str], profile_home: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        arguments,
        text=True,
        capture_output=True,
        check=False,
        env=command_env(profile_home),
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise ProfileSetupError(detail[-1] if detail else f"command_failed:{arguments[0]}")
    return result


def gateway_is_running(result: subprocess.CompletedProcess[str]) -> bool:
    output = f"{result.stdout}\n{result.stderr}"
    return "✓ Gateway is running" in output


def notion_plugin_enabled(profile_home: Path) -> bool:
    result = run_command(
        ["hermes", "plugins", "list", "--user", "--json"], profile_home
    )
    try:
        plugins = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ProfileSetupError("plugin_list_unreadable") from error
    if not isinstance(plugins, list):
        raise ProfileSetupError("plugin_list_must_be_list")
    return any(
        isinstance(plugin, dict)
        and plugin.get("name") == NOTION_PLUGIN_NAME
        and plugin.get("status") == "enabled"
        for plugin in plugins
    )


def enable_notion_plugin(profile_home: Path) -> None:
    run_command(
        [
            "hermes", "plugins", "enable", NOTION_PLUGIN_KEY,
            "--no-allow-tool-override",
        ],
        profile_home,
    )
    run_command(["hermes", "plugins", "doctor", NOTION_PLUGIN_KEY], profile_home)
    if not notion_plugin_enabled(profile_home):
        raise ProfileSetupError("notion_plugin_enable_verification_failed")


def multica_plugin_enabled(profile_home: Path) -> bool:
    result = run_command(
        ["hermes", "plugins", "list", "--user", "--json"], profile_home
    )
    try:
        plugins = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ProfileSetupError("plugin_list_unreadable") from error
    return isinstance(plugins, list) and any(
        isinstance(plugin, dict)
        and plugin.get("name") == MULTICA_PLUGIN_NAME
        and plugin.get("status") == "enabled"
        for plugin in plugins
    )


def enable_multica_plugin(profile_home: Path) -> None:
    run_command(
        [
            "hermes", "plugins", "enable", MULTICA_PLUGIN_KEY,
            "--no-allow-tool-override",
        ],
        profile_home,
    )
    run_command(["hermes", "plugins", "doctor", MULTICA_PLUGIN_KEY], profile_home)
    if not multica_plugin_enabled(profile_home):
        raise ProfileSetupError("multica_plugin_enable_verification_failed")


def read_jobs(profile_home: Path) -> list[dict[str, Any]]:
    path = profile_home / "cron" / "jobs.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileSetupError(f"cron_jobs_unreadable:{error}") from error
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    if not isinstance(jobs, list):
        raise ProfileSetupError("cron_jobs_must_be_list")
    return [job for job in jobs if isinstance(job, dict)]


def workspace_setting(workspace: Path, key: str, default: str) -> str:
    """Read one nonsecret managed setting from the installed workspace."""
    content = ""
    for path in (workspace / ".hermes.md", SOURCE_ROOT / "workspace.hermes.md"):
        try:
            content = path.read_text(encoding="utf-8")
            break
        except OSError:
            continue
    if not content:
        return default
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", content, re.MULTILINE)
    if not match:
        return default
    raw = match.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        try:
            raw = str(json.loads(raw))
        except json.JSONDecodeError:
            return default
    return raw if raw and raw != "REPLACE_ME" else default


def desired_job(spec: dict[str, Any], workspace: Path) -> dict[str, str]:
    contract = workspace / spec["contract"]
    company_name = workspace_setting(workspace, "company_name", "Company")
    timezone = workspace_setting(workspace, "company_timezone", "UTC")
    prompt = (
        f"Execute the installed {company_name} Company OS {spec['cadence']} operating automation. "
        f"Read {workspace / '.hermes.md'} and {contract} completely, then follow "
        "the contract's authority, validation, receipt, idempotency, and stop conditions. "
        f"Use {timezone} as the company timezone and never infer production authority."
    )
    return {
        "name": spec["name"],
        "schedule": spec["schedule"],
        "prompt": prompt,
        "workdir": str(workspace),
        "deliver": "local",
    }


def schedule_expression(job: dict[str, Any]) -> str:
    schedule = job.get("schedule")
    if isinstance(schedule, dict):
        return str(schedule.get("expr") or "")
    return str(schedule or "")


def schedule_configuration_hash(profile_home: Path, workspace: Path | None = None) -> str:
    """Bind activation proof to current jobs, contracts, and rendered answers."""
    workspace = workspace or profile_home / "workspace"
    digest = hashlib.sha256()
    for spec in SCHEDULES:
        desired = desired_job(spec, workspace)
        digest.update(json.dumps(desired, sort_keys=True).encode())
        contract = workspace / spec["contract"]
        digest.update(contract.read_bytes() if contract.is_file() else b"<missing-contract>")
    answers = profile_home / "config" / "setup-answers.json"
    digest.update(answers.read_bytes() if answers.is_file() else b"<missing-answers>")
    return digest.hexdigest()


def schedules_activated(profile_home: Path, workspace: Path | None = None) -> bool:
    try:
        receipt = json.loads((profile_home / ACTIVATION_RECEIPT).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        isinstance(receipt, dict)
        and receipt.get("status") == "activated"
        and receipt.get("schedule_configuration_hash")
        == schedule_configuration_hash(profile_home, workspace)
    )


def cron_plan(profile_home: Path, workspace: Path) -> list[dict[str, Any]]:
    jobs = read_jobs(profile_home)
    should_be_enabled = schedules_activated(profile_home, workspace)
    actions: list[dict[str, Any]] = []
    for spec in SCHEDULES:
        desired = desired_job(spec, workspace)
        accepted_names = {desired["name"], *spec.get("legacy_names", ())}
        matches = [job for job in jobs if job.get("name") in accepted_names]
        if len(matches) > 1:
            raise ProfileSetupError(f"duplicate_cron_name:{desired['name']}")
        if not matches:
            actions.append({"action": "create", **desired})
            continue
        current = matches[0]
        exact = (
            current.get("name") == desired["name"]
            and schedule_expression(current) == desired["schedule"]
            and current.get("prompt") == desired["prompt"]
            and current.get("workdir") == desired["workdir"]
            and current.get("deliver", "local") == "local"
            and (current.get("enabled", True) is not False) is should_be_enabled
        )
        actions.append(
            {
                "action": "in_sync" if exact else "update",
                "id": str(current.get("id") or ""),
                **desired,
            }
        )
    return actions


def set_managed_schedules_enabled(profile_home: Path, enabled: bool) -> list[dict[str, Any]]:
    """Set only Company OS schedules to the proof-gated desired state."""
    jobs = read_jobs(profile_home)
    states: list[dict[str, Any]] = []
    for spec in SCHEDULES:
        accepted = {spec["name"], *spec.get("legacy_names", ())}
        matches = [job for job in jobs if job.get("name") in accepted]
        if len(matches) != 1 or not matches[0].get("id"):
            raise ProfileSetupError(f"managed_cron_job_missing:{spec['name']}")
        job = matches[0]
        currently_enabled = job.get("enabled", True) is not False
        if currently_enabled != enabled:
            verb = "resume" if enabled else "pause"
            run_command(["hermes", "cron", verb, str(job["id"])], profile_home)
        states.append({"id": str(job["id"]), "name": spec["name"], "enabled": enabled})
    return states


def activate_managed_schedules(profile_home: Path, proof: dict[str, Any]) -> Path:
    """Resume and verify managed schedules, committing proof only on success."""
    destination = profile_home / ACTIVATION_RECEIPT
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = destination.with_suffix(".pending.json")

    def write_atomic(target: Path, payload: dict[str, Any]) -> None:
        descriptor, temporary = tempfile.mkstemp(prefix=".setup-proof-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    write_atomic(
        pending,
        {"schema_version": 1, "status": "activating", "proof": proof},
    )
    try:
        set_managed_schedules_enabled(profile_home, True)
        jobs = read_jobs(profile_home)
        workspace = profile_home / "workspace"
        for spec in SCHEDULES:
            desired = desired_job(spec, workspace)
            accepted = {desired["name"], *spec.get("legacy_names", ())}
            matches = [job for job in jobs if job.get("name") in accepted]
            if len(matches) != 1:
                raise ProfileSetupError(f"cron_activation_verification_failed:{desired['name']}")
            current = matches[0]
            if not (
                current.get("enabled", True) is not False
                and current.get("name") == desired["name"]
                and schedule_expression(current) == desired["schedule"]
                and current.get("prompt") == desired["prompt"]
                and current.get("workdir") == desired["workdir"]
                and current.get("deliver", "local") == "local"
            ):
                raise ProfileSetupError(f"cron_activation_verification_failed:{desired['name']}")
        write_atomic(
            destination,
            {
                "schema_version": 1,
                "status": "activated",
                "activated_at": time.time(),
                "proof": proof,
                "schedule_configuration_hash": schedule_configuration_hash(
                    profile_home, workspace
                ),
            },
        )
    except BaseException:
        rollback_error: BaseException | None = None
        try:
            set_managed_schedules_enabled(profile_home, False)
        except Exception as caught:
            rollback_error = caught
        destination.unlink(missing_ok=True)
        pending.unlink(missing_ok=True)
        if rollback_error is not None:
            raise ProfileSetupError("cron_activation_rollback_failed") from rollback_error
        raise
    pending.unlink(missing_ok=True)
    return destination


def apply_cron(profile_home: Path, actions: list[dict[str, Any]]) -> None:
    for job in actions:
        if job["action"] == "in_sync":
            continue
        common = [
            "--name", job["name"], "--deliver", "local", "--workdir", job["workdir"]
        ]
        if job["action"] == "create":
            command = ["hermes", "cron", "create", job["schedule"], job["prompt"], *common]
        else:
            if not job.get("id"):
                raise ProfileSetupError(f"cron_job_id_missing:{job['name']}")
            command = [
                "hermes", "cron", "edit", job["id"], "--schedule", job["schedule"],
                "--prompt", job["prompt"], *common,
            ]
        run_command(command, profile_home)
    set_managed_schedules_enabled(
        profile_home,
        schedules_activated(profile_home, profile_home / "workspace"),
    )


def run(
    profile_home: Path,
    apply: bool,
    enable_notion_webhook: bool = False,
    enable_multica: bool = False,
) -> int:
    try:
        profile_home = profile_home.expanduser().resolve()
        if not profile_home.is_dir():
            raise ProfileSetupError("profile_home_must_be_existing_directory")
        workspace = profile_home / "workspace"
        if apply:
            workspace.mkdir(parents=True, exist_ok=True)
        elif not workspace.is_dir():
            emit(
                "changes_pending",
                profile_home=str(profile_home),
                workspace=str(workspace),
                workspace_action="create",
                cron_actions=[{"name": item["name"], "action": "create"} for item in SCHEDULES],
                next_action="rerun_with_apply",
            )
            return 0

        workspace_command = [
            sys.executable, str(SETUP_WORKSPACE), "--workspace", str(workspace),
            "--profile-home", str(profile_home),
        ]
        if profile_home == SOURCE_ROOT.resolve():
            workspace_command.append("--installed-distribution")
        if apply:
            workspace_command.append("--apply")
        setup_result = run_command(workspace_command, profile_home)
        setup_receipt = json.loads(setup_result.stdout)
        actions = cron_plan(profile_home, workspace)
        plugin_action = (
            "in_sync" if notion_plugin_enabled(profile_home) else "enable"
        ) if enable_notion_webhook else "not_requested"
        multica_plugin_action = (
            "in_sync" if multica_plugin_enabled(profile_home) else "enable"
        ) if enable_multica else "not_requested"
        if not apply:
            emit(
                "changes_pending" if setup_receipt.get("pending") or any(
                    item["action"] != "in_sync" for item in actions
                ) or plugin_action == "enable" or multica_plugin_action == "enable" else "in_sync",
                profile_home=str(profile_home),
                workspace=str(workspace),
                workspace_setup=setup_receipt,
                notion_plugin_action=plugin_action,
                multica_plugin_action=multica_plugin_action,
                cron_actions=actions,
                next_action="rerun_with_apply",
            )
            return 0

        if enable_notion_webhook:
            enable_notion_plugin(profile_home)
        if enable_multica:
            enable_multica_plugin(profile_home)
        run_command(["hermes", "config", "set", "terminal.backend", "docker"], profile_home)
        backend_result = run_command(
            ["hermes", "config", "get", "terminal.backend"], profile_home
        )
        if backend_result.stdout.strip().lower() != "docker":
            raise ProfileSetupError("terminal_backend_verification_failed")
        run_command(["hermes", "config", "set", "terminal.cwd", str(workspace)], profile_home)
        cwd_result = run_command(["hermes", "config", "get", "terminal.cwd"], profile_home)
        if Path(cwd_result.stdout.strip()).expanduser().resolve() != workspace.resolve():
            raise ProfileSetupError("terminal_cwd_verification_failed")
        # Hermes' Docker backend intentionally defaults to an isolated,
        # ephemeral /workspace. Company OS artifacts must survive container
        # teardown, so bind only this selected profile workspace to /workspace.
        run_command(
            [
                "hermes", "config", "set",
                "terminal.docker_mount_cwd_to_workspace", "true",
            ],
            profile_home,
        )
        mount_result = run_command(
            [
                "hermes", "config", "get",
                "terminal.docker_mount_cwd_to_workspace",
            ],
            profile_home,
        )
        if mount_result.stdout.strip().lower() not in {"true", "1", "yes", "on"}:
            raise ProfileSetupError("terminal_workspace_mount_verification_failed")
        apply_cron(profile_home, actions)
        verified = cron_plan(profile_home, workspace)
        if any(item["action"] != "in_sync" for item in verified):
            raise ProfileSetupError("cron_verification_failed")
        gateway = subprocess.run(
            ["hermes", "gateway", "status"], text=True, capture_output=True,
            check=False, env=command_env(profile_home),
        )
        scheduler_ready = gateway_is_running(gateway)
        emit(
            "configured" if scheduler_ready else "partial",
            profile_home=str(profile_home),
            workspace=str(workspace),
            workspace_setup=setup_receipt,
            notion_plugin_action="in_sync" if enable_notion_webhook else "not_requested",
            multica_plugin_action="in_sync" if enable_multica else "not_requested",
            terminal_cwd=str(workspace),
            terminal_backend="docker",
            terminal_workspace_mount=True,
            cron_jobs=verified,
            schedules_activated=schedules_activated(profile_home),
            scheduler_ready=scheduler_ready,
            next_action=(
                "verify_installation"
                if scheduler_ready
                else "start_the_profile_gateway_then_run_setup_verify"
            ),
        )
        return 0
    except (OSError, json.JSONDecodeError, ProfileSetupError) as error:
        emit("blocked", blocker=str(error))
        return 2


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    default_home = os.environ.get("HERMES_HOME")
    command.add_argument(
        "--profile-home", type=Path, default=Path(default_home) if default_home else None,
        help="Installed distribution profile root; defaults to HERMES_HOME.",
    )
    command.add_argument("--apply", action="store_true")
    command.add_argument(
        "--enable-notion-webhook",
        action="store_true",
        help="Enable and validate the optional Notion webhook plugin.",
    )
    command.add_argument(
        "--enable-multica",
        action="store_true",
        help="Enable and validate the host-side Multica task plugin.",
    )
    return command


def main() -> int:
    args = parser().parse_args()
    if args.profile_home is None:
        emit("blocked", blocker="profile_home_required")
        return 2
    return run(
        args.profile_home,
        args.apply,
        args.enable_notion_webhook,
        args.enable_multica,
    )


if __name__ == "__main__":
    raise SystemExit(main())
