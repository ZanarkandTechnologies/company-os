#!/usr/bin/env python3
"""Stage and validate the Company OS .hermes.md workspace context."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PACKAGE = Path(__file__).resolve().parents[1]
TEMPLATE = PACKAGE / "assets" / "templates" / "company-workspace.hermes.md"
SURFACES = ("Work", "People", "Knowledge", "Communications", "Decisions")
TABLE_HEADER = "| Platform | Use via (skill, CLI, or MCP) | Pages or sources | How it is structured |"


def emit(state: str, **values: object) -> None:
    print(json.dumps({"state": state, **values}, sort_keys=True))


def initialize(company_name: str, company_description: str, company_timezone: str, output: Path) -> int:
    if output.exists():
        emit("blocked", blocker="output_exists", output=str(output))
        return 2
    try:
        ZoneInfo(company_timezone.strip())
    except ZoneInfoNotFoundError:
        emit("blocked", blocker="invalid_company_timezone", timezone=company_timezone.strip())
        return 2
    content = TEMPLATE.read_text(encoding="utf-8")
    content = content.replace("{{COMPANY_NAME}}", company_name.strip())
    content = content.replace("{{COMPANY_DESCRIPTION}}", company_description.strip())
    content = content.replace("{{COMPANY_TIMEZONE}}", company_timezone.strip())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    emit("drafted", output=str(output), next_action="Fill source rows, remove onboarding comments, then run check.")
    return 0


def inspect(path: Path) -> tuple[list[str], str]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        return [f"cannot_read:{error}"], ""
    issues: list[str] = []
    if "{{" in content or "}}" in content:
        issues.append("unresolved_placeholder")
    timezone_match = re.search(r'^company_timezone:\s*"([^"]+)"\s*$', content, re.MULTILINE)
    if timezone_match:
        try:
            ZoneInfo(timezone_match.group(1))
        except ZoneInfoNotFoundError:
            issues.append("invalid_company_timezone")
    else:
        issues.append("company_timezone_missing")
    if "<!-- ONBOARDING:" in content:
        issues.append("onboarding_comments_remain")
    for surface in SURFACES:
        if content.count(f"## {surface}\n") != 1:
            issues.append(f"surface_missing_or_duplicated:{surface}")
    if content.count(TABLE_HEADER) != len(SURFACES):
        issues.append("surface_table_count_invalid")
    if re.search(r"(?i)(api[_ -]?key|access[_ -]?token|password)\s*[:=]\s*[^<\s][^\s]*", content):
        issues.append("possible_secret_value")
    return issues, content


def check(path: Path) -> int:
    issues, _ = inspect(path)
    if issues:
        emit("needs_review", file=str(path), issues=issues)
        return 1
    emit("ready_for_owner_review", file=str(path), surfaces=list(SURFACES))
    return 0


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    init = subcommands.add_parser("init", help="Create a staged Company OS context from the bundled template.")
    init.add_argument("--company-name", required=True)
    init.add_argument("--company-description", required=True)
    init.add_argument("--company-timezone", required=True, help="IANA timezone, such as Asia/Kuala_Lumpur.")
    init.add_argument("--output", type=Path, required=True)
    validate = subcommands.add_parser("check", help="Check a staged context before owner review.")
    validate.add_argument("--file", type=Path, required=True)
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "init":
        return initialize(args.company_name, args.company_description, args.company_timezone, args.output)
    return check(args.file)


if __name__ == "__main__":
    raise SystemExit(main())
