#!/usr/bin/env python3
"""Run the installed PM eval suites without provider or messaging effects."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Any, Callable

from apps.eval_viewer.build import build_static_evidence_viewer
from apps.eval_viewer.model import ViewerError, build_evidence_model
from apps.installer import runtime
from apps.installer import model_output


CADENCES = ("daily", "weekly")
STATE_DIRECTORY = Path("workspace/.company-os/eval-runs")
SESSION_ID = re.compile(r"(?:^|\n)session_id:\s*([^\s]+)")
FILE_TOOLSET = "file"
# This is a real Hermes toolset whose resolved tool list is empty. It gives the
# judge a model-only turn instead of inheriting the profile's default tools.
NO_TOOLS_TOOLSET = "context_engine"
ALLOWED_GENERATION_TOOLS = {"read_file", "write_file", "patch", "search_files"}
CommandRunner = Callable[..., Any]
BrowserOpener = Callable[[str], Any]


class EvaluationError(RuntimeError):
    """A redacted, operator-actionable evaluation failure."""


def package_root() -> Path:
    """Resolve catalogs and fixtures from this installed distribution."""
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvaluationError(f"{label}_invalid") from error
    if not isinstance(value, dict):
        raise EvaluationError(f"{label}_invalid")
    return value


def load_catalog(root: Path) -> dict[str, list[dict[str, Any]]]:
    """Load and strictly validate both capability-owned eval catalogs."""
    suites: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    for cadence in CADENCES:
        path = root / f"skills/pm-{cadence}/evals/evals.json"
        suite = _read_json(path, f"pm_{cadence}_catalog")
        rows = suite.get("evals")
        if suite.get("skill_name") != f"pm-{cadence}" or not isinstance(rows, list) or not rows:
            raise EvaluationError(f"pm_{cadence}_catalog_invalid")
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                raise EvaluationError(f"pm_{cadence}_catalog_invalid")
            eval_id = row.get("id")
            files = row.get("files")
            assertions = row.get("assertions")
            if (
                not isinstance(eval_id, str)
                or not re.fullmatch(r"[a-z0-9_]+", eval_id)
                or eval_id in seen
                or not isinstance(row.get("prompt"), str)
                or not isinstance(row.get("expected_output"), str)
                or not isinstance(files, list)
                or not files
                or not all(isinstance(item, str) for item in files)
                or not isinstance(assertions, list)
                or not assertions
                or not all(isinstance(item, str) for item in assertions)
            ):
                raise EvaluationError(f"pm_{cadence}_catalog_invalid")
            seen.add(eval_id)
            normalized.append(row)
        suites[cadence] = normalized
    return suites


def _owner_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def _write_json(path: Path, value: Any) -> None:
    _owner_directory(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _copy_private(source: Path, destination: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise EvaluationError("eval_fixture_missing")
    _owner_directory(destination.parent)
    shutil.copyfile(source, destination)
    os.chmod(destination, 0o600)


def prepare_run(
    profile_home: Path,
    *,
    root: Path | None = None,
    run_id: str | None = None,
) -> tuple[Path, dict[str, list[dict[str, Any]]]]:
    """Materialize immutable, mutually-exclusive scenarios in private state."""
    root = (root or package_root()).resolve()
    suites = load_catalog(root)
    run_id = run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise EvaluationError("eval_run_id_invalid")
    state = profile_home.expanduser().resolve() / STATE_DIRECTORY
    _owner_directory(state)
    run = state / run_id
    if run.exists():
        raise EvaluationError("eval_run_already_exists")
    _owner_directory(run)
    for cadence, cases in suites.items():
        cadence_root = run / cadence
        _owner_directory(cadence_root)
        _copy_private(root / f"skills/pm-{cadence}/SKILL.md", cadence_root / "SKILL.md")
        for case in cases:
            scenario = cadence_root / "scenarios" / case["id"]
            _owner_directory(scenario / "inputs")
            _owner_directory(scenario / "outputs")
            _write_json(scenario / "case.json", case)
            skill_root = root / f"skills/pm-{cadence}"
            for relative in case["files"]:
                candidate = Path(relative)
                if candidate.is_absolute() or ".." in candidate.parts:
                    raise EvaluationError("eval_fixture_path_invalid")
                source = (skill_root / candidate).resolve()
                if skill_root.resolve() not in source.parents:
                    raise EvaluationError("eval_fixture_path_invalid")
                _copy_private(source, scenario / "inputs" / candidate)
        templates = root / f"skills/pm-{cadence}/templates"
        if templates.is_dir():
            for source in sorted(templates.rglob("*")):
                if source.is_file() and not source.is_symlink():
                    _copy_private(source, cadence_root / "templates" / source.relative_to(templates))
    return run, suites


def generation_prompt(container_cadence_root: Path, cases: list[dict[str, Any]], cadence: str) -> str:
    manifest = [
        {
            "eval_id": case["id"],
            "instruction": case["prompt"],
            "expected_output": case["expected_output"],
            "assertions": case["assertions"],
            "scenario": str(container_cadence_root / "scenarios" / case["id"]),
        }
        for case in cases
    ]
    return (
        f"Read SKILL.md completely, then operate this isolated PM {cadence} "
        "evaluation batch. The host working directory is bind-mounted at /workspace in "
        f"the Docker backend. The exact batch root is {container_cadence_root}. Resolve every "
        "scenario from the absolute container path in MANIFEST and write artifacts only under "
        "that scenario's outputs directory; never use a host absolute path. "
        "The scenarios are mutually exclusive: treat each scenario as a fresh "
        "world and never carry facts or generated state between them. Read only that scenario's "
        "inputs plus the copied templates in this working directory. Write only inside that "
        "scenario's outputs directory using relative paths. "
        "For every scenario, create outputs/result.md explaining the observed result and source "
        "evidence; also create every business artifact required by the skill. A legitimate no-op "
        "or blocked scenario still requires result.md proving why no business artifact changed. "
        "Do not use network, MCP, provider, browser, messaging, terminal, or delegation tools. "
        "Do not modify source inputs. Finish all scenarios in this single session and return a "
        "concise list of completed eval IDs and output paths.\n\nMANIFEST:\n"
        + json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
    )


def _require_persistent_docker_workspace(
    profile_home: Path, command_runner: CommandRunner
) -> None:
    """Fail before model spend unless Docker outputs persist to the host workspace."""
    expected = {
        "terminal.backend": {"docker"},
        "terminal.docker_mount_cwd_to_workspace": {"true", "1", "yes", "on"},
    }
    for key, accepted in expected.items():
        result = command_runner(
            ["hermes", "config", "get", key],
            profile_home,
            check=False,
            timeout=30,
        )
        if result.returncode or result.stdout.strip().lower() not in accepted:
            raise EvaluationError(f"eval_runtime_config_invalid:{key}")


def _compact_trace(raw: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            session = json.loads(line)
        except json.JSONDecodeError as error:
            raise EvaluationError("eval_trace_invalid") from error
        rows = session.get("messages") if isinstance(session, dict) else None
        if not isinstance(rows, list):
            raise EvaluationError("eval_trace_invalid")
        for row in rows:
            if not isinstance(row, dict) or row.get("role") == "system":
                continue
            role = str(row.get("role") or "")
            compact: dict[str, Any] = {"role": role}
            if role == "tool":
                compact["tool"] = str(row.get("tool_name") or row.get("name") or "unknown")
                compact["content"] = str(row.get("content") or "")[:4000]
            elif role == "assistant" and row.get("tool_calls"):
                compact["tool_calls"] = row["tool_calls"]
                if row.get("content"):
                    compact["content"] = str(row["content"])[:4000]
            elif role in {"user", "assistant"}:
                compact["content"] = str(row.get("content") or "")[:4000]
            else:
                continue
            messages.append(compact)
    if not messages:
        raise EvaluationError("eval_trace_empty")
    return messages


def _tool_names(trace: list[dict[str, Any]]) -> set[str]:
    names = {str(row["tool"]) for row in trace if row.get("role") == "tool" and row.get("tool")}
    for row in trace:
        for call in row.get("tool_calls") or []:
            if isinstance(call, dict):
                function = call.get("function")
                name = function.get("name") if isinstance(function, dict) else call.get("name")
                if name:
                    names.add(str(name))
    return names


def _run_cadence(
    profile_home: Path,
    run: Path,
    cadence: str,
    cases: list[dict[str, Any]],
    *,
    command_runner: CommandRunner,
    timeout: int,
) -> dict[str, Any]:
    cadence_root = run / cadence
    workspace_root = profile_home / "workspace"
    try:
        container_cadence_root = Path("/workspace") / cadence_root.relative_to(workspace_root)
    except ValueError as error:
        raise EvaluationError("eval_run_outside_workspace") from error
    result = command_runner(
        [
            "hermes", "chat", "--quiet", "--toolsets", FILE_TOOLSET,
            "--ignore-rules", "--query-file", "-", "--source", "tool",
            "--in", str(workspace_root), "--max-turns", "120", "--run-budget", str(timeout),
        ],
        profile_home,
        input_text=generation_prompt(container_cadence_root, cases, cadence),
        check=False,
        timeout=timeout + 30,
    )
    if result.returncode:
        raise EvaluationError(f"eval_{cadence}_generation_failed")
    match = SESSION_ID.search(result.stderr or "")
    if not match:
        raise EvaluationError(f"eval_{cadence}_session_missing")
    session_id = match.group(1)
    exported = command_runner(
        [
            "hermes", "sessions", "export", "-", "--format", "jsonl",
            "--session-id", session_id, "--redact", "--yes",
        ],
        profile_home,
        check=False,
        timeout=60,
    )
    if exported.returncode:
        raise EvaluationError(f"eval_{cadence}_trace_export_failed")
    trace = _compact_trace(exported.stdout or "")
    tools = _tool_names(trace)
    if not tools or not tools.issubset(ALLOWED_GENERATION_TOOLS):
        raise EvaluationError(f"eval_{cadence}_unsafe_tool_trace")
    _write_json(run / "traces" / f"{cadence}.json", {"session_id": session_id, "messages": trace})
    outputs: dict[str, list[str]] = {}
    for case in cases:
        output_root = cadence_root / "scenarios" / case["id"] / "outputs"
        result_path = output_root / "result.md"
        if not result_path.is_file() or result_path.is_symlink() or not result_path.read_text(encoding="utf-8").strip():
            raise EvaluationError(f"eval_output_missing:{case['id']}")
        rows: list[str] = []
        for path in sorted(output_root.rglob("*")):
            if path.is_symlink():
                raise EvaluationError(f"eval_output_unsafe:{case['id']}")
            if path.is_file():
                relative = path.relative_to(run).as_posix()
                rows.append(relative)
                os.chmod(path, 0o600)
        if not rows:
            raise EvaluationError(f"eval_output_missing:{case['id']}")
        outputs[case["id"]] = rows
    return {"status": "passed", "session_id": session_id, "outputs": outputs}


def _artifact_payload(run: Path, outputs: dict[str, list[str]]) -> dict[str, list[dict[str, str]]]:
    payload: dict[str, list[dict[str, str]]] = {}
    for eval_id, paths in outputs.items():
        rows = []
        for relative in paths:
            path = (run / relative).resolve()
            if run.resolve() not in path.parents or not path.is_file():
                raise EvaluationError(f"eval_output_missing:{eval_id}")
            content = path.read_text(encoding="utf-8", errors="replace")
            rows.append({"path": relative, "content": content[:24000]})
        payload[eval_id] = rows
    return payload


def judge_prompt(
    run_id: str,
    suites: dict[str, list[dict[str, Any]]],
    artifacts: dict[str, list[dict[str, str]]],
) -> str:
    cases = []
    for cadence in CADENCES:
        for case in suites[cadence]:
            cases.append(
                {
                    "eval_id": case["id"],
                    "cadence": cadence,
                    "expected_output": case["expected_output"],
                    "assertions": case["assertions"],
                    "artifacts": artifacts[case["id"]],
                }
            )
    schema = (
        '{"overall":"passed|failed","eval_results":[{"eval_id":"...",'
        '"status":"passed|failed","assertions":[{"index":0,"met":true,'
        '"evidence":["specific artifact evidence"]}],"reason":"brief reason"}]}'
    )
    return (
        "Judge this complete PM Daily and PM Weekly evaluation batch using only the supplied "
        "artifacts. Do not use tools. Include every eval ID exactly once and every authored "
        "assertion exactly once in source order. Evidence must name a supplied path and a "
        "specific observed fact. Missing or ambiguous evidence fails the assertion. A case "
        "passes only when every assertion passes; overall passes only when every case passes. "
        f"Return JSON only with this exact shape: {schema}\n\nINPUT:\n"
        + json.dumps({"run_id": run_id, "cases": cases}, ensure_ascii=False, separators=(",", ":"))
    )


def judge_repair_prompt(
    raw_response: str, suites: dict[str, list[dict[str, Any]]]
) -> str:
    cases = [
        {"eval_id": case["id"], "assertion_count": len(case["assertions"])}
        for cadence in CADENCES
        for case in suites[cadence]
    ]
    return (
        "Normalize the prior evaluator response into the required JSON contract. Do not "
        "re-judge, add cases, omit cases, or use tools. Preserve its pass/fail decisions and "
        "specific evidence. Include each listed eval_id once and assertion indexes from zero "
        "through assertion_count minus one. Return JSON only with keys overall and "
        "eval_results; each result must have eval_id, status, assertions, and reason; each "
        "assertion must have index, met, and a non-empty evidence array.\n\n"
        + json.dumps(
            {"cases": cases, "prior_response": raw_response[:48000]},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
def _json_object(raw: str) -> dict[str, Any]:
    return model_output.json_object(raw, EvaluationError("eval_judge_invalid_json"))


def validate_judgment(
    value: dict[str, Any], suites: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    expected = {case["id"]: case for cadence in CADENCES for case in suites[cadence]}
    rows = value.get("eval_results")
    if (
        set(value) != {"overall", "eval_results"}
        or value.get("overall") not in {"passed", "failed"}
        or not isinstance(rows, list)
    ):
        raise EvaluationError("eval_judge_invalid_shape")
    observed: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise EvaluationError("eval_judge_invalid_case")
        if set(row) != {"eval_id", "status", "assertions", "reason"}:
            raise EvaluationError("eval_judge_invalid_case")
        eval_id = row.get("eval_id")
        if not isinstance(eval_id, str) or eval_id not in expected or eval_id in observed:
            raise EvaluationError("eval_judge_case_mismatch")
        observed.add(eval_id)
        assertions = row.get("assertions")
        if (
            row.get("status") not in {"passed", "failed"}
            or not isinstance(assertions, list)
            or not isinstance(row.get("reason"), str)
        ):
            raise EvaluationError("eval_judge_invalid_verdict")
        required = expected[eval_id]["assertions"]
        if len(assertions) != len(required):
            raise EvaluationError("eval_judge_assertion_count")
        normalized_assertions = []
        for index, assertion in enumerate(assertions):
            if (
                not isinstance(assertion, dict)
                or set(assertion) != {"index", "met", "evidence"}
                or assertion.get("index") != index
                or not isinstance(assertion.get("met"), bool)
                or not isinstance(assertion.get("evidence"), list)
                or not assertion["evidence"]
                or not all(isinstance(item, str) and item.strip() for item in assertion["evidence"])
            ):
                raise EvaluationError("eval_judge_invalid_assertion")
            normalized_assertions.append(
                {"index": index, "met": assertion["met"], "evidence": assertion["evidence"]}
            )
        status = "passed" if all(item["met"] for item in normalized_assertions) else "failed"
        if row["status"] != status:
            raise EvaluationError("eval_judge_inconsistent_verdict")
        normalized.append(
            {
                "eval_id": eval_id,
                "status": status,
                "assertions": normalized_assertions,
                "reason": str(row.get("reason") or ""),
            }
        )
    if observed != set(expected):
        raise EvaluationError("eval_judge_missing_case")
    computed_overall = "passed" if all(row["status"] == "passed" for row in normalized) else "failed"
    if value["overall"] != computed_overall:
        raise EvaluationError("eval_judge_inconsistent_overall")
    order = {case["id"]: index for index, case in enumerate(expected.values())}
    return sorted(normalized, key=lambda row: order[row["eval_id"]])


def _latest_metadata(profile_home: Path, run: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    receipt_bytes = (run / "eval-receipt.json").read_bytes()
    artifact_hashes: dict[str, str] = {}
    for path in sorted(run.rglob("*")):
        if path.is_symlink():
            raise EvaluationError("eval_artifact_symlink")
        if path.is_file():
            artifact_hashes[path.relative_to(run).as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return {
        "schema_version": 1,
        "run_id": receipt["run_id"],
        "status": receipt["status"],
        "index": f"{receipt['run_id']}/dossier/index.html",
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "artifact_sha256": artifact_hashes,
        "updated_at": time.time(),
    }


def run_evaluation(
    profile_home: Path,
    *,
    root: Path | None = None,
    command_runner: CommandRunner = runtime.run_command,
    timeout: int = 900,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run each cadence once, judge all cases once, and build its dossier."""
    if timeout < 1:
        raise EvaluationError("eval_timeout_invalid")
    root = (root or package_root()).resolve()
    profile_home = profile_home.expanduser().resolve()
    _require_persistent_docker_workspace(profile_home, command_runner)
    run, suites = prepare_run(profile_home, root=root, run_id=run_id)
    started = time.time()
    automation_runs: dict[str, dict[str, Any]] = {}
    outputs: dict[str, list[str]] = {}
    for cadence in CADENCES:
        cadence_result = _run_cadence(
            profile_home, run, cadence, suites[cadence],
            command_runner=command_runner, timeout=timeout,
        )
        automation_runs[cadence] = {
            "status": cadence_result["status"],
            "session_id": cadence_result["session_id"],
        }
        outputs.update(cadence_result["outputs"])
    artifacts = _artifact_payload(run, outputs)
    judge_arguments = [
        "hermes", "chat", "--quiet", "--toolsets", NO_TOOLS_TOOLSET,
        "--reasoning", "none", "--ignore-rules", "--query-file", "-", "--source", "tool",
        "--in", str(profile_home / "workspace"), "--max-turns", "1",
        "--run-budget", str(timeout),
    ]
    judged = command_runner(
        judge_arguments,
        profile_home,
        input_text=judge_prompt(run.name, suites, artifacts),
        check=False,
        timeout=timeout + 30,
    )
    if judged.returncode:
        raise EvaluationError("eval_judge_failed")
    judge_calls = 1
    try:
        judgments = validate_judgment(_json_object(judged.stdout or ""), suites)
    except EvaluationError:
        repaired = command_runner(
            judge_arguments,
            profile_home,
            input_text=judge_repair_prompt(judged.stdout or "", suites),
            check=False,
            timeout=timeout + 30,
        )
        if repaired.returncode:
            raise EvaluationError("eval_judge_repair_failed")
        judge_calls = 2
        judgments = validate_judgment(_json_object(repaired.stdout or ""), suites)
    eval_results = []
    for judgment in judgments:
        eval_results.append({**judgment, "outputs": outputs[judgment["eval_id"]]})
    status = "passed" if all(row["status"] == "passed" for row in eval_results) else "failed"
    receipt = {
        "schema_version": 1,
        "run_id": run.name,
        "status": status,
        "run_mode": "analysis_only",
        "provider_mutations": 0,
        "started_at": started,
        "finished_at": time.time(),
        "automation_runs": automation_runs,
        "judge_calls": judge_calls,
        "eval_results": eval_results,
        "root_output_url": "dossier/index.html",
    }
    _write_json(run / "eval-receipt.json", receipt)
    build_static_evidence_viewer(out_dir=run / "dossier", eval_run_root=run)
    for path in (run / "dossier").rglob("*"):
        if path.is_file():
            os.chmod(path, 0o600)
        elif path.is_dir():
            os.chmod(path, 0o700)
    _write_json(profile_home / STATE_DIRECTORY / "latest.json", _latest_metadata(profile_home, run, receipt))
    return receipt


def latest_valid_index(profile_home: Path, *, root: Path | None = None) -> Path:
    """Return only a latest dossier whose metadata, receipt, and model validate."""
    root = (root or package_root()).resolve()
    state = profile_home.expanduser().resolve() / STATE_DIRECTORY
    metadata = _read_json(state / "latest.json", "eval_latest")
    run_id = metadata.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise EvaluationError("eval_latest_invalid")
    run = (state / run_id).resolve()
    if state.resolve() not in run.parents:
        raise EvaluationError("eval_latest_invalid")
    receipt_path = run / "eval-receipt.json"
    try:
        digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    except OSError as error:
        raise EvaluationError("eval_latest_receipt_missing") from error
    if digest != metadata.get("receipt_sha256"):
        raise EvaluationError("eval_latest_receipt_stale")
    expected_hashes = metadata.get("artifact_sha256")
    if not isinstance(expected_hashes, dict) or not expected_hashes:
        raise EvaluationError("eval_latest_artifact_manifest_missing")
    actual_paths: dict[str, Path] = {}
    for path in sorted(run.rglob("*")):
        if path.is_symlink():
            raise EvaluationError("eval_latest_artifact_unsafe")
        if path.is_file():
            actual_paths[path.relative_to(run).as_posix()] = path
    if set(actual_paths) != set(expected_hashes):
        raise EvaluationError("eval_latest_artifact_set_stale")
    for relative, path in actual_paths.items():
        expected = expected_hashes.get(relative)
        if not isinstance(expected, str) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise EvaluationError(f"eval_latest_artifact_stale:{relative}")
    try:
        build_evidence_model(project_root=root, eval_run_root=run)
    except ViewerError as error:
        raise EvaluationError("eval_latest_receipt_invalid") from error
    index = (run / "dossier" / "index.html").resolve()
    if run not in index.parents or not index.is_file():
        raise EvaluationError("eval_latest_index_missing")
    return index


def open_latest_dossier(
    profile_home: Path,
    *,
    root: Path | None = None,
    opener: BrowserOpener = webbrowser.open,
) -> str:
    """Open the latest validated private dossier with an injectable browser edge."""
    uri = latest_valid_index(profile_home, root=root).as_uri()
    if opener(uri) is False:
        raise EvaluationError("eval_dossier_open_failed")
    return uri
