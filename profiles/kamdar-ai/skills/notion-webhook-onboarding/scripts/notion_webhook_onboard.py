#!/usr/bin/env python3
"""Deterministic ngrok onboarding phases for the Hermes Notion connector."""

from __future__ import annotations

import argparse
import getpass
import grp
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from pathlib import Path
from typing import Any

NGROK_LOGIN_URL = "https://dashboard.ngrok.com/get-started/your-authtoken"
NOTION_INTEGRATIONS_URL = "https://www.notion.so/profile/integrations"
NGROK_KEY_URL = "https://ngrok-agent.s3.amazonaws.com/ngrok.asc"
NGROK_REPOSITORY = "deb https://ngrok-agent.s3.amazonaws.com bookworm main\n"
NGROK_SERVICE = "hermes-notion-ngrok.service"
WEBHOOK_PATH = "/notion/webhook"
LOCAL_ORIGIN = "http://127.0.0.1:8645"
ALLOWED_SECURE_KEYS = {"NGROK_AUTHTOKEN", "NOTION_TOKEN", "OPENROUTER_API_KEY"}


class OnboardError(RuntimeError):
    """A safe operator-facing onboarding failure."""


def emit(state: str, **values: Any) -> dict[str, Any]:
    return {"state": state, **values}


def profile_root() -> Path:
    override = os.getenv("HERMES_PROFILE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[3]


def runtime_identity(root: Path) -> tuple[str, str, Path]:
    owner = pwd.getpwuid(root.stat().st_uid)
    group = grp.getgrgid(owner.pw_gid)
    return owner.pw_name, group.gr_name, Path(owner.pw_dir)


def state_path(root: Path) -> Path:
    return root / "state" / "notion-webhook.json"


def read_state(root: Path) -> dict[str, Any]:
    defaults = {
        "verification_token": "",
        "workspace_id": "",
        "seen": {},
        "reply_targets": {},
        "last_reply": {},
    }
    try:
        value = json.loads(state_path(root).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return defaults
    if not isinstance(value, dict):
        return defaults
    return {**defaults, **value}


def reset_onboarding_state(root: Path) -> None:
    """Start a fresh subscription attempt without accepting prior proof."""
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "verification_token": "",
        "workspace_id": "",
        "seen": {},
        "reply_targets": {},
        "last_reply": {},
    }
    handle, temporary = tempfile.mkstemp(prefix="notion-webhook-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(value, stream, separators=(",", ":"))
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run(
    argv: list[str],
    *,
    input_text: str | None = None,
    check: bool = True,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            argv,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise OnboardError(f"command failed to run: {argv[0]}: {error}") from error
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else f"exit {result.returncode}"
        raise OnboardError(f"{argv[0]} failed: {message}")
    return result


def require_command(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise OnboardError(f"required command is missing: {name}")
    return path


def doppler_secret_names(root: Path) -> set[str]:
    doppler = require_command("doppler")
    result = run([doppler, "secrets", "--only-names", "--json", "--scope", str(root)])
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise OnboardError("Doppler returned invalid secret-name JSON") from error
    if isinstance(value, dict):
        return {str(name) for name in value}
    if isinstance(value, list):
        return {str(item.get("name") if isinstance(item, dict) else item) for item in value}
    raise OnboardError("Doppler returned an unsupported secret-name shape")


def set_doppler_values(root: Path, values: dict[str, str]) -> None:
    doppler = require_command("doppler")
    assignments = [f"{name}={value}" for name, value in values.items()]
    run([doppler, "secrets", "set", *assignments, "--silent", "--scope", str(root)])


def get_public_doppler_value(root: Path, name: str) -> str:
    if name not in {"NOTION_WEBHOOK_PUBLIC_URL", "NOTION_COMMENT_TRIGGER"}:
        raise OnboardError("refusing to read a credential-bearing Doppler value")
    doppler = require_command("doppler")
    result = run(
        [doppler, "secrets", "get", name, "--plain", "--scope", str(root)],
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def parse_page_id(value: str) -> str:
    decoded = urllib.parse.unquote(value.strip())
    matches = re.findall(
        r"(?<![0-9a-fA-F])([0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})(?![0-9a-fA-F])",
        decoded,
    )
    if not matches:
        raise OnboardError("the Notion root-page URL does not contain a page ID")
    return str(uuid.UUID(matches[-1]))


def browser_open(target: str) -> dict[str, Any]:
    urls = {"ngrok": NGROK_LOGIN_URL, "notion": NOTION_INTEGRATIONS_URL}
    url = urls[target]
    headless_ssh = bool(os.getenv("SSH_CONNECTION")) and not (
        os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY")
    )
    opened = False
    if not headless_ssh:
        try:
            opened = bool(webbrowser.open(url, new=2))
        except webbrowser.Error:
            opened = False
    return emit(
        "human_required",
        action=f"login_{target}",
        browser_opened=opened,
        url=url,
        next_action=(
            "Complete login in the opened browser, then resume onboarding."
            if opened
            else "Open the clickable URL, complete login, then resume onboarding."
        ),
    )


def local_health() -> bool:
    try:
        with urllib.request.urlopen(f"{LOCAL_ORIGIN}/notion/health", timeout=3) as response:
            value = json.loads(response.read().decode("utf-8"))
            return response.status == 200 and bool(value.get("ok"))
    except (OSError, ValueError, urllib.error.URLError):
        return False


def ngrok_public_url() -> str:
    try:
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=3) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return ""
    tunnels = value.get("tunnels") if isinstance(value, dict) else []
    for tunnel in tunnels if isinstance(tunnels, list) else []:
        public = str(tunnel.get("public_url") or "") if isinstance(tunnel, dict) else ""
        config = tunnel.get("config") if isinstance(tunnel, dict) and isinstance(tunnel.get("config"), dict) else {}
        upstream = str(config.get("addr") or tunnel.get("forwards_to") or "") if isinstance(tunnel, dict) else ""
        if public.startswith("https://") and upstream.rstrip("/").endswith(":8645"):
            return public.rstrip("/")
    return ""


def privileged(argv: list[str], *, timeout: int = 300) -> None:
    if os.geteuid() == 0:
        run(argv, timeout=timeout)
        return
    sudo = require_command("sudo")
    run([sudo, *argv], timeout=timeout)


def install_ngrok() -> str:
    existing = shutil.which("ngrok")
    if existing:
        return existing
    if sys.platform != "linux":
        raise OnboardError("automatic ngrok installation currently supports Linux only")
    require_command("curl")
    require_command("apt-get")
    with tempfile.TemporaryDirectory(prefix="hermes-notion-ngrok-") as directory:
        key = Path(directory) / "ngrok.asc"
        repo = Path(directory) / "ngrok.list"
        run(["curl", "-fsSL", NGROK_KEY_URL, "-o", str(key)])
        repo.write_text(NGROK_REPOSITORY, encoding="utf-8")
        privileged(["install", "-m", "0644", str(key), "/etc/apt/trusted.gpg.d/ngrok.asc"])
        privileged(["install", "-m", "0644", str(repo), "/etc/apt/sources.list.d/ngrok.list"])
    privileged(["apt-get", "update"], timeout=600)
    privileged(["apt-get", "install", "-y", "ngrok"], timeout=600)
    return require_command("ngrok")


def ngrok_unit(root: Path, ngrok: str, doppler: str) -> str:
    user, group, home = runtime_identity(root)
    path = f"{home}/.local/bin:{home}/.hermes/bin:/usr/local/bin:/usr/bin:/bin"
    return f"""[Unit]
Description=Hermes Notion ngrok endpoint
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
Group={group}
Environment=HOME={home}
Environment=PATH={path}
ExecStart={doppler} run --scope {root} -- {ngrok} http {LOCAL_ORIGIN} --log=stdout --log-format=json
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""


def install_ngrok_service(root: Path, ngrok: str) -> None:
    doppler = require_command("doppler")
    content = ngrok_unit(root, ngrok, doppler)
    with tempfile.NamedTemporaryFile("w", prefix="hermes-notion-ngrok-", delete=False) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    try:
        privileged(["install", "-m", "0644", str(temporary), f"/etc/systemd/system/{NGROK_SERVICE}"])
    finally:
        temporary.unlink(missing_ok=True)
    privileged(["systemctl", "daemon-reload"])
    privileged(["systemctl", "enable", "--now", NGROK_SERVICE])


def detect_hermes_service(explicit: str = "") -> str:
    if explicit:
        if not re.fullmatch(r"[A-Za-z0-9_.@-]+\.service", explicit):
            raise OnboardError("invalid Hermes systemd service name")
        return explicit
    systemctl = require_command("systemctl")
    result = run(
        [systemctl, "list-units", "--type=service", "--all", "--no-legend", "--plain"],
        check=False,
    )
    units = []
    for line in result.stdout.splitlines():
        name = line.split(maxsplit=1)[0] if line.split() else ""
        if name.endswith(".service") and "hermes" in name.casefold() and name != NGROK_SERVICE:
            units.append(name)
    active = [name for name in units if " active " in f" {next((line for line in result.stdout.splitlines() if line.startswith(name)), '')} "]
    candidates = active or units
    if len(candidates) != 1:
        raise OnboardError(
            "could not select one Hermes systemd service; rerun configure with --hermes-service NAME.service"
        )
    return candidates[0]


def restart_service(name: str) -> None:
    privileged(["systemctl", "restart", name])


def wait_for_ngrok(seconds: int = 30) -> str:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        public = ngrok_public_url()
        if public:
            return public
        time.sleep(1)
    raise OnboardError("ngrok started without exposing an HTTPS endpoint")


def webhook_reachable(endpoint: str) -> bool:
    request = urllib.request.Request(endpoint, method="GET")
    try:
        urllib.request.urlopen(request, timeout=8)
    except urllib.error.HTTPError as error:
        return error.code == 405
    except urllib.error.URLError:
        return False
    return False


def preflight(root: Path) -> dict[str, Any]:
    if sys.platform != "linux" or not Path("/run/systemd/system").exists():
        return emit(
            "blocked",
            blocker="linux_systemd_required",
            next_action="Run this Hermes skill on the Linux VPS that will host the webhook.",
        )
    if not (root / "plugins" / "platforms" / "notion" / "plugin.yaml").is_file():
        return emit(
            "blocked",
            blocker="notion_connector_missing",
            next_action="Install a Hermes profile with the Notion connector, then rerun preflight.",
        )
    missing_commands = [name for name in ("doppler", "systemctl") if not shutil.which(name)]
    if missing_commands:
        return emit(
            "blocked",
            blocker="missing_commands",
            missing=missing_commands,
            next_action="Install the missing prerequisite before onboarding.",
        )
    try:
        names = doppler_secret_names(root)
    except OnboardError as error:
        return emit("blocked", blocker="doppler_scope", detail=str(error), next_action="Authenticate Doppler for this profile.")
    missing_secrets = sorted({"NGROK_AUTHTOKEN", "NOTION_TOKEN", "OPENROUTER_API_KEY"} - names)
    if missing_secrets:
        return emit(
            "human_required",
            action="configure_credentials",
            missing_secret_names=missing_secrets,
            login_urls={"ngrok": NGROK_LOGIN_URL, "notion": NOTION_INTEGRATIONS_URL},
            next_action="Use open-login and secure-set for each missing credential.",
        )
    if not local_health():
        return emit(
            "blocked",
            blocker="hermes_notion_listener",
            hermes_health=False,
            next_action=f"Start the existing Hermes Notion listener at {LOCAL_ORIGIN}, then rerun preflight.",
        )
    return emit(
        "ready",
        ingress="ngrok",
        hermes_health=True,
        ngrok_installed=bool(shutil.which("ngrok")),
        profile=str(root),
        next_action="Run configure with the Notion root-page URL.",
    )


def configure(
    root: Path,
    root_page_url: str,
    mention: str,
    hermes_service: str,
    dry_run: bool,
) -> dict[str, Any]:
    page_id = parse_page_id(root_page_url)
    mention = mention.strip() or "@vishanai"
    if not mention.startswith("@") or any(character.isspace() for character in mention):
        raise OnboardError("the Notion mention must begin with @ and contain no spaces")
    settings = {
        "NOTION_ROOT_PAGE_ID": page_id,
        "NOTION_COMMENT_TRIGGER": mention,
        "NOTION_ENABLE_WRITES": "false",
        "NOTION_ALLOW_ALL_WORKSPACES": "true",
    }
    if dry_run:
        return emit(
            "ready",
            dry_run=True,
            ingress="ngrok",
            profile=str(root),
            root_page_id=page_id,
            mention=mention,
            comment_replies=True,
            page_property_writes=False,
            planned_settings=settings,
            next_action="Run configure without --dry-run on the VPS.",
        )
    if sys.platform != "linux" or not Path("/run/systemd/system").exists():
        raise OnboardError("ngrok onboarding requires a Linux VPS running systemd")
    names = doppler_secret_names(root)
    missing = sorted({"NGROK_AUTHTOKEN", "NOTION_TOKEN", "OPENROUTER_API_KEY"} - names)
    if missing:
        return emit(
            "human_required",
            action="configure_credentials",
            missing_secret_names=missing,
            next_action="Use open-login and secure-set, then rerun configure.",
        )
    if not local_health():
        return emit(
            "blocked",
            blocker="hermes_notion_listener",
            next_action=f"Start the existing Hermes Notion listener at {LOCAL_ORIGIN}, then rerun configure.",
        )
    reset_onboarding_state(root)
    ngrok = install_ngrok()
    set_doppler_values(
        root,
        {
            **settings,
            "NOTION_ALLOWED_DATA_SOURCES": "",
            "NOTION_ALLOWED_WORKSPACES": "",
        },
    )
    install_ngrok_service(root, ngrok)
    public = wait_for_ngrok()
    endpoint = f"{public}{WEBHOOK_PATH}"
    set_doppler_values(root, {"NOTION_WEBHOOK_PUBLIC_URL": endpoint})
    service = detect_hermes_service(hermes_service)
    restart_service(service)
    if not webhook_reachable(endpoint):
        raise OnboardError("the ngrok endpoint did not reach the Hermes webhook")
    return emit(
        "human_required",
        action="create_notion_subscription",
        endpoint=endpoint,
        event_type="comment.created",
        browser_url=NOTION_INTEGRATIONS_URL,
        browser_opened=browser_open("notion")["browser_opened"],
        next_action="Create the Notion webhook subscription, then run verification.",
    )


def verification(root: Path) -> dict[str, Any]:
    state = read_state(root)
    token = str(state.get("verification_token") or "")
    if not token:
        return emit(
            "human_required",
            action="wait_for_verification_token",
            endpoint=get_public_doppler_value(root, "NOTION_WEBHOOK_PUBLIC_URL"),
            verification_token_captured=False,
            next_action="Use Resend token in Notion, then poll verification again.",
        )
    return emit(
        "human_required",
        action="paste_verification_token",
        verification_token_captured=True,
        verification_token=token,
        next_action="Paste this one-time token into Notion, verify the subscription, then run discover.",
    )


def notion_request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        raise OnboardError("NOTION_TOKEN is not available in the Doppler runtime")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        f"https://api.notion.com/v1{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": os.getenv("NOTION_API_VERSION", "2026-03-11"),
            "Content-Type": "application/json",
            "User-Agent": "hermes-notion-onboarding/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise OnboardError(f"Notion API returned HTTP {error.code} for {path}") from error
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        raise OnboardError(f"Notion API request failed for {path}: {error}") from error
    if not isinstance(value, dict):
        raise OnboardError("Notion API returned an unsupported response")
    return value


def discover_internal(root_page_id: str) -> dict[str, Any]:
    notion_request("GET", f"/pages/{root_page_id}")
    cursor = ""
    sources: list[dict[str, str]] = []
    while True:
        body: dict[str, Any] = {
            "filter": {"property": "object", "value": "data_source"},
            "page_size": 100,
        }
        if cursor:
            body["start_cursor"] = cursor
        page = notion_request("POST", "/search", body)
        for item in page.get("results", []):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            title = "".join(
                str(part.get("plain_text") or "")
                for part in item.get("title", [])
                if isinstance(part, dict)
            ).strip()
            sources.append({"id": str(item["id"]), "title": title or "Untitled data source"})
        if not page.get("has_more"):
            break
        cursor = str(page.get("next_cursor") or "")
        if not cursor:
            break
    return {"sources": sources}


def discover(root: Path, hermes_service: str) -> dict[str, Any]:
    doppler = require_command("doppler")
    page_id = get_doppler_value_via_runtime(root, "NOTION_ROOT_PAGE_ID")
    result = run(
        [
            doppler,
            "run",
            "--scope",
            str(root),
            "--",
            sys.executable,
            str(Path(__file__).resolve()),
            "_discover-internal",
            "--root-page-id",
            page_id,
        ],
        timeout=120,
    )
    try:
        value = json.loads(result.stdout)
        sources = value["sources"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise OnboardError("data-source discovery returned invalid JSON") from error
    identifiers = [str(item["id"]) for item in sources if isinstance(item, dict) and item.get("id")]
    if not identifiers:
        return emit(
            "blocked",
            blocker="no_shared_data_sources",
            next_action="Share at least one ticket database with the Notion connection, then rerun discover.",
        )
    set_doppler_values(root, {"NOTION_ALLOWED_DATA_SOURCES": ",".join(identifiers)})
    restart_service(detect_hermes_service(hermes_service))
    return emit(
        "ready",
        discovered_table_count=len(identifiers),
        discovered_tables=[str(item.get("title") or "Untitled data source") for item in sources],
        next_action="Leave one @vishanai test comment, then run finalize.",
    )


def get_doppler_values_via_runtime(root: Path, names: set[str]) -> dict[str, str]:
    allowed = {
        "NOTION_ROOT_PAGE_ID",
        "NOTION_ALLOWED_DATA_SOURCES",
        "NOTION_ALLOWED_WORKSPACES",
        "NOTION_ALLOW_ALL_WORKSPACES",
    }
    if not names or not names <= allowed:
        raise OnboardError("unsupported runtime setting lookup")
    doppler = require_command("doppler")
    requested = sorted(names)
    expression = "import json,os; print(json.dumps({name: os.getenv(name, '') for name in " + repr(requested) + "}))"
    result = run(
        [doppler, "run", "--scope", str(root), "--", sys.executable, "-c", expression]
    )
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise OnboardError("Doppler returned invalid runtime-setting JSON") from error
    if not isinstance(value, dict):
        raise OnboardError("Doppler returned an unsupported runtime-setting shape")
    return {name: str(value.get(name) or "") for name in requested}


def get_doppler_value_via_runtime(root: Path, name: str) -> str:
    value = get_doppler_values_via_runtime(root, {name})[name]
    if not value:
        raise OnboardError(f"{name} is not configured")
    return value


def finalize(root: Path, hermes_service: str) -> dict[str, Any]:
    state = read_state(root)
    workspace = str(state.get("workspace_id") or "")
    last_reply = state.get("last_reply") if isinstance(state.get("last_reply"), dict) else {}
    if not workspace:
        return emit(
            "human_required",
            action="leave_test_comment",
            workspace_locked=False,
            reply_observed=False,
            next_action="Leave one harmless comment beginning with the configured mention, then poll finalize again.",
        )
    if not last_reply.get("message_id"):
        return emit(
            "human_required",
            action="wait_for_reply",
            workspace_locked=False,
            reply_observed=False,
            next_action="Hermes received the workspace; wait for the Notion reply and poll finalize again.",
        )
    set_doppler_values(
        root,
        {
            "NOTION_ALLOWED_WORKSPACES": workspace,
            "NOTION_ALLOW_ALL_WORKSPACES": "false",
        },
    )
    service = detect_hermes_service(hermes_service)
    restart_service(service)
    return emit(
        "ready",
        endpoint=get_public_doppler_value(root, "NOTION_WEBHOOK_PUBLIC_URL"),
        verification_token_captured=bool(state.get("verification_token")),
        workspace_locked=True,
        reply_observed=True,
        next_action="Notion webhook onboarding is complete.",
    )


def status(root: Path) -> dict[str, Any]:
    state = read_state(root)
    names: set[str] = set()
    doppler_ok = False
    try:
        names = doppler_secret_names(root)
        doppler_ok = True
    except OnboardError:
        pass
    workspace = str(state.get("workspace_id") or "")
    last_reply = state.get("last_reply") if isinstance(state.get("last_reply"), dict) else {}
    endpoint = get_public_doppler_value(root, "NOTION_WEBHOOK_PUBLIC_URL") if doppler_ok else ""
    runtime_settings: dict[str, str] = {}
    if doppler_ok:
        try:
            runtime_settings = get_doppler_values_via_runtime(
                root,
                {
                    "NOTION_ALLOWED_DATA_SOURCES",
                    "NOTION_ALLOWED_WORKSPACES",
                    "NOTION_ALLOW_ALL_WORKSPACES",
                },
            )
        except OnboardError:
            pass
    data_sources_configured = bool(runtime_settings.get("NOTION_ALLOWED_DATA_SOURCES", "").strip())
    allowed_workspaces = {
        item.strip()
        for item in runtime_settings.get("NOTION_ALLOWED_WORKSPACES", "").split(",")
        if item.strip()
    }
    allow_all = runtime_settings.get("NOTION_ALLOW_ALL_WORKSPACES", "").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }
    workspace_locked = bool(workspace) and workspace in allowed_workspaces and not allow_all
    hermes_healthy = local_health()
    public_ngrok = ngrok_public_url()
    ready = all(
        [
            hermes_healthy,
            public_ngrok,
            endpoint,
            state.get("verification_token"),
            data_sources_configured,
            workspace_locked,
            last_reply.get("message_id"),
        ]
    )
    return emit(
        "ready" if ready else "human_required",
        endpoint=endpoint,
        hermes_health=hermes_healthy,
        ngrok_online=bool(public_ngrok),
        verification_token_captured=bool(state.get("verification_token")),
        data_sources_configured=data_sources_configured,
        workspace_locked=workspace_locked,
        reply_observed=bool(last_reply.get("message_id")),
        next_action="Onboarding is complete." if ready else "Resume the first incomplete onboarding phase.",
    )


def secure_set(root: Path, key: str) -> dict[str, Any]:
    if key not in ALLOWED_SECURE_KEYS:
        raise OnboardError("secure-set only accepts onboarding credential names")
    if not sys.stdin.isatty():
        return emit(
            "human_required",
            action="interactive_terminal_required",
            secret_name=key,
            next_action="Open the Hermes terminal and rerun secure-set; never paste the value into chat.",
        )
    value = getpass.getpass(f"{key}: ").strip()
    if not value:
        raise OnboardError(f"{key} was empty")
    doppler = require_command("doppler")
    run(
        [doppler, "secrets", "set", key, "--silent", "--scope", str(root)],
        input_text=f"{value}\n",
    )
    return emit("ready", secret_name=key, configured=True, next_action="Resume preflight.")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--profile-dir", default="", help=argparse.SUPPRESS)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight")
    opened = commands.add_parser("open-login")
    opened.add_argument("target", choices=["ngrok", "notion"])
    secured = commands.add_parser("secure-set")
    secured.add_argument("key", choices=sorted(ALLOWED_SECURE_KEYS))
    configured = commands.add_parser("configure")
    configured.add_argument("--root-page-url", required=True)
    configured.add_argument("--mention", required=True)
    configured.add_argument("--hermes-service", default="")
    configured.add_argument("--dry-run", action="store_true")
    commands.add_parser("verification")
    discovered = commands.add_parser("discover")
    discovered.add_argument("--hermes-service", default="")
    finalized = commands.add_parser("finalize")
    finalized.add_argument("--hermes-service", default="")
    commands.add_parser("status")
    internal = commands.add_parser("_discover-internal", help=argparse.SUPPRESS)
    internal.add_argument("--root-page-id", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.profile_dir).expanduser().resolve() if args.profile_dir else profile_root()
    try:
        if args.command == "preflight":
            value = preflight(root)
        elif args.command == "open-login":
            value = browser_open(args.target)
        elif args.command == "secure-set":
            value = secure_set(root, args.key)
        elif args.command == "configure":
            value = configure(root, args.root_page_url, args.mention, args.hermes_service, args.dry_run)
        elif args.command == "verification":
            value = verification(root)
        elif args.command == "discover":
            value = discover(root, args.hermes_service)
        elif args.command == "finalize":
            value = finalize(root, args.hermes_service)
        elif args.command == "status":
            value = status(root)
        elif args.command == "_discover-internal":
            value = discover_internal(args.root_page_id)
        else:
            raise OnboardError("unsupported onboarding command")
    except OnboardError as error:
        value = emit("blocked", blocker="onboarding_error", detail=str(error), next_action="Fix this blocker and rerun the same phase.")
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 1 if value.get("state") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
