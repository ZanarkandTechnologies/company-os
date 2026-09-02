#!/usr/bin/env python3
"""Preview or install reviewed Company OS sources into a Hermes runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / "workspace.hermes.md"
EXCLUDED_NAMES = {".DS_Store", "__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
class SetupError(Exception):
    """A safe, operator-actionable setup failure."""


def emit(state: str, **values: object) -> None:
    print(json.dumps({"state": state, **values}, sort_keys=True))


def inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_target(path: Path, label: str, *, allow_inside_project: bool = False) -> Path:
    if not path.exists() or not path.is_dir():
        raise SetupError(f"{label}_must_be_existing_directory")
    if path.is_symlink():
        raise SetupError(f"{label}_must_not_be_symlink")
    resolved = path.resolve()
    project = PROJECT.resolve()
    if not allow_inside_project and (resolved == project or inside(resolved, project)):
        raise SetupError(f"{label}_must_be_outside_source_project")
    return resolved


def validate_installed_distribution(workspace: Path, profile_home: Path) -> None:
    manifest = PROJECT / "distribution.yaml"
    if profile_home.resolve() != PROJECT.resolve():
        raise SetupError("installed_distribution_profile_home_must_equal_source")
    if workspace.resolve() != (profile_home / "workspace").resolve():
        raise SetupError("installed_distribution_workspace_must_be_profile_workspace")
    if not manifest.is_file():
        raise SetupError("installed_distribution_manifest_missing")
    content = manifest.read_text(encoding="utf-8")
    if not re.search(r"^source:\s*\S+", content, re.MULTILINE):
        raise SetupError("installed_distribution_source_missing")
    if not re.search(r"^installed_at:\s*\S+", content, re.MULTILINE):
        raise SetupError("installed_distribution_timestamp_missing")


def context_status() -> str:
    content = CONFIG.read_text(encoding="utf-8")
    match = re.search(r"^status:\s*([^\s]+)\s*$", content, re.MULTILINE)
    if not match:
        raise SetupError("workspace_context_status_missing")
    return match.group(1)


def source_files() -> list[tuple[Path, str, Path]]:
    files: list[tuple[Path, str, Path]] = [(CONFIG, "workspace", Path(".hermes.md"))]
    preflight_prompt = PROJECT / "apps" / "installer" / "prompts" / "preflight.md"
    if preflight_prompt.is_file():
        files.append(
            (preflight_prompt, "workspace", Path("prompts") / "preflight.md")
        )
    for name in ("pm-daily", "pm-weekly"):
        package = PROJECT / "skills" / name
        skill = package / "SKILL.md"
        if skill.is_file():
            files.append((skill, "workspace", Path("skills") / name / "SKILL.md"))
        for owned_directory in ("templates", "evals"):
            source_root = package / owned_directory
            for source in sorted(source_root.rglob("*")):
                relative = source.relative_to(package)
                if source.is_symlink() or any(part in EXCLUDED_NAMES for part in relative.parts):
                    continue
                if source.is_file() and source.suffix not in EXCLUDED_SUFFIXES:
                    files.append((source, "workspace", Path("skills") / name / relative))
    for owner, source_root, destination_root in (
        ("workspace", PROJECT / "automations", Path("automations")),
        ("workspace", PROJECT / "templates", Path("templates")),
        ("profile", PROJECT / "plugins", Path("plugins")),
    ):
        for source in sorted(source_root.rglob("*")):
            relative = source.relative_to(source_root)
            if source.is_symlink() or any(part in EXCLUDED_NAMES for part in relative.parts):
                continue
            if source.is_file() and source.suffix not in EXCLUDED_SUFFIXES:
                files.append((source, owner, destination_root / relative))
    return files


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            value.update(block)
    return value.hexdigest()


def check_destination(destination: Path, root: Path) -> None:
    if not inside(destination, root):
        raise SetupError("destination_escaped_target")
    cursor = root
    for part in destination.relative_to(root).parts:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise SetupError(f"destination_contains_symlink:{destination.relative_to(root)}")
    if destination.exists() and not destination.is_file():
        raise SetupError(f"destination_must_be_file:{destination.relative_to(root)}")


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".company-os-setup-", dir=destination.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        shutil.copy2(source, temporary_path)
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def run(
    workspace_arg: Path,
    profile_home_arg: Path,
    apply: bool,
    installed_distribution: bool = False,
) -> int:
    try:
        workspace = validate_target(
            workspace_arg, "workspace", allow_inside_project=installed_distribution
        )
        profile_home = validate_target(
            profile_home_arg, "profile_home", allow_inside_project=installed_distribution
        )
        if installed_distribution:
            validate_installed_distribution(workspace, profile_home)
        if workspace == profile_home or inside(profile_home, workspace):
            raise SetupError("profile_home_must_not_be_workspace_or_its_child")
        status = context_status()
        changes: list[tuple[Path, Path, str, Path]] = []
        for source, owner, relative in source_files():
            root = workspace if owner == "workspace" else profile_home
            destination = root / relative
            check_destination(destination, root)
            if not destination.exists() or not destination.is_file() or digest(source) != digest(destination):
                changes.append((source, destination, owner, relative))
        public_changes = [f"{owner}:{relative.as_posix()}" for _, _, owner, relative in changes]
        if apply and status not in {"approved", "active"}:
            emit("blocked", blocker="workspace_context_requires_owner_approval", context_status=status,
                 pending_changes=public_changes)
            return 2
        if apply:
            for source, destination, _, _ in changes:
                atomic_copy(source, destination)
        emit(
            "configured" if apply else ("changes_pending" if changes else "in_sync"),
            mode="apply" if apply else "preview",
            context_status=status,
            changed=public_changes if apply else [],
            pending=[] if apply else public_changes,
            source_project=str(PROJECT),
        )
        return 0
    except (OSError, SetupError) as error:
        emit("blocked", blocker=str(error))
        return 2


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--workspace", type=Path, required=True)
    command.add_argument("--profile-home", type=Path, required=True)
    command.add_argument(
        "--apply",
        action="store_true",
        help="Copy allowlisted files into the configured workspace and profile.",
    )
    command.add_argument(
        "--installed-distribution",
        action="store_true",
        help="Allow the verified native distribution profile to install its own workspace.",
    )
    return command


def main() -> int:
    args = parser().parse_args()
    return run(args.workspace, args.profile_home, args.apply, args.installed_distribution)


if __name__ == "__main__":
    raise SystemExit(main())
