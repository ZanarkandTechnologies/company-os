#!/usr/bin/env python3
"""Create the synthetic, fake-only Howie acceptance fixture in Google Drive.

This script uses the exact OAuth token/configuration owned by the ``howie-ai``
Hermes profile. It creates a single top-level synthetic folder and a handful
of text source files below it, then writes only the root ID and allowed titles
to the profile-private fixture manifest. It deliberately never searches or
reads pre-existing Drive data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_DRIVE_ENDPOINT = "https://drivemcp.googleapis.com/mcp/v1"
FOLDER_MIME = "application/vnd.google-apps.folder"

FIXTURE_FILES = (
    (
        "01 Meetings",
        "Aurora Lithium — weekly meeting notes (fictional)",
        """# Aurora Lithium weekly operating review — fictional\n\nThis is synthetic acceptance data for the Howie AI demo.\n\nDecisions\n- Prepare a geology review using the approved fictional basin facts.\n- Finance must confirm the base price case before the 13-week cash forecast.\n- Operations must choose the priority risk before the operating-risk brief.\n- The weekly operating pack depends on approved geology and forecast outputs.\n\nNo real company, reserve, financial, or personnel data is represented here.\n""",
    ),
    (
        "02 Geology",
        "Aurora Basin — approved fictional source facts",
        """# Aurora Basin — approved fictional source facts\n\nSynthetic source only.\n- Location: Pilbara, Western Australia (fictional project context)\n- Commodity: lithium\n- Conceptual resource: 12.8 Mt at 1.42% Li2O\n- Completed drill holes: 64\n- Data date: 2026-08-08\n\nUse as a traceable mock input only. Request technical review before treating any output as approved.\n""",
    ),
    (
        "03 Finance",
        "Aurora — fictional cash forecast assumptions",
        """# Aurora — fictional cash forecast assumptions\n\nSynthetic planning input only.\n- Starting cash: USD 4.2m\n- Illustrative funding target: USD 12.0m\n- Price case: pending finance confirmation\n\nDo not use for investment, accounting, or decision-making.\n""",
    ),
    (
        "04 Fundraising",
        "Aurora — fictional investor narrative inputs",
        """# Aurora — fictional investor narrative inputs\n\nSynthetic narrative frame only.\n- Stage: early technical validation\n- Evidence: fictional geology source facts\n- Funding purpose: fictional drilling, studies, and working capital\n\nA reviewer must approve every claim before external use.\n""",
    ),
    (
        "05 Compliance",
        "Aurora — fictional compliance checklist",
        """# Aurora — fictional compliance checklist\n\nSynthetic workflow checklist, not legal advice.\n- Confirm fictional permit register owner\n- Confirm fictional environmental evidence owner\n- Record outstanding review and due date\n\nCompliance reviewer approval is required before any status is marked complete.\n""",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed fake-only Drive data for Howie AI.")
    parser.add_argument("--profile-home", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    return parser.parse_args()


def write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".howie-drive-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


async def seed(profile_home: Path) -> tuple[str, list[str]]:
    from agent.secret_scope import (
        build_profile_secret_scope,
        reset_secret_scope,
        set_secret_scope,
    )
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
            raise RuntimeError("Google Drive is not authorized; run login-howie-drive-oauth.py first")
        entry = _resolve_mcp_server_config(entry)
        server = await asyncio.wait_for(_connect_server("googledrive", entry), timeout=90)

        async def create(arguments: dict[str, Any]) -> dict[str, Any]:
            result = await asyncio.wait_for(server.session.call_tool("create_file", arguments=arguments), timeout=90)
            if result.isError:
                message = " ".join(
                    str(getattr(block, "text", "")) for block in (result.content or [])
                ).strip()
                raise RuntimeError(
                    "Drive rejected synthetic fixture creation"
                    + (f": {message}" if message else "")
                )
            raw = getattr(result, "structuredContent", None)
            if isinstance(raw, dict):
                return raw
            text = "\n".join(str(getattr(block, "text", "")) for block in (result.content or []))
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise RuntimeError("Drive returned an unreadable fixture receipt") from exc

        root = await create({"title": "Howie AI — Aurora Lithium POC (synthetic)", "mimeType": FOLDER_MIME})
        root_id = root.get("id") or root.get("file", {}).get("id")
        if not isinstance(root_id, str) or not root_id:
            raise RuntimeError("Drive did not return a root folder receipt")

        folders: dict[str, str] = {}
        for folder_title, _, _ in FIXTURE_FILES:
            folder = await create({"title": folder_title, "mimeType": FOLDER_MIME, "parentId": root_id})
            folder_id = folder.get("id") or folder.get("file", {}).get("id")
            if not isinstance(folder_id, str) or not folder_id:
                raise RuntimeError("Drive did not return a child-folder receipt")
            folders[folder_title] = folder_id

        titles: list[str] = []
        for folder_title, title, content in FIXTURE_FILES:
            file_result = await create({
                "title": title,
                "textContent": content,
                "contentMimeType": "text/markdown",
                "disableConversionToGoogleType": True,
                "parentId": folders[folder_title],
            })
            file_id = file_result.get("id") or file_result.get("file", {}).get("id")
            if not isinstance(file_id, str) or not file_id:
                raise RuntimeError("Drive did not return a source-file receipt")
            titles.append(title)
        return root_id, titles
    finally:
        if server is not None:
            await server.shutdown()
        reset_secret_scope(secret_token)
        reset_hermes_home_override(home_token)


def main() -> int:
    args = parse_args()
    profile_home = args.profile_home.expanduser().resolve(strict=False)
    workspace = args.workspace.expanduser().resolve(strict=False)
    if not profile_home.is_dir() or profile_home.is_symlink():
        raise RuntimeError("--profile-home must be an existing real profile directory")
    if not workspace.is_dir() or workspace.is_symlink():
        raise RuntimeError("--workspace must be an existing real workspace directory")
    root_id, titles = asyncio.run(seed(profile_home))
    manifest_path = workspace / "drive" / "fixture-manifest.private.json"
    write_private_json(manifest_path, {
        "schema_version": 1,
        "fixture_kind": "fake-company-data",
        "approved_root_id": root_id,
        "approved_root_label": "Aurora Lithium fake-data root",
        "allowed_fixture_titles": titles,
    })
    print(f"SEEDED fake-only Drive fixture with {len(titles)} source files.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - bounded operator-facing result
        print(f"Drive fixture seed failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
