#!/usr/bin/env python3
"""Fetch today's Notion records and safely propose or post documentation comments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_PAGE_SIZE = 25
MARKER_PREFIX = "Hermes documentation check"


class CheckError(RuntimeError):
    pass


def emit(state: str, **values: Any) -> None:
    print(json.dumps({"state": state, **values}, ensure_ascii=False, sort_keys=True))


def ntn_env() -> dict[str, str]:
    env = os.environ.copy()
    if env.get("NOTION_TOKEN") and not env.get("NOTION_API_TOKEN"):
        env["NOTION_API_TOKEN"] = env["NOTION_TOKEN"]
    return env


def run_ntn(*args: str) -> str:
    try:
        result = subprocess.run(["ntn", *args], text=True, capture_output=True, check=False, env=ntn_env())
    except FileNotFoundError as error:
        raise CheckError("ntn_not_found") from error
    if result.returncode:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown_error"
        raise CheckError(f"ntn_failed:{detail}")
    return result.stdout


def parse_json(raw: str, operation: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CheckError(f"invalid_json:{operation}") from error
    if not isinstance(value, dict):
        raise CheckError(f"invalid_response:{operation}")
    return value


def utc_window(timezone_name: str, local_date: date) -> tuple[str, str]:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise CheckError(f"invalid_timezone:{timezone_name}") from error
    start = datetime.combine(local_date, time.min, tzinfo=zone).astimezone(timezone.utc)
    next_date = local_date.fromordinal(local_date.toordinal() + 1)
    end = datetime.combine(next_date, time.min, tzinfo=zone).astimezone(timezone.utc)
    return start.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


def selected_date(value: str | None, timezone_name: str) -> date:
    if value:
        return date.fromisoformat(value)
    try:
        return datetime.now(ZoneInfo(timezone_name)).date()
    except ZoneInfoNotFoundError as error:
        raise CheckError(f"invalid_timezone:{timezone_name}") from error


def query_records(data_source_id: str, start: str, end: str, page_size: int) -> dict[str, Any]:
    body = {
        "filter": {"and": [
            {"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": start}},
            {"timestamp": "last_edited_time", "last_edited_time": {"before": end}},
        ]},
        "sorts": [{"timestamp": "last_edited_time", "direction": "ascending"}],
        "page_size": page_size,
        "result_type": "page",
    }
    raw = run_ntn("api", f"/v1/data_sources/{data_source_id}/query", "-X", "POST", "-d", json.dumps(body))
    return parse_json(raw, "query")


def page_markdown(page_id: str) -> str:
    return run_ntn("pages", "get", page_id).strip()


def plain_text(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    return "".join(str(item.get("plain_text", "")) for item in items if isinstance(item, dict)).strip()


def list_comments(page_id: str) -> list[dict[str, str]]:
    response = parse_json(
        run_ntn("api", "/v1/comments", "-X", "GET", f"block_id=={page_id}", "page_size==100"),
        "comments",
    )
    return [
        {"id": str(item.get("id", "")), "text": plain_text(item.get("rich_text"))}
        for item in response.get("results", []) if isinstance(item, dict)
    ]


def template_map(path: Path) -> dict[str, str]:
    value = parse_json(path.read_text(encoding="utf-8"), "template_map")
    mapping = value.get("templates")
    if not isinstance(mapping, dict) or not mapping:
        raise CheckError("template_map_requires_nonempty_templates_object")
    normalized = {
        str(record_type).strip(): str(page_id).strip()
        for record_type, page_id in mapping.items()
        if str(record_type).strip() and str(page_id).strip()
    }
    if not normalized:
        raise CheckError("template_map_requires_nonempty_templates_object")
    return normalized


def record_type(item: dict[str, Any], property_name: str) -> str | None:
    properties = item.get("properties")
    if not isinstance(properties, dict) or not isinstance(properties.get(property_name), dict):
        return None
    value = properties[property_name]
    for kind in ("select", "status"):
        selected = value.get(kind)
        if isinstance(selected, dict) and selected.get("name"):
            return str(selected["name"])
    return None


def fetch(args: argparse.Namespace) -> int:
    if not 1 <= args.page_size <= MAX_PAGE_SIZE:
        raise CheckError(f"page_size_must_be_1_to_{MAX_PAGE_SIZE}")
    local_date = selected_date(args.date, args.timezone)
    start, end = utc_window(args.timezone, local_date)
    response = query_records(args.data_source_id, start, end, args.page_size)
    routing = template_map(args.template_map)
    templates = {page_id: page_markdown(page_id) for page_id in sorted(set(routing.values()))}
    records = []
    for item in response.get("results", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        page_id = str(item["id"])
        kind = record_type(item, args.type_property)
        template_page_id = routing.get(kind or "")
        if not template_page_id:
            records.append({
                "page_id": page_id, "url": item.get("url"),
                "last_edited_time": item.get("last_edited_time"),
                "record_type": kind, "state": "configuration_gap",
                "configuration_gap": "unmapped_template",
            })
            continue
        records.append({
            "page_id": page_id, "url": item.get("url"),
            "last_edited_time": item.get("last_edited_time"),
            "record_type": kind, "template_page_id": template_page_id,
            "markdown": page_markdown(page_id), "comments": list_comments(page_id),
        })
    emit(
        "fetched", local_date=local_date.isoformat(), timezone=args.timezone,
        utc_window={"start": start, "end": end},
        templates={page_id: markdown for page_id, markdown in templates.items()},
        records=records, partial=bool(response.get("has_more")), page_limit=args.page_size,
    )
    return 0


def normalized_missing(items: list[str]) -> list[str]:
    return sorted({" ".join(item.lower().split()) for item in items if item.strip()})


def marker(page_id: str, template_ref: str, missing_items: list[str]) -> str:
    material = json.dumps([page_id, template_ref, normalized_missing(missing_items)], separators=(",", ":"))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"[{MARKER_PREFIX}: {digest}]"


def comment(args: argparse.Namespace) -> int:
    request = parse_json(Path(args.input).read_text(encoding="utf-8"), "comment_input")
    page_id = str(request.get("page_id", "")).strip()
    template_ref = str(request.get("template_ref", "")).strip()
    missing_items = request.get("missing_items")
    body = str(request.get("comment", "")).strip()
    if not page_id or not template_ref or not isinstance(missing_items, list) or not missing_items or not body:
        raise CheckError("comment_input_requires_page_id_template_ref_missing_items_and_comment")
    if not all(isinstance(item, str) for item in missing_items):
        raise CheckError("missing_items_must_be_strings")
    if args.apply and args.comment_policy != "approved":
        raise CheckError("comment_policy_not_approved")
    tag = marker(page_id, template_ref, missing_items)
    if any(tag in existing["text"] for existing in list_comments(page_id)):
        emit("duplicate", page_id=page_id, marker=tag, write=False)
        return 0
    rendered = f"{body}\n\n{tag}"
    if len(rendered) > 2000:
        raise CheckError("comment_exceeds_notion_2000_character_limit")
    if not args.apply:
        emit("proposal", page_id=page_id, marker=tag, comment=rendered, write=False)
        return 0
    payload = {"parent": {"page_id": page_id}, "rich_text": [{"type": "text", "text": {"content": rendered}}]}
    response = parse_json(run_ntn("api", "/v1/comments", "-X", "POST", "-d", json.dumps(payload)), "create_comment")
    emit("posted", page_id=page_id, comment_id=response.get("id"), marker=tag, write=True)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    get = commands.add_parser("fetch")
    get.add_argument("--data-source-id", required=True)
    get.add_argument("--template-map", type=Path, required=True, help="JSON file with a templates object mapping record type to template page ID.")
    get.add_argument("--type-property", default="Type")
    get.add_argument("--timezone", required=True)
    get.add_argument("--date")
    get.add_argument("--page-size", type=int, default=MAX_PAGE_SIZE)
    post = commands.add_parser("comment")
    post.add_argument("--input", type=Path, required=True)
    post.add_argument("--apply", action="store_true")
    post.add_argument("--comment-policy", choices=("proposal-only", "approved"), default="proposal-only")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return fetch(args) if args.command == "fetch" else comment(args)
    except (CheckError, OSError, ValueError) as error:
        detail = str(error)
        if detail == "comment_policy_not_approved":
            state = "policy_blocked"
        elif detail.startswith("template_map_"):
            state = "configuration_gap"
        else:
            state = "source_gap"
        emit(state, error=detail, write=False)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
