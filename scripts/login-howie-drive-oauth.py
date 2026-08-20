#!/usr/bin/env python3
"""Complete Google Drive OAuth for the selected Howie Hermes profile.

This is intentionally a one-purpose, operator-present helper. It uses the
same rendered Hermes profile config and token store as the real agent, but
runs the interactive OAuth context inside the connection coroutine. That
keeps a dashboard/background-thread context boundary from turning the login
into an unauthenticated tool-discovery probe.

It never prints a client ID, secret, token, authorization code, or Drive ID.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


EXPECTED_DRIVE_ENDPOINT = "https://drivemcp.googleapis.com/mcp/v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Authorize the official Google Drive MCP for a Howie profile."
    )
    parser.add_argument("--profile-home", required=True, type=Path)
    return parser.parse_args()


async def authorize(profile_home: Path) -> list[str]:
    # Imports stay inside the execution path so --help is usable without a
    # Hermes runtime installed. The active venv supplies these modules.
    from agent.secret_scope import (
        build_profile_secret_scope,
        reset_secret_scope,
        set_secret_scope,
    )
    from hermes_cli.config import load_config
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override
    from tools.mcp_oauth import HermesTokenStorage, force_interactive_oauth
    from tools.mcp_tool import _connect_server
    from hermes_cli.mcp_config import _resolve_mcp_server_config

    home_token = set_hermes_home_override(profile_home)
    secret_token = set_secret_scope(build_profile_secret_scope(profile_home))
    server = None
    try:
        config = load_config()
        entry = dict((config.get("mcp_servers") or {}).get("googledrive") or {})
        if entry.get("url") != EXPECTED_DRIVE_ENDPOINT or entry.get("auth") != "oauth":
            raise RuntimeError("profile does not contain the expected Google Drive OAuth MCP entry")
        entry = _resolve_mcp_server_config(entry)
        if not ((entry.get("oauth") or {}).get("client_id")):
            raise RuntimeError("private Google Drive OAuth credentials are not configured")

        # This needs to wrap the coroutine itself: the native dashboard and
        # CLI currently lose the ContextVar while handing work to an MCP loop.
        # MCPServerTask.start() inherits this task's context when it starts its
        # connection task, which permits the normal provider OAuth browser flow.
        with force_interactive_oauth():
            server = await asyncio.wait_for(_connect_server("googledrive", entry), timeout=315)
        if not HermesTokenStorage("googledrive").has_cached_tokens():
            raise RuntimeError("Google did not persist an OAuth token; authorization was not completed")
        return sorted(str(tool.name) for tool in server._tools)
    finally:
        if server is not None:
            await server.shutdown()
        reset_secret_scope(secret_token)
        reset_hermes_home_override(home_token)


def main() -> int:
    args = parse_args()
    profile_home = args.profile_home.expanduser().resolve(strict=False)
    if not profile_home.is_dir() or profile_home.is_symlink():
        raise RuntimeError("--profile-home must be an existing real profile directory")
    tools = asyncio.run(authorize(profile_home))
    print(f"AUTHORIZED Google Drive MCP with {len(tools)} permitted tools.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Google Drive authorization cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - bounded operator-facing result
        print(f"Google Drive authorization failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
