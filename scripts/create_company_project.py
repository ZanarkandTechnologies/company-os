#!/usr/bin/env python3
"""Create a lean company project from canonical HermesCorp assets."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
STATIC_TEMPLATE = ROOT / "templates" / "company-project"
WORKSPACE_TEMPLATE = ROOT / "skills/company-os-onboarding/assets/templates/company-workspace.hermes.md"
SETUP_SKILL = ROOT / "skills" / "setup-company-workspace"
FILESYSTEM_EVALS = ROOT / "templates" / "authored-filesystem-evals"
AUTOMATIONS = (
    ROOT / "automations/daily-operating-update.md",
    ROOT / "automations/weekly-operating-review.md",
)
IGNORED_COPY_NAMES = {".DS_Store", "__pycache__"}


class ScaffoldError(Exception):
    """A safe project-scaffold failure."""


def emit(state: str, **values: object) -> None:
    print(json.dumps({"state": state, **values}, sort_keys=True))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ScaffoldError("company_name_must_produce_slug")
    return slug


def copy_ignore(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_COPY_NAMES or name.endswith((".pyc", ".pyo"))}


def render_text(path: Path, values: dict[str, str]) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for marker, value in values.items():
        content = content.replace(marker, value)
    path.write_text(content, encoding="utf-8")


def create_project(target_arg: Path, company_name: str, description: str, timezone: str) -> int:
    try:
        target = target_arg.expanduser()
        if target.exists() or target.is_symlink():
            raise ScaffoldError("target_must_not_exist")
        parent = target.parent.resolve()
        if not parent.is_dir():
            raise ScaffoldError("target_parent_must_exist")
        if not company_name.strip() or not description.strip():
            raise ScaffoldError("company_name_and_description_required")
        try:
            ZoneInfo(timezone.strip())
        except ZoneInfoNotFoundError as error:
            raise ScaffoldError("invalid_company_timezone") from error
        required = (STATIC_TEMPLATE, WORKSPACE_TEMPLATE, SETUP_SKILL, FILESYSTEM_EVALS, *AUTOMATIONS)
        if any(not item.exists() for item in required):
            raise ScaffoldError("canonical_template_asset_missing")

        values = {
            "{{COMPANY_NAME}}": company_name.strip(),
            "{{COMPANY_DESCRIPTION}}": description.strip(),
            "{{COMPANY_TIMEZONE}}": timezone.strip(),
            "{{COMPANY_SLUG}}": slugify(company_name),
        }
        with tempfile.TemporaryDirectory(prefix=".company-project-", dir=parent) as temporary:
            staging = Path(temporary) / "project"
            shutil.copytree(STATIC_TEMPLATE, staging, ignore=copy_ignore)
            (staging / "workspace.hermes.md").write_text(
                WORKSPACE_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            for source in AUTOMATIONS:
                shutil.copy2(source, staging / "automations" / source.name)
            shutil.copytree(SETUP_SKILL, staging / "skills/setup-company-workspace", ignore=copy_ignore)
            shutil.copytree(FILESYSTEM_EVALS, staging / "evals/filesystem", ignore=copy_ignore)
            for path in staging.rglob("*"):
                if path.is_file():
                    render_text(path, values)
            os.replace(staging, target)
        file_count = sum(1 for path in target.rglob("*") if path.is_file())
        emit("created", target=str(target.resolve()), company_slug=values["{{COMPANY_SLUG}}"],
             file_count=file_count, git_initialized=False, next_action="Review workspace.hermes.md")
        return 0
    except (OSError, ScaffoldError) as error:
        emit("blocked", blocker=str(error))
        return 2


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--target", type=Path, required=True)
    command.add_argument("--company-name", required=True)
    command.add_argument("--company-description", required=True)
    command.add_argument("--company-timezone", required=True)
    return command


def main() -> int:
    args = parser().parse_args()
    return create_project(args.target, args.company_name, args.company_description, args.company_timezone)


if __name__ == "__main__":
    raise SystemExit(main())
