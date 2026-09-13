"""Hermes tools backed by the authenticated host Multica CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_MAC_BIN = Path(
    "/Applications/Multica.app/Contents/Resources/app.asar.unpacked/resources/bin/multica"
)


def _binary() -> str | None:
    configured = os.environ.get("MULTICA_BIN", "").strip()
    if configured and Path(configured).is_file():
        return configured
    discovered = shutil.which("multica")
    if discovered:
        return discovered
    return str(DEFAULT_MAC_BIN) if DEFAULT_MAC_BIN.is_file() else None


def _profile_args() -> list[str]:
    profile = os.environ.get("MULTICA_PROFILE", "desktop-api.multica.ai").strip()
    return ["--profile", profile] if profile else []


def _run(arguments: list[str]) -> str:
    binary = _binary()
    if not binary:
        return json.dumps({"error": "multica_cli_missing"})
    mutating = arguments[:2] == ["issue", "create"]
    uncertain = {
        "outcome": "unknown",
        "recovery": "Read back before retrying; do not automatically repeat creation.",
    } if mutating else {}
    try:
        result = subprocess.run(
            [binary, *arguments, *_profile_args(), "--output", "json"],
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "multica_timeout", **uncertain})
    except OSError:
        return json.dumps({"error": "multica_launch_failed"})
    if result.returncode:
        return json.dumps({"error": "multica_command_failed", "exit_code": result.returncode, **uncertain})
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return json.dumps({"error": "multica_output_invalid", **uncertain})
    return json.dumps(payload)


def _list_projects(args: dict[str, Any] | None = None, **_: Any) -> str:
    values = args or {}
    return _run(["project", "list", "--workspace-id", str(values["workspace_id"])])


def _list_issues(args: dict[str, Any] | None = None, **_: Any) -> str:
    values = args or {}
    command = [
        "issue", "list", "--workspace-id", str(values["workspace_id"]),
        "--limit", str(min(max(int(values.get("limit", 100)), 1), 100)),
        "--offset", str(max(int(values.get("offset", 0)), 0)),
    ]
    for key, flag in (("project", "--project"), ("status", "--status"), ("assignee", "--assignee")):
        value = str(values.get(key) or "").strip()
        if value:
            command.extend([flag, value])
    return _run(command)


def _get_issue(args: dict[str, Any] | None = None, **_: Any) -> str:
    values = args or {}
    return _run(["issue", "get", str(values["issue_id"]),
                 "--workspace-id", str(values["workspace_id"])])


def _list_comments(args: dict[str, Any] | None = None, **_: Any) -> str:
    values = args or {}
    return _run(["issue", "comment", "list", str(values["issue_id"]), "--full",
                 "--workspace-id", str(values["workspace_id"])])


def _create_issue(args: dict[str, Any] | None = None, **_: Any) -> str:
    values = args or {}
    command = [
        "issue", "create", "--title", str(values["title"]),
        "--workspace-id", str(values["workspace_id"]),
    ]
    for key, flag in (("description", "--description"), ("project", "--project"), ("assignee", "--assignee"), ("status", "--status"), ("priority", "--priority"), ("due_date", "--due-date")):
        value = str(values.get(key) or "").strip()
        if value:
            command.extend([flag, value])
    return _run(command)


def _available() -> bool:
    return _binary() is not None


def register(ctx) -> None:
    common = {
        "workspace_id": {"type": "string", "description": "Exact Multica workspace ID."},
    }
    ctx.register_tool(
        name="multica_list_projects", toolset="multica", handler=_list_projects,
        check_fn=_available, emoji="📋",
        schema={"name": "multica_list_projects", "description": "List Multica projects in one exact workspace.", "parameters": {"type": "object", "properties": common, "required": ["workspace_id"]}},
    )
    issue_properties = {
        **common,
        "project": {"type": "string"}, "status": {"type": "string"},
        "assignee": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        "offset": {"type": "integer", "minimum": 0},
    }
    ctx.register_tool(
        name="multica_list_issues", toolset="multica", handler=_list_issues,
        check_fn=_available, emoji="📋",
        schema={"name": "multica_list_issues", "description": "List bounded Multica issues with optional project, status, and assignee filters.", "parameters": {"type": "object", "properties": issue_properties, "required": ["workspace_id"]}},
    )
    for name, handler, description in (
        ("multica_get_issue", _get_issue, "Read full details of one discovered Multica issue, retaining raw properties."),
        ("multica_list_comments", _list_comments, "Read all comments on one discovered Multica issue, including full resolved threads without folding or clipping."),
    ):
        ctx.register_tool(
            name=name, toolset="multica", handler=handler,
            check_fn=_available, emoji="📋",
            schema={"name": name, "description": description, "parameters": {
                "type": "object", "properties": {**common, "issue_id": {"type": "string"}},
                "required": ["workspace_id", "issue_id"],
            }},
        )
    create_properties = {
        **common, "title": {"type": "string"}, "description": {"type": "string"},
        "project": {"type": "string"}, "assignee": {"type": "string"},
        "status": {"type": "string"}, "priority": {"type": "string"},
        "due_date": {"type": "string"},
    }
    ctx.register_tool(
        name="multica_create_issue", toolset="multica", handler=_create_issue,
        check_fn=_available, emoji="➕",
        schema={"name": "multica_create_issue", "description": "Create one Multica issue after the caller performs its duplicate check.", "parameters": {"type": "object", "properties": create_properties, "required": ["workspace_id", "title"]}},
    )
