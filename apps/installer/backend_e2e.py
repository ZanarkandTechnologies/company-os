#!/usr/bin/env python3
"""Prove that host Hermes can execute and clean up its Docker terminal backend."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import uuid
from pathlib import Path


def run(receipt: Path) -> int:
    from tools.environments.docker import DockerEnvironment

    started = time.time()
    task_id = "company-os-backend-proof-" + uuid.uuid4().hex[:8]
    status = "fail"
    result: dict = {}
    cleanup = "pending"
    host_persistence = False
    with tempfile.TemporaryDirectory(prefix="company-os-docker-proof-") as temporary:
        host_workspace = Path(temporary).resolve()
        environment = DockerEnvironment(
            image=(
                "python:3.11-slim@sha256:"
                "6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2"
            ),
            cwd="/workspace",
            timeout=30,
            persistent_filesystem=False,
            persist_across_processes=False,
            task_id=task_id,
            network=False,
            host_cwd=str(host_workspace),
            auto_mount_cwd=True,
        )
        try:
            result = environment.execute(
                "python -c 'from pathlib import Path; import json,os; "
                "Path(\"persistence.txt\").write_text(\"COMPANY_OS_DOCKER_PERSISTENCE_OK\"); "
                "print(json.dumps({\"backend\":\"docker\",\"cwd\":os.getcwd(),\"ok\":True}))'"
            )
            parsed = json.loads(str(result.get("output", "")).strip())
        finally:
            environment.cleanup(force_remove=True)
            environment.wait_for_cleanup(timeout=30)
            cleanup = "complete"
        marker = host_workspace / "persistence.txt"
        host_persistence = (
            marker.is_file()
            and marker.read_text(encoding="utf-8") == "COMPANY_OS_DOCKER_PERSISTENCE_OK"
        )
        if result.get("returncode") == 0 and parsed == {
            "backend": "docker",
            "cwd": "/workspace",
            "ok": True,
        } and host_persistence:
            status = "pass"

    payload = {
        "schema_version": 1,
        "kind": "host-hermes-docker-backend-e2e",
        "status": status,
        "task_id": task_id,
        "duration_seconds": round(time.time() - started, 3),
        "network": "disabled",
        "host_workspace_persistence": host_persistence,
        "observation": {
            "returncode": result.get("returncode"),
            "output": str(result.get("output", "")).strip(),
        },
        "cleanup": cleanup,
    }
    receipt = receipt.expanduser().resolve()
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, receipt)
    print(json.dumps({"status": status, "receipt": str(receipt)}))
    return 0 if status == "pass" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    return run(args.receipt)


if __name__ == "__main__":
    raise SystemExit(main())
