"""Build the evidence viewer from PM eval catalogs and one shared run receipt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ViewerError(ValueError):
    pass


def _read(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ViewerError(f"{label} is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ViewerError(f"{label} must be an object")
    return value


def _catalog(project: Path, run: Path) -> list[dict[str, Any]]:
    evaluations: list[dict[str, Any]] = []
    frozen = _read(run / "catalog.json", "frozen catalog") if (run / "catalog.json").exists() else None
    for layer in ("daily", "weekly", "automation"):
        if frozen is not None:
            cases = frozen.get(layer, [])
        else:
            relative = "automations/evals/evals.json" if layer == "automation" else f"skills/pm-{layer}/evals/evals.json"
            cases = _read(project / relative, f"{layer} evals").get("evals", [])
        for position, case in enumerate(cases):
            metadata = case.get("metadata") or {}
            tags = metadata.get("tags") or []
            evaluations.append({
                "id": case["id"],
                "cadence": layer,
                "name": metadata.get("title") or case["id"].replace("_", " ").title(),
                "description": metadata.get("notes") or case["expected_output"],
                "expectedOutput": case["expected_output"],
                "requiredAssertions": case.get("assertions", []),
                "showcase": "showcase" in tags,
                "position": position,
            })
    ids = [row["id"] for row in evaluations]
    if len(ids) != len(set(ids)):
        raise ViewerError("eval IDs must be unique across catalogs")
    return sorted(evaluations, key=lambda row: (("daily", "weekly", "automation").index(row["cadence"]), not row["showcase"], row["position"]))


def _result_index(receipt: dict[str, Any], known_ids: set[str]) -> dict[str, dict[str, Any]]:
    rows = receipt.get("eval_results") or []
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ViewerError("eval_results must be a list of objects")
    results: dict[str, dict[str, Any]] = {}
    for row in rows:
        eval_id = row.get("eval_id")
        if not isinstance(eval_id, str) or eval_id not in known_ids:
            raise ViewerError(f"eval result targets unknown eval: {eval_id}")
        if eval_id in results:
            raise ViewerError(f"duplicate eval result: {eval_id}")
        results[eval_id] = row
    return results


def _assertion_results(required: list[str], result: dict[str, Any]) -> list[dict[str, Any]]:
    observed = result.get("assertions") or []
    if not isinstance(observed, list) or len(observed) != len(required):
        raise ViewerError(f"{result.get('eval_id')} assertion count does not match its eval catalog")
    indexed: dict[int, dict[str, Any]] = {}
    for row in observed:
        if not isinstance(row, dict) or not isinstance(row.get("index"), int):
            raise ViewerError(f"{result.get('eval_id')} assertions require integer indexes")
        index = row["index"]
        if index in indexed or index < 0 or index >= len(required):
            raise ViewerError(f"{result.get('eval_id')} has an invalid assertion index")
        indexed[index] = row
    assertions = []
    for index, assertion in enumerate(required):
        row = indexed.get(index)
        if row is None:
            raise ViewerError(f"{result.get('eval_id')} omits assertion {index}")
        met = row.get("met")
        status = "pass" if met is True else "fail" if met is False else "needs_information"
        evidence = row.get("evidence") or []
        if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
            raise ViewerError(f"{result.get('eval_id')} assertion evidence must be strings")
        if met is True and not evidence:
            raise ViewerError(f"{result.get('eval_id')} cannot pass assertion {index} without evidence")
        assertions.append({"assertion": assertion, "status": status, "evidence": evidence})
    return assertions


def _outputs(run: Path, result: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    paths = list(result.get("outputs") or [])
    delta = (result.get("execution") or {}).get("file_delta")
    if delta and delta not in paths:
        paths.append(delta)
    for relative in paths:
        if not isinstance(relative, str):
            raise ViewerError(f"{result.get('eval_id')} output paths must be strings")
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ViewerError(f"unsafe eval output path: {relative}")
        path = (run / candidate).resolve()
        if run not in path.parents or not path.is_file():
            raise ViewerError(f"eval output does not exist inside the run: {relative}")
        outputs.append({
            "id": relative,
            "label": "File changes" if relative == delta else path.name,
            "kind": {".md": "Markdown", ".json": "JSON"}.get(path.suffix.lower(), "Artifact"),
            "state": "observed",
            "url": relative,
            "markdown": path.read_text(encoding="utf-8"),
        })
    return outputs


def _validate_receipt(receipt: dict[str, Any]) -> str:
    automation_runs = receipt.get("automation_runs")
    allowed_statuses = {"passed", "failed", "not_run", "blocked_by_setup"}
    if not isinstance(automation_runs, dict) or set(automation_runs) != {"daily", "weekly"}:
        raise ViewerError("Eval receipt must contain exactly one Daily and one Weekly automation result")
    if any(
        not isinstance(automation_runs[cadence], dict)
        or automation_runs[cadence].get("status") not in allowed_statuses
        for cadence in ("daily", "weekly")
    ):
        raise ViewerError("Daily and Weekly automation results require valid statuses")
    mode = receipt.get("run_mode")
    mutations = receipt.get("provider_mutations")
    if mode == "analysis_only" and mutations == 0:
        return mode
    if mode == "analysis_only" and mutations is None and receipt.get("safety_verified") is False:
        return "unverified_trace"
    if (
        mode == "isolated_eval"
        and isinstance(mutations, int)
        and mutations >= 0
        and isinstance(receipt.get("isolation_scope"), str)
        and receipt.get("isolation_scope")
        and receipt.get("read_back_verified") is True
    ):
        return mode
    raise ViewerError("Eval receipt must prove analysis-only safety or a read-back-verified isolated eval scope")


def build_evidence_model(*, project_root: Path, eval_run_root: Path) -> dict[str, Any]:
    project = Path(project_root).resolve()
    run = Path(eval_run_root).resolve()
    receipt = _read(run / "eval-receipt.json", "eval receipt")
    run_mode = _validate_receipt(receipt)
    catalog = _catalog(project, run)
    results = _result_index(receipt, {row["id"] for row in catalog})
    selected = receipt.get("selected_eval_ids")
    if selected is not None and (not isinstance(selected, list) or not all(isinstance(item, str) for item in selected)):
        raise ViewerError("selected_eval_ids must be a list of strings")

    evaluations = []
    for case in catalog:
        run_state = (receipt.get("automation_runs") or {}).get(case["cadence"], {})
        run_status = run_state.get("status")
        result = results.get(case["id"])
        if (selected is not None and case["id"] not in selected) or (case["cadence"] == "automation" and result is None):
            status, status_note, assertions, outputs = "not_run", "Not executed in this run.", [], []
        elif result is not None:
            assertions = _assertion_results(case["requiredAssertions"], result)
            outputs = _outputs(run, result)
            status = "pass" if result.get("status") == "passed" and assertions and all(row["status"] == "pass" for row in assertions) else "fail"
            status_note = result.get("reason") or ("Every required assertion passed." if status == "pass" else "One or more checks failed.")
        elif run_status in {"failed", "not_run", "blocked_by_setup"}:
            failed = run_status == "failed"
            status = "fail" if failed else "not_run"
            status_note = "No output was accepted." if failed else "No operated output exists."
            assertions: list[dict[str, Any]] = []
            outputs: list[dict[str, Any]] = []
        elif run_status != "passed":
            raise ViewerError(f"unexpected {case['cadence']} automation status: {run_status}")
        else:
            status, status_note, assertions, outputs = "unjudged", "No result was supplied by the run.", [], []
        evaluations.append({
            "id": case["id"],
            "cadence": case["cadence"],
            "name": case["name"],
            "description": case["description"],
            "claim": case["expectedOutput"],
            "showcase": case["showcase"],
            "outputs": outputs,
            "status": status,
            "statusNote": status_note,
            "assertions": assertions,
        })

    assertions = [row for evaluation in evaluations for row in evaluation["assertions"]]
    return {
        "schemaVersion": "company-os-evidence-viewer@4.0.0",
        "runKind": "shared-automation-eval",
        "runStatus": receipt.get("status", "unknown"),
        "deliveryStatus": run_mode,
        "rootOutputUrl": receipt.get("root_output_url"),
        "activityLogAvailable": (run / "activity.jsonl").is_file(),
        "metrics": {
            "evaluations": {"total": len(evaluations), "passed": sum(row["status"] == "pass" for row in evaluations)},
            "checks": {"total": len(assertions), "passed": sum(row["status"] == "pass" for row in assertions)},
            "outputs": {"total": sum(len(row["outputs"]) for row in evaluations)},
        },
        "evaluations": evaluations,
    }
