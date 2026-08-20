#!/usr/bin/env python3
"""Validate a rendered Company OS workspace context without reading credentials."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SURFACES = ("Work", "People", "Knowledge", "Communications", "Decisions")
TABLE_HEADER = "| Platform | Use via (skill, CLI, or MCP) | Pages or sources | How it is structured |"


def inspect(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8")
    errors: list[str] = []
    if "{{" in content or "<!-- ONBOARDING:" in content:
        errors.append("onboarding_artifacts_remain")
    timezone = re.search(r'^company_timezone:\s*"([^"]+)"\s*$', content, re.MULTILINE)
    if not timezone:
        errors.append("company_timezone_missing")
    else:
        try:
            ZoneInfo(timezone.group(1))
        except ZoneInfoNotFoundError:
            errors.append("company_timezone_invalid")
    status = re.search(r"^status:\s*([^\s]+)\s*$", content, re.MULTILINE)
    if not status or status.group(1) not in {"proposed-owner-review", "approved", "active"}:
        errors.append("workspace_status_invalid")
    for surface in SURFACES:
        if content.count(f"## {surface}\n") != 1:
            errors.append(f"surface_invalid:{surface}")
    if content.count(TABLE_HEADER) != len(SURFACES):
        errors.append("surface_table_count_invalid")
    forbidden = ("NOTION_API_KEY=", "GOOGLE_CLIENT_SECRET=", "refresh_token", "BEGIN PRIVATE KEY")
    if any(item in content for item in forbidden):
        errors.append("possible_secret")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors = inspect(args.context)
    except OSError as error:
        print(f"context_invalid=cannot_read:{error}")
        return 1
    if errors:
        print("context_invalid=" + ",".join(errors))
        return 1
    print("context_valid=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
