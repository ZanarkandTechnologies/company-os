#!/usr/bin/env python3
"""Preview or install reviewed company sources into a separate Hermes runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_PROJECT = PACKAGE.parents[1]
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


def validate_target(path: Path, label: str, project: Path) -> Path:
    if not path.exists() or not path.is_dir():
        raise SetupError(f"{label}_must_be_existing_directory")
    if path.is_symlink():
        raise SetupError(f"{label}_must_not_be_symlink")
    resolved = path.resolve()
    source_project = project.resolve()
    if resolved == source_project or inside(resolved, source_project):
        raise SetupError(f"{label}_must_be_outside_source_project")
    return resolved


def context_status(config: Path) -> str:
    content = config.read_text(encoding="utf-8")
    match = re.search(r"^status:\s*([^\s]+)\s*$", content, re.MULTILINE)
    if not match:
        raise SetupError("workspace_context_status_missing")
    return match.group(1)


def context_safety_issues(config: Path) -> list[str]:
    content = config.read_text(encoding="utf-8")
    issues: list[str] = []
    if "{{" in content or "<!-- ONBOARDING:" in content:
        issues.append("onboarding_artifacts_remain")
    forbidden = ("NOTION_API_KEY=", "GOOGLE_CLIENT_SECRET=", "refresh_token", "BEGIN PRIVATE KEY")
    if any(item in content for item in forbidden):
        issues.append("possible_secret")
    return issues


def source_files(project: Path, config: Path) -> list[tuple[Path, str, Path]]:
    files: list[tuple[Path, str, Path]] = [(config, "workspace", Path(".hermes.md"))]
    for owner, source_root, destination_root in (
        ("workspace", project / "automations", Path("automations")),
        ("profile", project / "skills", Path("skills")),
    ):
        for source in sorted(source_root.rglob("*")):
            relative = source.relative_to(source_root)
            if source.is_symlink() or any(part in EXCLUDED_NAMES for part in relative.parts):
                continue
            if owner == "profile" and not (source_root / relative.parts[0] / "SKILL.md").is_file():
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
    descriptor, temporary = tempfile.mkstemp(prefix=".company-setup-", dir=destination.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        shutil.copy2(source, temporary_path)
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def run(source_project_arg: Path, workspace_arg: Path, profile_home_arg: Path, apply: bool) -> int:
    try:
        source_project = source_project_arg.resolve()
        if not source_project.is_dir() or source_project_arg.is_symlink():
            raise SetupError("source_project_must_be_real_directory")
        config = source_project / "workspace.hermes.md"
        workspace = validate_target(workspace_arg, "workspace", source_project)
        profile_home = validate_target(profile_home_arg, "profile_home", source_project)
        if workspace == profile_home or inside(profile_home, workspace):
            raise SetupError("profile_home_must_not_be_workspace_or_its_child")
        status = context_status(config)
        safety_issues = context_safety_issues(config)
        changes: list[tuple[Path, Path, str, Path]] = []
        for source, owner, relative in source_files(source_project, config):
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
        if apply and safety_issues:
            emit("blocked", blocker="workspace_context_invalid", issues=safety_issues,
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
            deletion_count=0,
            source_project=str(source_project),
        )
        return 0
    except (OSError, SetupError) as error:
        emit("blocked", blocker=str(error))
        return 2


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--source-project", type=Path, default=DEFAULT_PROJECT)
    command.add_argument("--workspace", type=Path, required=True)
    command.add_argument("--profile-home", type=Path, required=True)
    command.add_argument("--apply", action="store_true", help="Copy changed allowlisted files; never deletes files.")
    return command


def main() -> int:
    args = parser().parse_args()
    return run(args.source_project, args.workspace, args.profile_home, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
