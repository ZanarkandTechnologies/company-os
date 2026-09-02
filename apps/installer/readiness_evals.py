#!/usr/bin/env python3
"""Read-only data-readiness evaluation for configured Company OS sources."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from apps.installer import provider_catalog
from apps.installer.feature_setup import bindings_for_workspace
from apps.installer import model_output
from apps.installer import runtime as setup_runtime


SCHEMA_VERSION = 1
STATE_DIRECTORY = Path("state/readiness-evals")
CONNECTION_RECEIPT = Path("state/connection-evals/latest.json")
PREFLIGHT_PROMPT = Path(__file__).resolve().parent / "prompts" / "preflight.md"
SESSION_ID = re.compile(r"(?:^|\n)session_id:\s*([^\s]+)")
CommandRunner = Callable[..., Any]


class ReadinessEvalError(RuntimeError):
    """A redacted readiness orchestration failure."""


def _tool_allowed(tool_name: str, allowed_names: list[str]) -> bool:
    """Authorize only exact provider-qualified Hermes tool identities."""
    lowered = tool_name.casefold()
    return lowered in {name.casefold() for name in allowed_names}


@contextmanager
def _read_only_mcp_guard(
    profile_home: Path,
    server_names: set[str],
    command_runner: CommandRunner,
):
    """Make unknown/write-capable MCP calls require approval for this batch.

    Hermes' untrusted trust tier blocks every tool lacking a provider-declared
    ``readOnlyHint=true`` before the RPC fires. The original setting is restored
    afterward; a crash can only leave the safer untrusted setting behind.
    """
    originals: dict[str, str | None] = {}
    try:
        for name in sorted(server_names):
            key = f"mcp_servers.{name}.trust"
            current = command_runner(
                ["hermes", "config", "get", key], profile_home,
                check=False, timeout=30,
            )
            raw = current.stdout.strip() if current.returncode == 0 else ""
            originals[name] = raw if raw and raw.lower() not in {"null", "none"} else None
            changed = command_runner(
                ["hermes", "config", "set", key, "untrusted"], profile_home,
                check=False, timeout=30,
            )
            if changed.returncode:
                raise ReadinessEvalError(f"mcp_read_only_guard_failed:{name}")
        yield
    finally:
        for name, original in originals.items():
            key = f"mcp_servers.{name}.trust"
            arguments = (
                ["hermes", "config", "set", key, original]
                if original is not None
                else ["hermes", "config", "unset", key]
            )
            restored = command_runner(
                arguments, profile_home, check=False, timeout=30,
            )
            if restored.returncode:
                raise ReadinessEvalError(f"mcp_read_only_guard_restore_failed:{name}")


def _json_object(raw: str, error_code: str) -> dict[str, Any]:
    return model_output.json_object(raw, ReadinessEvalError(error_code))


def _session_trace(raw: str) -> list[dict[str, str]]:
    """Return an in-memory redacted trace containing only tool evidence."""
    trace: list[dict[str, str]] = []
    called_tools: list[str] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            session = json.loads(line)
        except json.JSONDecodeError as error:
            raise ReadinessEvalError("session_export_invalid") from error
        messages = session.get("messages") if isinstance(session, dict) else None
        if not isinstance(messages, list):
            raise ReadinessEvalError("session_export_messages_invalid")
        for message in messages:
            if not isinstance(message, dict):
                continue
            if message.get("role") == "assistant":
                tool_calls = message.get("tool_calls")
                if isinstance(tool_calls, list):
                    for tool_call in tool_calls:
                        if not isinstance(tool_call, dict):
                            continue
                        function = tool_call.get("function")
                        name = (
                            function.get("name")
                            if isinstance(function, dict)
                            else tool_call.get("name")
                        )
                        if isinstance(name, str) and name:
                            called_tools.append(name)
                continue
            if message.get("role") != "tool":
                continue
            name = str(message.get("tool_name") or message.get("name") or "unknown")
            if name not in called_tools:
                raise ReadinessEvalError("tool_result_without_call")
            content = message.get("content")
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False, sort_keys=True)
            trace.append({"tool": name, "content": content[:12000]})
    if not trace:
        raise ReadinessEvalError("tool_result_missing")
    if len(trace) != len(called_tools):
        raise ReadinessEvalError("tool_call_without_result")
    return trace


def _case_prompt(binding: dict[str, Any]) -> str:
    contract = binding["provider"]["readiness"]
    output = {
        "source_state": "populated|empty|inaccessible",
        "record_count": "non-negative integer or null",
        "available_fields": ["canonical_field_name"],
        "relations_with_values": ["canonical_relation_name"],
        "optional_fields_present": ["canonical_field_name"],
        "meeting_evidence": "present|absent|not_applicable",
        "read_only": True,
    }
    try:
        template = PREFLIGHT_PROMPT.read_text(encoding="utf-8")
    except OSError as error:
        raise ReadinessEvalError("preflight_prompt_missing") from error
    values = {
        "{{PROVIDER_INSTRUCTION}}": provider_catalog.render_readiness_prompt(binding),
        "{{OUTPUT_SCHEMA}}": json.dumps(output, separators=(",", ":")),
        "{{REQUIRED_FIELDS}}": json.dumps(contract.get("required_fields", [])),
        "{{REQUIRED_RELATIONS}}": json.dumps(contract.get("required_relations", [])),
        "{{OPTIONAL_FIELDS}}": json.dumps(contract.get("optional_fields", [])),
    }
    for marker, value in values.items():
        template = template.replace(marker, value)
    return template.strip()


def _run_case(
    binding: dict[str, Any],
    *,
    profile_home: Path,
    command_runner: CommandRunner,
    timeout: int,
) -> dict[str, Any]:
    prompt = _case_prompt(binding)
    mcp_name = str(binding["provider"]["mcp"]["name"])
    connection = command_runner(
        ["hermes", "mcp", "test", mcp_name],
        profile_home,
        check=False,
        timeout=60,
    )
    if not setup_runtime.mcp_connection_ready(connection):
        return {
            "case_id": binding["case_id"],
            "data_source": binding["data_source"],
            "provider": binding["provider"]["id"],
            "importance": binding["provider"]["readiness"]["importance"],
            "contract": binding["provider"]["readiness"],
            "response": "",
            "trace": [],
            "error": f"mcp_connection_test_failed:{mcp_name}",
        }
    result = command_runner(
        [
            "hermes", "chat", "--quiet", "--toolsets", mcp_name,
            "--ignore-rules", "--query-file", "-", "--source", "tool",
            "--max-turns", "40", "--run-budget", str(timeout),
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
        "importance": binding["provider"]["readiness"]["importance"],
        "contract": binding["provider"]["readiness"],
        "response": (result.stdout or "").strip(),
        "trace": [],
        "error": None,
    }
    if result.returncode:
        case["error"] = f"hermes_chat_exit_{result.returncode}"
        return case
    match = SESSION_ID.search(result.stderr or "")
    if not match:
        case["error"] = "session_id_missing"
        return case
    exported = command_runner(
        [
            "hermes", "sessions", "export", "-", "--format", "jsonl",
            "--session-id", match.group(1), "--redact", "--yes",
        ],
        profile_home,
        check=False,
        timeout=60,
    )
    if exported.returncode:
        case["error"] = f"session_export_exit_{exported.returncode}"
        return case
    try:
        case["trace"] = _session_trace(exported.stdout or "")
    except ReadinessEvalError as error:
        case["error"] = str(error)
        return case
    allowed = binding["provider"]["readiness"]["allowed_read_tools"]
    if any(not _tool_allowed(row["tool"], allowed) for row in case["trace"]):
        case["error"] = "non_read_tool_observed"
    return case


def _connection_proof(
    profile_home: Path,
    bindings: list[dict[str, Any]],
    binding: dict[str, Any],
    receipt: dict[str, Any] | None,
) -> dict[str, Any]:
    if receipt is None:
        try:
            loaded = json.loads((profile_home / CONNECTION_RECEIPT).read_text(encoding="utf-8"))
            receipt = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            receipt = {}
    current = receipt.get("configuration_sha256") == provider_catalog.configuration_hash(bindings)
    judgment = receipt.get("judgment")
    rows = judgment.get("cases", []) if isinstance(judgment, dict) else []
    certified = current and receipt.get("status") == "passed" and any(
        isinstance(row, dict)
        and row.get("case_id") == binding["case_id"]
        and row.get("status") == "passed"
        for row in rows
    )
    return {
        "case_id": binding["case_id"],
        "data_source": binding["data_source"],
        "provider": binding["provider"]["id"],
        "importance": "capability",
        "status": "passed" if certified else "needs_setup",
        "source_state": "capability_confirmed" if certified else "capability_unconfirmed",
        "record_count": None,
        "missing_required_fields": [],
        "missing_required_relations": [],
        "issues": [] if certified else ["capability_not_certified"],
        "warnings": [] if certified else ["capability_not_certified"],
        "evidence": {"proof": "current_connection_receipt", "configuration_match": current},
    }


def _judge_prompt(cases: list[dict[str, Any]]) -> str:
    payload = {
        "cases": [
            {
                "case_id": case["case_id"],
                "importance": case["importance"],
                "contract": case["contract"],
                "executor_error": case["error"],
                "response": case["response"],
                "tool_results": case["trace"],
            }
            for case in cases
        ]
    }
    return (
        "Judge this batch of read-only data-readiness cases using only the supplied "
        "Hermes responses and tool results. Never infer a fetch from assistant prose. "
        "A missing tool result, malformed response, or observed write is failed. "
        "For reachable core or optional input sources, empty data or missing required "
        "fields/relations is needs_setup. Optional declared fields are warnings only. "
        "Inaccessible sources are needs_setup. "
        "Destinations pass when reachable and need setup when inaccessible. Return "
        "JSON only, one row per case, with this shape and no free-text evidence: "
        '{"cases":[{"case_id":"...","status":"passed|needs_setup|failed",'
        '"source_state":"populated|empty|inaccessible","record_count":0,'
        '"available_fields":[],"relations_with_values":[],'
        '"meeting_evidence":"present|absent|not_applicable","warnings":[]}]}. '
        "Warnings may only use optional_source_empty, optional_field_missing:<field>, "
        "or meetings_not_observed. Do not include provider content, names, IDs, URLs, "
        "email addresses, or excerpts.\nINPUT:\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )


def _normalize_judgment(raw: str, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = _json_object(raw, "judge_response_invalid_json")
    rows = payload.get("cases")
    if not isinstance(rows, list):
        raise ReadinessEvalError("judge_response_invalid_shape")
    by_id = {case["case_id"]: case for case in cases}
    observed: set[str] = set()
    results: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ReadinessEvalError("judge_response_invalid_case")
        case_id = str(row.get("case_id") or "")
        if case_id not in by_id or case_id in observed:
            raise ReadinessEvalError("judge_response_case_mismatch")
        observed.add(case_id)
        case = by_id[case_id]
        contract = case["contract"]
        state = row.get("source_state")
        fields = row.get("available_fields")
        relations = row.get("relations_with_values")
        meeting_evidence = row.get("meeting_evidence")
        count = row.get("record_count")
        if (
            row.get("status") not in {"passed", "needs_setup", "failed"}
            or state not in {"populated", "empty", "inaccessible"}
            or not isinstance(fields, list)
            or not all(isinstance(value, str) for value in fields)
            or not isinstance(relations, list)
            or not all(isinstance(value, str) for value in relations)
            or meeting_evidence not in {"present", "absent", "not_applicable"}
            or (count is not None and (not isinstance(count, int) or count < 0))
        ):
            raise ReadinessEvalError("judge_response_invalid_verdict")
        required_fields = set(contract.get("required_fields", []))
        required_relations = set(contract.get("required_relations", []))
        optional_fields = set(contract.get("optional_fields", []))
        present_fields = set(fields)
        present_relations = set(relations)
        missing_fields = sorted(required_fields - present_fields)
        missing_relations = sorted(required_relations - present_relations)
        warnings: list[str] = []
        issues: list[str] = []
        status = "passed"
        if case["error"]:
            status = "failed"
            issues.append(str(case["error"]))
        elif state == "inaccessible":
            status = "needs_setup"
            issues.append("source_inaccessible")
        elif contract["importance"] in {"core", "optional"} and (
            state == "empty" or count == 0
        ):
            status = "needs_setup"
            issues.append(
                "core_source_empty"
                if contract["importance"] == "core"
                else "selected_source_empty"
            )
        elif contract["importance"] in {"core", "optional"} and (
            missing_fields or missing_relations
        ):
            status = "needs_setup"
            issues.extend(f"required_field_missing:{field}" for field in missing_fields)
            issues.extend(
                f"required_relation_missing:{field}" for field in missing_relations
            )
        elif contract["importance"] == "optional":
            warnings.extend(
                f"optional_field_missing:{field}"
                for field in sorted((required_fields | optional_fields) - present_fields)
            )
        results.append(
            {
                "case_id": case_id,
                "data_source": case["data_source"],
                "provider": case["provider"],
                "importance": contract["importance"],
                "status": status,
                "source_state": state,
                "record_count": count,
                "missing_required_fields": missing_fields,
                "missing_required_relations": missing_relations,
                "issues": issues,
                "warnings": warnings,
                "evidence": {
                    "tool_result_count": len(case["trace"]),
                    "tool_names": sorted({item["tool"] for item in case["trace"]}),
                    "response_sha256": hashlib.sha256(case["response"].encode()).hexdigest(),
                    "meeting_evidence": meeting_evidence,
                },
            }
        )
    if observed != set(by_id):
        raise ReadinessEvalError("judge_response_missing_case")
    return sorted(results, key=lambda item: item["case_id"])


def run_readiness_evals(
    profile_home: Path,
    workspace: Path,
    *,
    catalog_directory: Path = provider_catalog.DEFAULT_CATALOG,
    command_runner: CommandRunner = setup_runtime.run_command,
    max_workers: int = 1,
    timeout: int = 180,
    run_id: str | None = None,
    connection_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch selected sources read-only and judge their minimum usable shape once."""
    if max_workers < 1 or timeout < 1:
        raise ReadinessEvalError("readiness_limits_invalid")
    started = time.time()
    run_id = run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    catalog = provider_catalog.load_catalog(catalog_directory)
    bindings = bindings_for_workspace(workspace, catalog)
    configured_roles = {binding["data_source"] for binding in bindings}
    aliases = [binding for binding in bindings if binding["provider"]["readiness"]["importance"] == "alias"]
    capabilities = [binding for binding in bindings if binding["provider"]["readiness"]["importance"] == "capability"]
    selected = [binding for binding in bindings if binding not in aliases and binding not in capabilities]
    cases: list[dict[str, Any]] = []
    if selected:
        guarded_servers = {
            str(binding["provider"]["mcp"]["name"]) for binding in selected
        }
        with _read_only_mcp_guard(profile_home, guarded_servers, command_runner):
            with ThreadPoolExecutor(max_workers=min(max_workers, len(selected))) as pool:
                futures = {
                    pool.submit(
                        _run_case,
                        binding,
                        profile_home=profile_home,
                        command_runner=command_runner,
                        timeout=timeout,
                    ): binding
                    for binding in selected
                }
                for future in as_completed(futures):
                    binding = futures[future]
                    try:
                        cases.append(future.result())
                    except Exception:
                        cases.append(
                            {
                                "case_id": binding["case_id"],
                                "data_source": binding["data_source"],
                                "provider": binding["provider"]["id"],
                                "importance": binding["provider"]["readiness"]["importance"],
                                "contract": binding["provider"]["readiness"],
                                "response": "",
                                "trace": [],
                                "error": "executor_failed",
                            }
                        )
    results: list[dict[str, Any]] = [
        {
            "case_id": case["case_id"],
            "data_source": case["data_source"],
            "provider": case["provider"],
            "importance": case["importance"],
            "status": "failed",
            "source_state": "inaccessible",
            "record_count": None,
            "missing_required_fields": [],
            "missing_required_relations": [],
            "issues": [str(case["error"])],
            "warnings": [],
            "evidence": {"tool_result_count": len(case["trace"])},
        }
        for case in cases
        if case.get("error")
    ]
    judge_cases = [case for case in cases if not case.get("error")]
    judge_error: str | None = None
    if judge_cases:
        judge = command_runner(
            [
                "hermes", "chat", "--quiet", "--toolsets", "context_engine",
                "--query-file", "-", "--source",
                "tool", "--ignore-rules", "--max-turns", "3", "--run-budget", str(timeout),
            ],
            profile_home,
            input_text=_judge_prompt(
                sorted(judge_cases, key=lambda item: item["case_id"])
            ),
            check=False,
            timeout=timeout + 30,
        )
        if judge.returncode:
            judge_error = f"judge_exit_{judge.returncode}"
        else:
            try:
                results.extend(_normalize_judgment(judge.stdout or "", judge_cases))
            except ReadinessEvalError as error:
                judge_error = str(error)
    for binding in capabilities:
        results.append(_connection_proof(profile_home, bindings, binding, connection_receipt))
    result_by_role = {result["data_source"]: result for result in results}
    for binding in aliases:
        contract = binding["provider"]["readiness"]
        parent = result_by_role.get(contract["alias_of"])
        status = "needs_setup" if parent is None else parent["status"]
        warnings = ["alias_parent_missing"] if parent is None else []
        if parent:
            warnings = (
                []
                if parent.get("evidence", {}).get("meeting_evidence") == "present"
                else ["meetings_not_observed"]
            )
        results.append(
            {
                "case_id": binding["case_id"],
                "data_source": binding["data_source"],
                "provider": binding["provider"]["id"],
                "importance": "alias",
                "status": status,
                "source_state": "checked_within_tasks" if parent else "alias_parent_missing",
                "record_count": None,
                "missing_required_fields": [],
                "missing_required_relations": [],
                "issues": ["alias_parent_missing"] if parent is None else [],
                "warnings": warnings,
                "evidence": {"alias_of": contract["alias_of"], "separate_fetch": False},
            }
        )
    for role in ("projects", "tasks"):
        if role in configured_roles:
            continue
        results.append(
            {
                "case_id": f"{role}:not_configured",
                "data_source": role,
                "provider": "not_configured",
                "importance": "core",
                "status": "needs_setup",
                "source_state": "not_configured",
                "record_count": None,
                "missing_required_fields": [],
                "missing_required_relations": [],
                "issues": ["core_source_not_configured"],
                "warnings": [],
                "evidence": {"configured": False},
            }
        )
    if judge_error:
        status = "failed"
    elif any(result["status"] == "failed" for result in results):
        status = "failed"
    elif any(result["status"] == "needs_setup" for result in results):
        status = "needs_setup"
    else:
        status = "passed"
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": status,
        "profile": setup_runtime.PROFILE_NAME,
        "configuration_sha256": provider_catalog.configuration_hash(bindings),
        "readiness_sha256": provider_catalog.readiness_hash(bindings),
        "started_at": started,
        "finished_at": time.time(),
        "judge_calls": 1 if judge_cases else 0,
        "judge_error": judge_error,
        "cases": sorted(results, key=lambda item: item["case_id"]),
    }


def write_receipt(profile_home: Path, receipt: dict[str, Any]) -> Path:
    """Write owner-only immutable and latest receipts using atomic replacement."""
    directory = profile_home / STATE_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    destination = directory / f"{receipt['run_id']}.json"
    for target in (destination, directory / "latest.json"):
        descriptor, temporary = tempfile.mkstemp(prefix=".readiness-", dir=directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(receipt, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return destination


def latest_valid_passed_receipt(profile_home: Path, workspace: Path) -> tuple[Path, dict[str, Any]]:
    """Validate the latest passed readiness proof against current configuration."""
    directory = profile_home / STATE_DIRECTORY
    latest = directory / "latest.json"
    try:
        if latest.is_symlink():
            raise ReadinessEvalError("readiness_latest_unsafe")
        receipt = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReadinessEvalError("readiness_latest_missing") from error
    if not isinstance(receipt, dict) or receipt.get("status") != "passed":
        raise ReadinessEvalError("readiness_receipt_not_passed")
    run_id = receipt.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise ReadinessEvalError("readiness_latest_invalid")
    immutable = directory / f"{run_id}.json"
    try:
        if immutable.is_symlink():
            raise ReadinessEvalError("readiness_receipt_unsafe")
        saved = json.loads(immutable.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReadinessEvalError("readiness_receipt_missing") from error
    if saved != receipt:
        raise ReadinessEvalError("readiness_latest_stale")
    catalog = provider_catalog.load_catalog()
    bindings = bindings_for_workspace(workspace, catalog)
    if receipt.get("configuration_sha256") != provider_catalog.configuration_hash(bindings):
        raise ReadinessEvalError("readiness_configuration_stale")
    if receipt.get("readiness_sha256") != provider_catalog.readiness_hash(bindings):
        raise ReadinessEvalError("readiness_contract_stale")
    return immutable, receipt
