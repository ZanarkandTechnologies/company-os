"""Deterministic storage and validation for guided conversation intake setup."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from apps.installer.feature_setup import FeatureSetupError
from plugins.conversation_context.intake import IntakeError, private_root, read_project
from plugins.conversation_context.models import Policy

ENV_NAME = "COMPANY_OS_CONVERSATION_INTAKE"
DISABLED_ANSWER = "Conversation context is disabled. Do not read conversation sources."


class ConversationSetupError(FeatureSetupError):
    """A redacted, operator-actionable setup failure."""


@dataclass(frozen=True)
class ConversationStatus:
    project_id: str
    status: str
    sources: tuple[str, ...]
    bindings: int
    conversations: int
    messages: int
    gaps: tuple[str, ...]


def enabled_sources(answer: str) -> tuple[str, ...]:
    if not answer or answer == DISABLED_ANSWER:
        return ()
    sources: list[str] = []
    if "chatgpt_manual" in answer:
        sources.append("chatgpt_manual")
    if "codex_local" in answer:
        sources.extend(("codex_local", "codex_manual"))
    return tuple(sources)


def default_intake_root(profile_home: Path) -> Path:
    if os.name == "nt" and profile_home.anchor:
        return Path(profile_home.anchor) / "CompanyOSPrivate" / profile_home.name / "conversations"
    return Path.home() / ".local" / "share" / "company-os-private" / profile_home.name / "conversations"


def discover_codex_session_roots(user_home: Path | None = None) -> list[str]:
    base = (user_home or Path.home()) / ".codex"
    return [str(path.absolute()) for path in (base / "sessions", base / "archived_sessions") if path.is_dir()]


def load_policy_if_present(root: Path) -> dict[str, Any] | None:
    path = root / "policy.json"
    if not path.is_file():
        return None
    try:
        return Policy.model_validate_json(path.read_bytes()).model_dump()
    except (OSError, ValueError) as error:
        raise ConversationSetupError("conversation_policy_invalid") from error


def save_policy(root: Path, *, timezone: str, projects: dict[str, list[dict[str, Any]]]) -> Path:
    try:
        root.mkdir(parents=True, exist_ok=True)
        private_root(root)
        policy = Policy.model_validate({"schema_version": 1, "timezone": timezone, "projects": projects})
    except (OSError, ValueError, IntakeError) as error:
        code = str(error) if isinstance(error, IntakeError) else "conversation_policy_invalid"
        raise ConversationSetupError(code) from error
    destination = root / "policy.json"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".policy-", dir=root)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(policy.model_dump(), stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return destination


def current_week(timezone: str) -> str:
    year, week, _ = datetime.now(ZoneInfo(timezone)).isocalendar()
    return f"{year:04d}-W{week:02d}"


def test_policy(root: Path, project_id: str, sources: tuple[str, ...]) -> ConversationStatus:
    policy = Policy.model_validate_json((root / "policy.json").read_bytes())
    result = read_project(root, project_id, current_week(policy.timezone), list(sources))
    conversations = result.pop("conversations", [])
    result.pop("trust", None)
    coverage = result.get("coverage", [])
    gaps = tuple(str(item.get("note", "source_unavailable")) for item in coverage if item.get("status") != "complete")
    return ConversationStatus(
        project_id=project_id,
        status=str(result.get("status", "partial")),
        sources=tuple(sorted({str(item.get("source")) for item in coverage})),
        bindings=len(coverage),
        conversations=len(conversations),
        messages=sum(len(item.get("messages", [])) for item in conversations),
        gaps=gaps,
    )
