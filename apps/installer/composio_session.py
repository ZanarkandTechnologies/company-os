"""Provision one restricted Composio session and expose it to Hermes over MCP."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable


API_ORIGIN = "https://backend.composio.dev"
SESSION_API = "/api/v3.1/tool_router/session"
STATE_PATH = Path("state/composio/session.json")
Request = Callable[[str, str, str, dict[str, Any] | None], dict[str, Any]]


class ComposioSessionError(RuntimeError):
    """A redacted Composio provisioning or state failure."""


def _request(
    method: str,
    path: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        API_ORIGIN + path,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ComposioSessionError(f"composio_http_{error.code}") from error
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ComposioSessionError("composio_unavailable") from error
    if not isinstance(result, dict):
        raise ComposioSessionError("composio_response_invalid")
    return result


def _desired(providers: list[dict[str, Any]]) -> dict[str, list[str]]:
    desired: dict[str, set[str]] = {}
    for provider in providers:
        mcp = provider.get("mcp", {})
        if mcp.get("source") != "composio_session":
            continue
        toolkit = str(mcp["toolkit"])
        desired.setdefault(toolkit, set()).update(str(tool) for tool in mcp["tools"])
    return {key: sorted(value) for key, value in sorted(desired.items())}


def _configuration_hash(toolkits: dict[str, list[str]]) -> str:
    encoded = json.dumps(toolkits, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _read_state(profile_home: Path) -> dict[str, Any]:
    try:
        payload = json.loads((profile_home / STATE_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_state(profile_home: Path, state: dict[str, Any]) -> Path:
    destination = profile_home / STATE_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(destination.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".composio-", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def ensure_session(
    profile_home: Path,
    providers: list[dict[str, Any]],
    api_key: str,
    *,
    request: Request = _request,
) -> dict[str, Any]:
    """Create or reuse one fixed-tool Composio MCP session for this profile."""
    if not api_key.strip():
        raise ComposioSessionError("composio_api_key_missing")
    toolkits = _desired(providers)
    if not toolkits:
        raise ComposioSessionError("composio_toolkits_missing")
    desired_hash = _configuration_hash(toolkits)
    state = _read_state(profile_home)
    if (
        state.get("configuration_sha256") == desired_hash
        and isinstance(state.get("session_id"), str)
        and isinstance(state.get("mcp_url"), str)
    ):
        request(
            "GET",
            f"{SESSION_API}/{state['session_id']}",
            api_key,
            None,
        )
        return state

    user_id = str(state.get("user_id") or f"company-os-{uuid.uuid4().hex}")
    enabled_tools = sorted({tool for tools in toolkits.values() for tool in tools})
    payload = {
        "user_id": user_id,
        "toolkits": {"enable": sorted(toolkits)},
        "tools": {
            toolkit: {"enable": tools} for toolkit, tools in toolkits.items()
        },
        "manage_connections": {
            "enable": True,
            "enable_wait_for_connections": False,
            "enable_connection_removal": True,
        },
        "workbench": {"enable": False, "enable_proxy_execution": False},
        "preload": {"tools": enabled_tools},
    }
    result = request("POST", SESSION_API, api_key, payload)
    session_id = result.get("session_id")
    mcp = result.get("mcp")
    mcp_url = mcp.get("url") if isinstance(mcp, dict) else None
    if not isinstance(session_id, str) or not isinstance(mcp_url, str):
        raise ComposioSessionError("composio_session_response_invalid")
    parsed = urllib.parse.urlsplit(mcp_url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (
        hostname == "composio.dev" or hostname.endswith(".composio.dev")
    ):
        raise ComposioSessionError("composio_mcp_url_invalid")
    state = {
        "schema_version": 1,
        "session_id": session_id,
        "user_id": user_id,
        "mcp_url": mcp_url,
        "toolkits": toolkits,
        "configuration_sha256": desired_hash,
    }
    _write_state(profile_home, state)
    return state


def create_connect_link(
    state: dict[str, Any],
    toolkit: str,
    api_key: str,
    *,
    request: Request = _request,
) -> str:
    session_id = state.get("session_id")
    if not isinstance(session_id, str) or toolkit not in state.get("toolkits", {}):
        raise ComposioSessionError("composio_session_state_invalid")
    result = request(
        "POST",
        f"{SESSION_API}/{session_id}/link",
        api_key,
        {"toolkit": toolkit},
    )
    url = result.get("redirect_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ComposioSessionError("composio_connect_link_invalid")
    return url


def connected_toolkits(
    state: dict[str, Any],
    api_key: str,
    *,
    request: Request = _request,
) -> set[str]:
    """Return configured toolkits whose connected account is active."""
    session_id = state.get("session_id")
    toolkits = state.get("toolkits")
    if not isinstance(session_id, str) or not isinstance(toolkits, dict):
        raise ComposioSessionError("composio_session_state_invalid")
    names = ",".join(sorted(toolkits))
    result = request(
        "GET",
        f"{SESSION_API}/{session_id}/toolkits"
        f"?limit=50&is_connected=true&toolkits={names}",
        api_key,
        None,
    )
    items = result.get("items")
    if not isinstance(items, list):
        raise ComposioSessionError("composio_toolkits_response_invalid")
    connected: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        account = item.get("connected_account")
        if (
            isinstance(account, dict)
            and str(account.get("status", "")).upper() == "ACTIVE"
            and isinstance(item.get("slug"), str)
        ):
            connected.add(str(item["slug"]).lower())
    return connected
