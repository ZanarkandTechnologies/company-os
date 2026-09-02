"""Persist feature answers and compile them into self-contained automations."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = 3
OPTIONAL_DEFAULT_ANSWERS = {
    "weekly_meeting.destination": (
        "Do not create a weekly meeting ticket. Record `skipped_disabled` and call no task integration."
    ),
    "weekly_meeting.template": (
        "Title the ticket `Weekly operating review — YYYY-Www`. Include links or paths to the weekly reports, "
        "unresolved risks, decisions needed, owners, and next-week commitments."
    ),
}
NOTION_ROLE_BY_QUESTION = {
    "daily.projects": "projects",
    "daily.work": "tasks",
    "daily.meetings": "meetings",
    "daily.people": "people",
    "daily.progress_route": "tasks",
    "daily.documentation_route": "tasks",
    "weekly.reports_destination": "reports",
    "weekly.sops_destination": "sops",
    "weekly.decisions_destination": "decisions",
    "weekly.project_memory_destination": "projects",
}
SLOT = re.compile(
    r"(?P<open><!-- setup:(?P<key>[a-z0-9_.-]+) -->)"
    r"(?P<body>.*?)"
    r"(?P<close><!-- /setup:(?P=key) -->)",
    re.DOTALL,
)


class FeatureSetupError(ValueError):
    """A safe, operator-actionable feature setup failure."""


@dataclass(frozen=True)
class RenderResult:
    path: Path
    changed: bool
    slots: tuple[str, ...]


@dataclass(frozen=True)
class SetupState:
    answers: dict[str, str]
    selections: dict[str, str]
    provider_requirements: dict[str, tuple[str, ...]]
    provider_targets: dict[str, dict[str, str]]


def with_optional_defaults(answers: dict[str, str]) -> dict[str, str]:
    """Add safe defaults for newly introduced, disabled-by-default features."""
    return {**OPTIONAL_DEFAULT_ANSWERS, **answers}


def load_answers(path: Path) -> dict[str, str]:
    return load_state(path).answers


def load_state(path: Path) -> SetupState:
    if not path.is_file():
        return SetupState({}, {}, {}, {})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FeatureSetupError(f"setup_answers_unreadable:{path}") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise FeatureSetupError("setup_answers_schema_invalid")
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        raise FeatureSetupError("setup_answers_missing")
    normalized: dict[str, str] = {}
    for key, value in answers.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
            raise FeatureSetupError("setup_answer_invalid")
        normalized[key] = value.strip()
    selections = payload.get("selections")
    requirements = payload.get("provider_requirements")
    targets = payload.get("provider_targets")
    if not isinstance(selections, dict) or not isinstance(requirements, dict) or not isinstance(targets, dict):
        raise FeatureSetupError("setup_answer_metadata_missing")
    normalized_requirements: dict[str, tuple[str, ...]] = {}
    for key, values in requirements.items():
        if not isinstance(key, str) or not isinstance(values, list) or not all(
            isinstance(value, str) and value for value in values
        ):
            raise FeatureSetupError("setup_provider_requirements_invalid")
        normalized_requirements[key] = tuple(values)
    normalized_targets: dict[str, dict[str, str]] = {}
    for key, values in targets.items():
        if not isinstance(key, str) or not isinstance(values, dict) or not all(
            isinstance(provider, str) and isinstance(target, str) and target.strip()
            for provider, target in values.items()
        ):
            raise FeatureSetupError("setup_provider_targets_invalid")
        normalized_targets[key] = {
            provider: target.strip() for provider, target in values.items()
        }
    return SetupState(
        normalized,
        {str(key): str(value) for key, value in selections.items()},
        normalized_requirements,
        normalized_targets,
    )


def serialize_state(
    answers: dict[str, str],
    selections: dict[str, str],
    provider_requirements: dict[str, tuple[str, ...]],
    provider_targets: dict[str, dict[str, str]],
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "answers": dict(sorted(answers.items())),
        "selections": dict(sorted(selections.items())),
        "provider_requirements": {
            key: list(values) for key, values in sorted(provider_requirements.items())
        },
        "provider_targets": {
            key: dict(sorted(values.items())) for key, values in sorted(provider_targets.items())
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def save_answers(
    path: Path,
    answers: dict[str, str],
    selections: dict[str, str] | None = None,
    provider_requirements: dict[str, tuple[str, ...]] | None = None,
    provider_targets: dict[str, dict[str, str]] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(
        path,
        serialize_state(
            answers,
            selections or {},
            provider_requirements or {},
            provider_targets or {},
        ),
    )


def render_text(template: str, answers: dict[str, str]) -> tuple[str, tuple[str, ...]]:
    found = [match.group("key") for match in SLOT.finditer(template)]
    if len(found) != len(set(found)):
        raise FeatureSetupError("automation_setup_slot_duplicate")
    missing = sorted(set(found) - set(answers))
    if missing:
        raise FeatureSetupError("automation_setup_answers_missing:" + ",".join(missing))

    def replace(match: re.Match[str]) -> str:
        key = match.group("key")
        value = answers[key].strip()
        if not value:
            raise FeatureSetupError(f"automation_setup_answer_empty:{key}")
        if "<!-- setup:" in value or "<!-- /setup:" in value:
            raise FeatureSetupError(f"automation_setup_answer_contains_marker:{key}")
        return f"{match.group('open')}\n{value}\n{match.group('close')}"

    rendered = SLOT.sub(replace, template)
    return rendered, tuple(found)


def render_file(path: Path, answers: dict[str, str], *, apply: bool) -> RenderResult:
    original = path.read_text(encoding="utf-8")
    rendered, slots = render_text(original, answers)
    changed = rendered != original
    if apply and changed:
        _atomic_write(path, rendered)
    return RenderResult(path=path, changed=changed, slots=slots)


def render_files(paths: tuple[Path, ...], answers: dict[str, str]) -> tuple[RenderResult, ...]:
    """Validate every automation before committing the rendered batch."""
    rendered_files: dict[Path, str] = {}
    results: list[RenderResult] = []
    for path in paths:
        original = path.read_text(encoding="utf-8")
        rendered, slots = render_text(original, answers)
        rendered_files[path] = rendered
        results.append(RenderResult(path, rendered != original, slots))
    write_batch(rendered_files)
    return tuple(results)


def selected_bindings(
    answers: dict[str, str],
    catalog: dict[str, dict[str, Any]],
    provider_requirements: dict[str, tuple[str, ...]],
    provider_targets: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Derive provider authorization needs from rendered feature answers."""
    from apps.installer.provider_catalog import provider_for

    bindings: list[dict[str, Any]] = []

    def add(role: str, provider_id: str, source: str, *, case_suffix: str = "") -> None:
        bindings.append({
            "case_id": f"{role}:{provider_id}{case_suffix}",
            "data_source": role,
            "source": source,
            "provider": provider_for(catalog, role, provider_id),
        })

    required = {provider for values in provider_requirements.values() for provider in values}
    for key, targets in provider_targets.items():
        answer = answers.get(key, "")
        for target in targets.values():
            if target not in answer:
                raise FeatureSetupError(f"provider_target_not_rendered:{key}")
    unsupported_notion = sorted(
        key
        for key, values in provider_targets.items()
        if "notion" in values and key not in NOTION_ROLE_BY_QUESTION
    )
    if unsupported_notion:
        raise FeatureSetupError("notion_role_unsupported:" + ",".join(unsupported_notion))
    notion_targets = sorted({
        (NOTION_ROLE_BY_QUESTION[key], values["notion"])
        for key, values in provider_targets.items()
        if "notion" in values
    })
    for _, target in notion_targets:
        _require_provider_url(target, {"notion.so", "www.notion.so", "app.notion.com"}, "notion_target_invalid")
    if "notion" in required and not notion_targets:
        raise FeatureSetupError("notion_source_required_for_notion_comments")
    for index, (role, target) in enumerate(notion_targets, 1):
        add(role, "notion", target, case_suffix=f":{index}")

    drive_targets = sorted({
        values["google_drive"]
        for values in provider_targets.values()
        if "google_drive" in values
    })
    for target in drive_targets:
        _require_provider_url(target, {"drive.google.com"}, "google_drive_target_invalid")
    if "google_drive" in required and not drive_targets:
        raise FeatureSetupError("google_drive_destination_required")
    for index, drive_target in enumerate(drive_targets, 1):
        add("storage", "google_drive", drive_target, case_suffix=f":{index}")

    if "gmail" in required:
        add("operator_email", "gmail", "authenticated-gmail-profile")
    return bindings


def bindings_for_workspace(workspace: Path, catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer feature answers while retaining old workspaces during migration."""
    answers_path = workspace.parent / "config" / "setup-answers.json"
    if answers_path.is_file():
        state = load_state(answers_path)
        return selected_bindings(
            state.answers,
            catalog,
            state.provider_requirements,
            state.provider_targets,
        )
    from apps.installer.provider_catalog import selected_bindings as legacy_bindings

    return legacy_bindings(workspace, catalog)


def _require_provider_url(target: str, hosts: set[str], error_code: str) -> None:
    parsed = urlparse(target)
    if parsed.scheme != "https" or parsed.hostname not in hosts:
        raise FeatureSetupError(error_code)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def write_batch(files: dict[Path, str]) -> None:
    """Commit a validated setup batch and restore prior bytes on write failure."""
    originals = {
        path: path.read_bytes() if path.is_file() else None
        for path in files
    }
    committed: list[Path] = []
    try:
        for path, content in files.items():
            _atomic_write(path, content)
            committed.append(path)
    except Exception:
        for path in reversed(committed):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                _atomic_write(path, original.decode("utf-8"))
        raise
