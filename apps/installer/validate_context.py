#!/usr/bin/env python3
"""Validate a rendered Company OS context without reading credentials."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

REQUIRED_SECTIONS = (
    "Company",
    "Data sources",
    "Private weekly workspace",
    "Outputs",
    "Communications",
    "Operating guidance",
)
REQUIRED_BLOCKS = ("data-sources", "artifact-sync", "communications")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    args = parser.parse_args()
    content = args.context.read_text(encoding="utf-8")
    errors: list[str] = []
    if "{{" in content or "REPLACE_ME" in content or "<!-- ONBOARDING:" in content:
        errors.append("template_artifacts_remain")
    for field in ("company_name", "company_description"):
        if not re.search(rf'^{field}:\s*"[^"\n]+"\s*$', content, re.MULTILINE):
            errors.append(f"{field}_missing")
    timezone = re.search(r'^company_timezone:\s*"([^"]+)"\s*$', content, re.MULTILINE)
    if not timezone:
        errors.append("company_timezone_missing")
    else:
        try:
            ZoneInfo(timezone.group(1))
        except ZoneInfoNotFoundError:
            errors.append("company_timezone_invalid")
    for section in REQUIRED_SECTIONS:
        if content.count(f"## {section}\n") != 1:
            errors.append(f"section_invalid:{section}")
    for block in REQUIRED_BLOCKS:
        if content.count(f"<!-- hermes:managed {block} -->") != 1 or content.count(
            f"<!-- /hermes:managed {block} -->"
        ) != 1:
            errors.append(f"managed_block_invalid:{block}")
    forbidden = ("NOTION_API_KEY=", "GOOGLE_CLIENT_SECRET=", "refresh_token", "BEGIN PRIVATE KEY")
    if any(item in content for item in forbidden):
        errors.append("possible_secret")
    required = ("proposal-only", "Project Memory", "Employee Memory", "SOP Memory")
    if any(item not in content for item in required):
        errors.append("required_company_os_policy_missing")
    if errors:
        print("context_invalid=" + ",".join(errors))
        return 1
    print("context_valid=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
