#!/usr/bin/env python3
"""Verify the authenticated Howie profile can perform a read-only Drive call."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


EXPECTED_DRIVE_ENDPOINT = "https://drivemcp.googleapis.com/mcp/v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Howie's authenticated Drive search.")
    parser.add_argument("--profile-home", required=True, type=Path)
    return parser.parse_args()


async def verify(profile_home: Path) -> int:
    from agent.secret_scope import build_profile_secret_scope, reset_secret_scope, set_secret_scope
    from hermes_cli.config import load_config
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override
    from tools.mcp_oauth import HermesTokenStorage
    from tools.mcp_tool import _connect_server
    from hermes_cli.mcp_config import _resolve_mcp_server_config

    home_token = set_hermes_home_override(profile_home)
    secret_token = set_secret_scope(build_profile_secret_scope(profile_home))
    server = None
    try:
        entry = dict((load_config().get("mcp_servers") or {}).get("googledrive") or {})
        if entry.get("url") != EXPECTED_DRIVE_ENDPOINT or entry.get("auth") != "oauth":
            raise RuntimeError("profile does not contain the expected Google Drive OAuth MCP entry")
        if not HermesTokenStorage("googledrive").has_cached_tokens():
            raise RuntimeError("Google Drive is not authorized")
        server = await asyncio.wait_for(_connect_server("googledrive", _resolve_mcp_server_config(entry)), timeout=90)
        result = await asyncio.wait_for(
            server.session.call_tool(
                "search_files",
                arguments={
                    "query": "title = '__howie_oauth_sentinel__'",
                    "pageSize": 1,
                    "excludeContentSnippets": True,
                },
            ),
            timeout=90,
        )
        if result.isError:
            message = " ".join(str(getattr(block, "text", "")) for block in (result.content or [])).strip()
            raise RuntimeError(f"read-only Drive search failed: {message or 'unknown error'}")
        return len(server._tools)
    finally:
        if server is not None:
            await server.shutdown()
        reset_secret_scope(secret_token)
        reset_hermes_home_override(home_token)


def main() -> int:
    profile_home = parse_args().profile_home.expanduser().resolve(strict=False)
    if not profile_home.is_dir() or profile_home.is_symlink():
        raise RuntimeError("--profile-home must be an existing real profile directory")
    tools = asyncio.run(verify(profile_home))
    print(f"VERIFIED authenticated Drive read path with {tools} permitted tools.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Drive access verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
