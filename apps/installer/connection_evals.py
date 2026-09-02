#!/usr/bin/env python3
"""Certify configured data-source providers through Hermes and one batch judge."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.installer import provider_catalog
from apps.installer.feature_setup import bindings_for_workspace
from apps.installer import model_output
from apps.installer import runtime as setup_runtime


SCHEMA_VERSION = 1
STATE_DIRECTORY = Path("state/connection-evals")
SESSION_ID = re.compile(r"(?:^|\n)session_id:\s*([^\s]+)")
CommandRunner = Callable[..., Any]


class ConnectionEvalError(RuntimeError):
    """A redacted connection-eval orchestration failure."""


def _compact_content(value: Any, limit: int = 8000) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return text if len(text) <= limit else text[:limit] + "…[truncated]"


def compact_session_export(raw: str) -> list[dict[str, Any]]:
    """Keep only judge-relevant messages and tool evidence from a redacted export."""
    messages: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            session = json.loads(line)
        except json.JSONDecodeError as error:
            raise ConnectionEvalError("session_export_invalid") from error
        rows = session.get("messages", []) if isinstance(session, dict) else []
        if not isinstance(rows, list):
            raise ConnectionEvalError("session_export_messages_invalid")
        for message in rows:
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "")
            if role == "system":
                continue
            compact: dict[str, Any] = {"role": role}
            if role == "tool":
                compact["tool"] = str(
                    message.get("tool_name") or message.get("name") or "unknown"
                )
                compact["content"] = _compact_content(message.get("content"))
            elif role == "assistant" and message.get("tool_calls"):
                compact["tool_calls"] = message.get("tool_calls")
                if message.get("content"):
                    compact["content"] = _compact_content(message.get("content"))
            elif role in {"user", "assistant"}:
                compact["content"] = _compact_content(message.get("content"))
            else:
                continue
            messages.append(compact)
    if not messages:
        raise ConnectionEvalError("session_export_empty")
    return messages


def _run_case(
    binding: dict[str, Any],
    *,
    run_id: str,
    profile_home: Path,
    command_runner: CommandRunner,
    timeout: int,
) -> dict[str, Any]:
    prompt = provider_catalog.render_test_prompt(binding, run_id)
    mcp_name = str(binding["provider"]["mcp"]["name"])
    result = command_runner(
        [
            "hermes",
            "chat",
            "--quiet",
            "--toolsets",
            mcp_name,
            "--ignore-rules",
            "--query-file",
            "-",
            "--source",
            "tool",
            "--max-turns",
            "80",
            "--run-budget",
            str(timeout),
        ],
        profile_home,
        input_text=prompt,
        check=False,
        timeout=timeout + 30,
    )
    case: dict[str, Any] = {
        "case_id": binding["case_id"],
        "data_source": binding["data_source"],
        "provider": binding["provider"]["id"],
        "connection": provider_catalog.connection_key(binding["provider"]),
        "risk": binding["provider"]["test"]["risk"],
        "prompt": prompt,
        "expected_output": binding["provider"]["test"]["expected_output"],
        "assertions": binding["provider"]["test"]["assertions"],
        "response": (result.stdout or "").strip(),
        "session_id": None,
        "trace": [],
        "precheck": "failed",
        "error": None,
    }
    if result.returncode:
        case["error"] = f"hermes_chat_exit_{result.returncode}"
        return case
    match = SESSION_ID.search(result.stderr or "")
    if not match:
        case["error"] = "session_id_missing"
        return case
    session_id = match.group(1)
    case["session_id"] = session_id
    exported = command_runner(
        [
            "hermes",
            "sessions",
            "export",
            "-",
            "--format",
            "jsonl",
            "--session-id",
            session_id,
            "--redact",
            "--yes",
        ],
        profile_home,
        check=False,
        timeout=60,
    )
    if exported.returncode:
        case["error"] = f"session_export_exit_{exported.returncode}"
        return case
    try:
        case["trace"] = compact_session_export(exported.stdout or "")
    except ConnectionEvalError as error:
        case["error"] = str(error)
        return case
    has_tool_result = any(message.get("role") == "tool" for message in case["trace"])
    if not has_tool_result:
        case["error"] = "tool_result_missing"
        return case
    case["precheck"] = "passed"
    return case


def _judge_prompt(run_id: str, cases: list[dict[str, Any]]) -> str:
    payload = {
        "run_id": run_id,
        "cases": [
            {
                "case_id": case["case_id"],
                "data_source": case["data_source"],
                "provider": case["provider"],
                "expected_output": case["expected_output"],
                "assertions": case["assertions"],
                "precheck": case["precheck"],
                "precheck_error": case["error"],
                "response": case["response"],
                "redacted_trace": case["trace"],
            }
            for case in cases
        ],
    }
    return (
        "Judge this batch of configured-provider connection evals. Use only the "
        "supplied response and redacted Hermes trace. A case passes only when every "
        "assertion is directly supported and the precheck passed. Never infer a "
        "provider action from prose alone. Return JSON only with this shape: "
        '{"overall":"passed|failed","cases":[{"case_id":"...",'
        '"status":"passed|failed","assertions":[{"index":0,"passed":true,'
        '"evidence":"brief observed evidence"}],"reason":"brief reason"}]}. '
        "Include every input case exactly once. The overall result is failed when "
        "any case fails.\n\nINPUT:\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )


def _json_object(raw: str) -> dict[str, Any]:
    return model_output.json_object(
        raw, ConnectionEvalError("judge_response_invalid_json")
    )


def _validate_judgment(
    judgment: dict[str, Any], cases: list[dict[str, Any]]
) -> dict[str, Any]:
    rows = judgment.get("cases")
    if judgment.get("overall") not in {"passed", "failed"} or not isinstance(rows, list):
        raise ConnectionEvalError("judge_response_invalid_shape")
    expected_ids = {case["case_id"] for case in cases}
    observed_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    case_by_id = {case["case_id"]: case for case in cases}
    for row in rows:
        if not isinstance(row, dict):
            raise ConnectionEvalError("judge_response_invalid_case")
        case_id = str(row.get("case_id") or "")
        if case_id not in expected_ids or case_id in observed_ids:
            raise ConnectionEvalError("judge_response_case_mismatch")
        observed_ids.add(case_id)
        status = row.get("status")
        assertions = row.get("assertions")
        if status not in {"passed", "failed"} or not isinstance(assertions, list):
            raise ConnectionEvalError("judge_response_invalid_verdict")
        expected_count = len(case_by_id[case_id]["assertions"])
        if len(assertions) != expected_count:
            raise ConnectionEvalError("judge_response_assertion_count")
        for index, assertion in enumerate(assertions):
            if (
                not isinstance(assertion, dict)
                or assertion.get("index") != index
                or not isinstance(assertion.get("passed"), bool)
                or not isinstance(assertion.get("evidence"), str)
            ):
                raise ConnectionEvalError("judge_response_invalid_assertion")
        if case_by_id[case_id]["precheck"] != "passed" or not all(
            assertion["passed"] for assertion in assertions
        ):
            status = "failed"
        normalized.append(
            {
                "case_id": case_id,
                "status": status,
                "assertions": assertions,
                "reason": str(row.get("reason") or ""),
            }
        )
    if observed_ids != expected_ids:
        raise ConnectionEvalError("judge_response_missing_case")
    overall = "passed" if all(row["status"] == "passed" for row in normalized) else "failed"
    return {"overall": overall, "cases": sorted(normalized, key=lambda row: row["case_id"])}


def run_connection_evals(
    profile_home: Path,
    workspace: Path,
    *,
    catalog_directory: Path = provider_catalog.DEFAULT_CATALOG,
    command_runner: CommandRunner = setup_runtime.run_command,
    max_workers: int = 3,
    timeout: int = 180,
    allow_side_effects: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute selected cases concurrently, then grade all results once."""
    if max_workers < 1:
        raise ConnectionEvalError("max_workers_must_be_positive")
    if timeout < 1:
        raise ConnectionEvalError("timeout_must_be_positive")
    started = time.time()
    run_id = run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    catalog = provider_catalog.load_catalog(catalog_directory)
    bindings = bindings_for_workspace(workspace, catalog)
    selected: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for binding in bindings:
        test = binding["provider"]["test"]
        if test["requires_confirmation"] and not allow_side_effects:
            blocked.append(
                {
                    "case_id": binding["case_id"],
                    "data_source": binding["data_source"],
                    "provider": binding["provider"]["id"],
                    "status": "human_required",
                    "reason": f"{test['risk']}_test_requires_confirmation",
                }
            )
        else:
            selected.append(binding)
    cases: list[dict[str, Any]] = []
    if selected:
        workers = max(1, min(max_workers, len(selected)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _run_case,
                    binding,
                    run_id=run_id,
                    profile_home=profile_home,
                    command_runner=command_runner,
                    timeout=timeout,
                ): binding["case_id"]
                for binding in selected
            }
            for future in as_completed(futures):
                try:
                    cases.append(future.result())
                except Exception:
                    binding = next(
                        item for item in selected if item["case_id"] == futures[future]
                    )
                    cases.append(
                        {
                            "case_id": binding["case_id"],
                            "data_source": binding["data_source"],
                            "provider": binding["provider"]["id"],
                            "connection": provider_catalog.connection_key(binding["provider"]),
                            "risk": binding["provider"]["test"]["risk"],
                            "prompt": provider_catalog.render_test_prompt(binding, run_id),
                            "expected_output": binding["provider"]["test"]["expected_output"],
                            "assertions": binding["provider"]["test"]["assertions"],
                            "response": "",
                            "session_id": None,
                            "trace": [],
                            "precheck": "failed",
                            "error": "executor_failed",
                        }
                    )
    cases.sort(key=lambda case: case["case_id"])
    judgment: dict[str, Any] | None = None
    judge_error: str | None = None
    if cases:
        result = command_runner(
            [
                "hermes",
                "chat",
                "--quiet",
                "--query-file",
                "-",
                "--source",
                "tool",
                "--ignore-rules",
                "--max-turns",
                "3",
                "--run-budget",
                str(timeout),
            ],
            profile_home,
            input_text=_judge_prompt(run_id, cases),
            check=False,
            timeout=timeout + 30,
        )
        if result.returncode:
            judge_error = f"judge_exit_{result.returncode}"
        else:
            try:
                judgment = _validate_judgment(_json_object(result.stdout or ""), cases)
            except ConnectionEvalError as error:
                judge_error = str(error)
    status = "passed"
    if blocked:
        status = "human_required"
    if judge_error or (judgment and judgment["overall"] != "passed"):
        status = "failed"
    if cases and judgment is None:
        status = "failed"
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": status,
        "profile": setup_runtime.PROFILE_NAME,
        "configuration_sha256": provider_catalog.configuration_hash(bindings),
        "started_at": started,
        "finished_at": time.time(),
        "parallelism": max(1, min(max_workers, len(selected))) if selected else 0,
        "judge_calls": 1 if cases else 0,
        "cases": cases,
        "blocked": blocked,
        "judgment": judgment,
        "judge_error": judge_error,
    }
    return receipt


def write_receipt(profile_home: Path, receipt: dict[str, Any]) -> Path:
    directory = profile_home / STATE_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    destination = directory / f"{receipt['run_id']}.json"
    for target in (destination, directory / "latest.json"):
        descriptor, temporary = tempfile.mkstemp(prefix=".connection-eval-", dir=directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(receipt, stream, indent=2, sort_keys=True)
                stream.write("\n")
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return destination


def defer_connection_evals(
    profile_home: Path,
    workspace: Path,
    *,
    previous: dict[str, Any] | None = None,
    reason: str = "deferred_by_user",
    catalog_directory: Path = provider_catalog.DEFAULT_CATALOG,
) -> dict[str, Any]:
    """Persist an honest, configuration-bound defer decision for later retry."""
    bindings = bindings_for_workspace(
        workspace, provider_catalog.load_catalog(catalog_directory)
    )
    receipt = dict(previous or {})
    previous_run_id = receipt.get("run_id")
    receipt.update(
        {
            "schema_version": SCHEMA_VERSION,
            "run_id": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            + "-"
            + uuid.uuid4().hex[:8],
            "status": "deferred",
            "last_attempt_status": (previous or {}).get("status", "not_run"),
            "previous_run_id": previous_run_id,
            "deferred_reason": reason,
            "deferred_at": time.time(),
            "profile": setup_runtime.PROFILE_NAME,
            "configuration_sha256": provider_catalog.configuration_hash(bindings),
        }
    )
    write_receipt(profile_home, receipt)
    return receipt


def resolve_certification(
    run: Callable[[], dict[str, Any]],
    render: Callable[[dict[str, Any]], None],
    choose: Callable[[], str],
    defer: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    interactive: bool,
) -> dict[str, Any]:
    """Resolve certification by passing, retrying, or explicitly deferring."""
    while True:
        receipt = run()
        render(receipt)
        if receipt.get("status") == "passed" or not interactive:
            return receipt
        if choose() == "retry":
            continue
        return defer(receipt)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--profile-home", type=Path, required=True)
    command.add_argument("--workspace", type=Path)
    command.add_argument("--catalog", type=Path, default=provider_catalog.DEFAULT_CATALOG)
    command.add_argument("--max-workers", type=int, default=3)
    command.add_argument("--timeout", type=int, default=180)
    command.add_argument("--allow-side-effects", action="store_true")
    return command


def main() -> int:
    args = parser().parse_args()
    profile_home = args.profile_home.expanduser().resolve()
    workspace = (args.workspace or profile_home / "workspace.hermes.md").expanduser().resolve()
    try:
        receipt = run_connection_evals(
            profile_home,
            workspace,
            catalog_directory=args.catalog.expanduser().resolve(),
            max_workers=args.max_workers,
            timeout=args.timeout,
            allow_side_effects=args.allow_side_effects,
        )
        path = write_receipt(profile_home, receipt)
        print(json.dumps({"status": receipt["status"], "receipt": str(path)}))
        return {"passed": 0, "human_required": 1}.get(receipt["status"], 2)
    except (ConnectionEvalError, provider_catalog.CatalogError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
