"""Load feature bindings and publish validated setup files atomically."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA_VERSION = 4
NOTION_ROLE_BY_QUESTION = {
    "daily.projects": "projects",
    "daily.work": "tasks",
    "daily.meetings": "meetings",
    "daily.people": "people",
    "daily.context_sources": "projects",
    "daily.progress_route": "tasks",
    "daily.documentation_route": "tasks",
    "weekly.reports_destination": "reports",
    "weekly.sops_destination": "sops",
    "weekly.decisions_destination": "decisions",
    "weekly.project_memory_destination": "projects",
    "weekly.employee_memory_destination": "people",
}


class FeatureSetupError(ValueError):
    """A safe, operator-actionable feature setup failure."""


@dataclass(frozen=True)
class SetupState:
    answers: dict[str, str]
    selections: dict[str, tuple[str, ...]]
    provider_requirements: dict[str, tuple[str, ...]]
    provider_targets: dict[str, dict[str, str]]


def load_state(path: Path) -> SetupState:
    if not path.is_file():
        return SetupState({}, {}, {}, {})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FeatureSetupError(f"setup_answers_unreadable:{path}") from error
    if isinstance(payload, dict) and payload.get("schema_version") == 5:
        from apps.installer.prompt_generation import discover, migrate, rendered_answers, validate_values
        _, questions = discover(path.parent.parent)
        payload = migrate(payload, questions)
        values = payload.get("values", {})
        validate_values(questions, values)
        return SetupState(*rendered_answers(questions, values))
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
    normalized_selections: dict[str, tuple[str, ...]] = {}
    for key, values in selections.items():
        if not isinstance(key, str) or not isinstance(values, list) or not values or not all(
            isinstance(value, str) and value for value in values
        ):
            raise FeatureSetupError("setup_selections_invalid")
        normalized_selections[key] = tuple(values)
    return SetupState(
        normalized,
        normalized_selections,
        normalized_requirements,
        normalized_targets,
    )


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
    unsupported = required - {"notion", "multica", "google_drive", "gmail", "discord", "telegram", "whatsapp", "local"}
    if unsupported:
        raise FeatureSetupError("provider_capability_not_certified:" + ",".join(sorted(unsupported)))
    for key, targets in provider_targets.items():
        answer = answers.get(key, "")
        for target in targets.values():
            if target not in answer:
                raise FeatureSetupError(f"provider_target_not_rendered:{key}")
    def target_provider(key: str) -> str:
        return key.split(":", 1)[0]

    unsupported_notion = sorted(
        key
        for key, values in provider_targets.items()
        if any(target_provider(target_key) == "notion" for target_key in values)
        and key not in NOTION_ROLE_BY_QUESTION
    )
    if unsupported_notion:
        raise FeatureSetupError("notion_role_unsupported:" + ",".join(unsupported_notion))
    notion_targets = sorted({
        (NOTION_ROLE_BY_QUESTION[key], target)
        for key, values in provider_targets.items()
        for target_key, target in values.items()
        if target_provider(target_key) == "notion"
    })
    for _, target in notion_targets:
        _require_provider_url(target, {"notion.so", "www.notion.so", "app.notion.com"}, "notion_target_invalid")
    if "notion" in required and not notion_targets:
        raise FeatureSetupError("notion_source_required_for_notion_comments")
    for index, (role, target) in enumerate(notion_targets, 1):
        add(role, "notion", target, case_suffix=f":{index}")

    drive_targets = sorted({
        target
        for values in provider_targets.values()
        for target_key, target in values.items()
        if target_provider(target_key) == "google_drive"
    })
    for target in drive_targets:
        _require_provider_url(target, {"drive.google.com"}, "google_drive_target_invalid")
    if "google_drive" in required and not drive_targets:
        raise FeatureSetupError("google_drive_destination_required")
    for index, drive_target in enumerate(drive_targets, 1):
        add("storage", "google_drive", drive_target, case_suffix=f":{index}")

    multica_targets = sorted({
        target
        for key, values in provider_targets.items()
        for target_key, target in values.items()
        if target_provider(target_key) == "multica"
    })
    if "multica" in required and not multica_targets:
        raise FeatureSetupError("multica_source_required")
    for index, target in enumerate(multica_targets, 1):
        add("tasks", "multica", target, case_suffix=f":{index}")

    if "gmail" in required:
        add("operator_email", "gmail", "authenticated-gmail-profile")
    return bindings


def bindings_for_workspace(workspace: Path, catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve integration bindings from the workspace's saved setup answers."""
    from apps.installer.provider_catalog import CatalogError

    answers_path = workspace.parent / "config" / "setup-answers.json"
    try:
        if not answers_path.is_file():
            raise FeatureSetupError(f"setup_answers_missing:{answers_path}")
        state = load_state(answers_path)
        return selected_bindings(
            state.answers,
            catalog,
            state.provider_requirements,
            state.provider_targets,
        )
    except FeatureSetupError as error:
        raise CatalogError(str(error)) from error


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
