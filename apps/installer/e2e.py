#!/usr/bin/env python3
"""Operate the real Company OS Compose setup path in isolated Docker resources."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "compose.yaml"
OVERRIDE = ROOT / "apps" / "installer" / "compose.e2e.yaml"
PROTECTED_VOLUME = "company-os-hermes-data"
PROTECTED_PORT = 9119


class SetupE2EError(RuntimeError):
    pass


def _free_port() -> int:
    with socket.socket() as stream:
        stream.bind(("127.0.0.1", 0))
        return int(stream.getsockname()[1])


def _run_id() -> str:
    return time.strftime("%Y%m%d%H%M%S", time.gmtime()) + "-" + uuid.uuid4().hex[:8]


def _redact(value: str) -> str:
    value = re.sub(r"(?i)(token|secret|password|api[_-]?key)=([^\s]+)", r"\1=[redacted]", value)
    value = re.sub(r"Bearer\s+[A-Za-z0-9._~+/-]+", "Bearer [redacted]", value)
    return value[-12000:]


class ComposeRun:
    def __init__(self, *, run_id: str, port: int, receipt: Path, keep: bool) -> None:
        self.run_id = run_id
        self.project = f"company-os-e2e-{run_id}".lower()
        self.volume = f"company-os-e2e-{run_id}-data".lower()
        self.port = port
        self.receipt_path = receipt
        self.keep = keep
        self.cleanup_state = "preserved_for_inspection" if keep else "pending"
        self.events: list[dict[str, Any]] = []
        self.started = time.time()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "COMPANY_OS_E2E_PORT": str(port),
                "COMPANY_OS_E2E_VOLUME": self.volume,
            }
        )

    @property
    def base(self) -> list[str]:
        return [
            "docker", "compose", "-p", self.project,
            "-f", str(COMPOSE), "-f", str(OVERRIDE),
        ]

    def command(
        self,
        arguments: list[str],
        *,
        timeout: int = 600,
        allowed: set[int] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        started = time.time()
        result = subprocess.run(
            [*self.base, *arguments],
            cwd=ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        self.events.append(
            {
                "command": ["docker", "compose", *arguments],
                "exit_code": result.returncode,
                "duration_seconds": round(time.time() - started, 3),
                "stdout": _redact(result.stdout),
                "stderr": _redact(result.stderr),
            }
        )
        expected = allowed or {0}
        if result.returncode not in expected:
            raise SetupE2EError(
                f"compose command failed ({result.returncode}): {' '.join(arguments)}"
            )
        return result

    def guard(self) -> dict[str, Any]:
        rendered = self.command(["--profile", "setup", "config", "--format", "json"])
        try:
            config = json.loads(rendered.stdout)
        except json.JSONDecodeError as error:
            raise SetupE2EError("rendered Compose config is not JSON") from error
        volumes = config.get("volumes") or {}
        resolved_names = {
            str(value.get("name") or key)
            for key, value in volumes.items()
            if isinstance(value, dict)
        }
        ports = (config.get("services") or {}).get("dashboard", {}).get("ports", [])
        published = {
            int(item.get("published"))
            for item in ports
            if isinstance(item, dict) and str(item.get("published", "")).isdigit()
        }
        if PROTECTED_VOLUME in resolved_names or self.volume not in resolved_names:
            raise SetupE2EError("rendered Compose config touches the protected volume")
        if PROTECTED_PORT in published or self.port not in published or len(published) != 1:
            raise SetupE2EError("rendered Compose config does not isolate the dashboard port")
        return {
            "project": self.project,
            "volume": self.volume,
            "port": self.port,
            "resolved_volumes": sorted(resolved_names),
            "published_ports": sorted(published),
        }

    def pull_services(self) -> None:
        for attempt in range(1, 4):
            try:
                self.command(["pull", "setup", "gateway", "dashboard"], timeout=1200)
                return
            except SetupE2EError:
                if attempt == 3:
                    raise
                self.events.append({"pull_retry": attempt, "backoff_seconds": 2 ** attempt})
                time.sleep(2 ** attempt)

    def wait_dashboard(self, timeout: int = 120) -> None:
        deadline = time.time() + timeout
        url = f"http://127.0.0.1:{self.port}/"
        last = ""
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    if 200 <= response.status < 500:
                        self.events.append({"probe": url, "status": response.status})
                        return
            except (OSError, urllib.error.URLError) as error:
                last = type(error).__name__
            time.sleep(2)
        raise SetupE2EError(f"dashboard did not respond: {last}")

    def service_state(self) -> dict[str, Any]:
        result = self.command(["ps", "--format", "json"])
        try:
            payload = json.loads(result.stdout or "[]")
            rows = payload if isinstance(payload, list) else [payload]
        except json.JSONDecodeError:
            rows = [
                json.loads(line)
                for line in result.stdout.splitlines()
                if line.strip()
            ]
        services = {
            str(row.get("Service")): {
                "name": row.get("Name"),
                "state": row.get("State"),
                "health": row.get("Health"),
            }
            for row in rows
            if isinstance(row, dict)
        }
        for required in ("gateway", "dashboard"):
            if required not in services or services[required]["state"] != "running":
                raise SetupE2EError(f"{required} service is not running")
        return services

    def write_receipt(self, *, status: str, detail: dict[str, Any]) -> None:
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "kind": "company-os-real-docker-e2e",
            "status": status,
            "run_id": self.run_id,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.started)),
            "duration_seconds": round(time.time() - self.started, 3),
            "detail": detail,
            "events": self.events,
            "cleanup": self.cleanup_state,
        }
        temporary = self.receipt_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.receipt_path)
        self.write_viewer(status=status, detail=detail)

    def write_viewer(self, *, status: str, detail: dict[str, Any]) -> None:
        checks = [
            ("Isolated Compose resources", "pass" if detail.get("guard") else "not reached"),
            ("Pinned image available", "pass" if any(event.get("command", [None, None, None])[:3] == ["docker", "compose", "pull"] and event.get("exit_code") == 0 for event in self.events) else "not reached"),
            ("Company OS wizard reached", "pass" if detail.get("launch_state") else "not reached"),
            ("Native profile reconciled", "pass" if detail.get("profile_reconciliation") else "not reached"),
            ("Gateway and dashboard running", "pass" if detail.get("services_before_restart") else "not reached"),
            ("Stop/start persistence", "pass" if detail.get("services_after_restart") else "not reached"),
        ]
        cards = "".join(
            f"<li><span>{html.escape(name)}</span><strong>{html.escape(value)}</strong></li>"
            for name, value in checks
        )
        service_json = html.escape(
            json.dumps(
                {
                    "before_restart": detail.get("services_before_restart"),
                    "after_restart": detail.get("services_after_restart"),
                    "managed_state_sha256": detail.get("managed_state_sha256"),
                },
                indent=2,
            )
        )
        page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Company OS Setup Proof</title>
<style>body{{margin:0;background:#f4f1e8;color:#17231f;font:16px/1.5 Inter,system-ui}}main{{max-width:1050px;margin:auto;padding:48px 28px}}header{{background:#173c35;color:white;padding:34px;border-radius:22px}}h1{{margin:0 0 8px}}ul{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;padding:0}}li{{list-style:none;background:white;border:1px solid #d7d0c1;border-radius:14px;padding:18px;display:flex;justify-content:space-between}}strong{{color:#176b52}}section{{background:white;border:1px solid #d7d0c1;border-radius:18px;padding:24px;margin-top:20px}}pre{{white-space:pre-wrap}}</style></head><body><main>
<header><h1>Company OS setup proof</h1><p>Real pinned image · isolated Docker volume · exact setup entrypoint · restart verified</p></header>
<ul>{cards}</ul><section><h2>Run boundary</h2><p>Status: <strong>{html.escape(status)}</strong></p><p>Project: {html.escape(self.project)}<br>Volume: {html.escape(self.volume)}<br>Dashboard: http://127.0.0.1:{self.port}</p></section>
<section><h2>Service evidence</h2><pre>{service_json}</pre></section></main></body></html>"""
        path = self.receipt_path.with_name("setup-proof.html")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(page, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    def cleanup(self) -> None:
        if self.keep:
            return
        if not self.project.startswith("company-os-e2e-") or not self.volume.startswith("company-os-e2e-"):
            raise SetupE2EError("cleanup ownership guard failed")
        self.command(["down", "-v", "--remove-orphans"], timeout=180, allowed={0})
        checks = [
            ["docker", "container", "ls", "-aq", "--filter", f"label=com.docker.compose.project={self.project}"],
            ["docker", "volume", "ls", "-q", "--filter", f"name=^{self.volume}$"],
            ["docker", "network", "ls", "-q", "--filter", f"name=^{self.project}_runtime$"],
        ]
        remaining: list[str] = []
        for arguments in checks:
            result = subprocess.run(arguments, text=True, capture_output=True, timeout=30, check=False)
            self.events.append(
                {
                    "command": arguments,
                    "exit_code": result.returncode,
                    "duration_seconds": 0,
                    "stdout": _redact(result.stdout),
                    "stderr": _redact(result.stderr),
                }
            )
            if result.returncode != 0 or result.stdout.strip():
                remaining.append(" ".join(arguments[1:3]))
        if remaining:
            raise SetupE2EError(f"disposable Docker resources remain after cleanup: {', '.join(remaining)}")
        self.cleanup_state = "complete_and_verified"


def safe_docker(args: argparse.Namespace) -> int:
    if not shutil.which("docker"):
        raise SetupE2EError("docker is unavailable")
    run_id = args.run_id or _run_id()
    port = args.port or _free_port()
    receipt = args.receipt.expanduser().resolve()
    operated = ComposeRun(run_id=run_id, port=port, receipt=receipt, keep=args.keep)
    detail: dict[str, Any] = {}
    try:
        detail["guard"] = operated.guard()
        operated.pull_services()
        launch = operated.command(
            [
                "--profile", "setup", "run", "--rm", "-T", "setup",
                "python", "/distribution/setup.py", "launch", "--non-interactive",
            ],
            timeout=1200,
            allowed={0, 2},
        )
        detail["launch_exit"] = launch.returncode
        launch_output = f"{launch.stdout}\n{launch.stderr}"
        if "invalid choice: 'launch'" in launch_output:
            raise SetupE2EError("setup command was incorrectly routed to hermes launch")
        if launch.returncode == 2:
            expected_marker = "Workspace setup needs your answers"
            if expected_marker not in launch_output:
                raise SetupE2EError("setup launch exited 2 without reaching the interactive wizard boundary")
            detail["launch_state"] = "interactive_answers_required"
        else:
            detail["launch_state"] = "completed_or_resumable"
        operated.command(
            ["--profile", "setup", "run", "--rm", "-T", "setup", "true"],
            timeout=300,
        )
        detail["profile_reconciliation"] = "second_container_boot_completed"
        operated.command(["up", "-d", "gateway", "dashboard"], timeout=600)
        operated.wait_dashboard()
        detail["services_before_restart"] = operated.service_state()
        operated.command(["stop", "gateway", "dashboard"], timeout=180)
        operated.command(["start", "gateway", "dashboard"], timeout=180)
        operated.wait_dashboard()
        detail["services_after_restart"] = operated.service_state()
        inspect = operated.command(
            ["--profile", "setup", "run", "--rm", "-T", "setup", "sh", "-lc",
             "python - <<'PY'\nfrom pathlib import Path\nimport hashlib\np=Path('/opt/data/profiles/company-os')\nh=hashlib.sha256()\nfor f in sorted(x for x in p.rglob('*') if x.is_file() and 'logs' not in x.parts and 'sessions' not in x.parts):\n h.update(str(f.relative_to(p)).encode()); h.update(f.read_bytes())\nprint(h.hexdigest())\nPY"],
            timeout=300,
        )
        detail["managed_state_sha256"] = inspect.stdout.strip().splitlines()[-1]
        operated.cleanup()
        operated.write_receipt(status="pass", detail=detail)
        print(json.dumps({"status": "pass", "receipt": str(receipt), **detail["guard"]}))
        return 0
    except (OSError, subprocess.TimeoutExpired, SetupE2EError, json.JSONDecodeError) as error:
        detail["error"] = str(error)
        if not operated.keep and operated.cleanup_state != "complete_and_verified":
            try:
                operated.cleanup()
            except Exception as cleanup_error:
                detail["cleanup_error"] = str(cleanup_error)
        operated.write_receipt(status="fail", detail=detail)
        print(json.dumps({"status": "fail", "receipt": str(receipt), "error": str(error)}))
        return 2


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    safe = subcommands.add_parser("safe-docker")
    safe.add_argument("--receipt", type=Path, required=True)
    safe.add_argument("--run-id")
    safe.add_argument("--port", type=int)
    safe.add_argument("--keep", action="store_true")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "safe-docker":
        return safe_docker(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
