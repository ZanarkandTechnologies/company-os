"""Bounded adapter for retained local Codex rollout records (format v1).

Session metadata and legacy or desktop item-completed message events are supported.
Reasoning, tool output, credentials and injected instructions are not exported.
Exact cwd matching precedes body reads. Unsupported/mixed history fails closed.
This is a format adapter, not a semantic reducer or another agent runtime.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .intake import IntakeError, canonical, digest
from .models import Binding, Bundle, Conversation, Message, timestamp, validate_week, week_of


MAX_LINE_BYTES = 1_048_576
MAX_SESSION_BYTES = 32 * 1_048_576
MAX_FILES = 10000
MAX_SCAN_BYTES = 64 * 1_048_576


def _path_key(value: str) -> str:
    # Do not infer that a worktree/subdirectory is the configured repository.
    return os.path.normcase(os.path.normpath(value))


def _lines(path: Path, budget: list[int]):
    total = 0
    with path.open("rb") as stream:
        while True:
            line = stream.readline(MAX_LINE_BYTES + 1)
            if not line:
                return
            total += len(line)
            budget[0] -= len(line)
            if budget[0] < 0:
                raise IntakeError("codex_scan_limit")
            if len(line) > MAX_LINE_BYTES or total > MAX_SESSION_BYTES:
                raise IntakeError("codex_session_too_large")
            if not line.endswith(b"\n"):
                raise IntakeError("codex_session_incomplete_retry_after_turn")
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError()
            except (ValueError, UnicodeError) as error:
                raise IntakeError("codex_session_format_unsupported") from error
            yield value


def read_session(path: Path, binding: Binding, week: str, timezone_name: str, budget: list[int] | None = None) -> Conversation | None:
    records = _lines(path, budget if budget is not None else [MAX_SCAN_BYTES])
    try:
        header = next(records, {})
        metadata = header.get("payload", {})
        if header.get("type") != "session_meta" or not isinstance(metadata, dict):
            raise IntakeError("codex_session_metadata_missing")
        if not isinstance(metadata.get("cwd"), str) or not metadata["cwd"].strip():
            raise IntakeError("codex_session_project_missing")
        if _path_key(str(metadata.get("cwd", ""))) != _path_key(binding.cwd or ""):
            return None
        session_id = metadata.get("id")
        if not isinstance(session_id, str):
            raise IntakeError("codex_session_identity_missing")
        messages: list[Message] = []
        message_format: str | None = None
        for ordinal, record in enumerate(records, start=2):
            payload = record.get("payload", {})
            if not isinstance(payload, dict):
                raise IntakeError("codex_session_format_unsupported")
            if record.get("type") == "compacted" or payload.get("type") in {"thread_rolled_back", "turn_aborted"}:
                # Do not accidentally publish superseded or incomplete history as current.
                raise IntakeError("codex_history_requires_manual_selection")
            if record.get("type") == "turn_context" and payload.get("cwd") and (
                _path_key(payload["cwd"]) != _path_key(binding.cwd or "")
            ):
                raise IntakeError("codex_session_project_changed")
            if record.get("type") != "event_msg":
                continue
            event_type = payload.get("type")
            if event_type in {"user_message", "agent_message"}:
                current_format = "legacy"
                role = "user" if event_type == "user_message" else "assistant"
                body = payload.get("message")
                message_id = f"line-{ordinal}"
            elif event_type == "item_completed":
                item = payload.get("item")
                if not isinstance(item, dict) or item.get("type") not in {"UserMessage", "AgentMessage"}:
                    continue
                current_format = "desktop"
                role = "user" if item["type"] == "UserMessage" else "assistant"
                if role == "assistant" and item.get("phase") == "commentary":
                    continue
                if role == "assistant" and item.get("phase") != "final_answer":
                    raise IntakeError("codex_assistant_phase_unsupported")
                if not isinstance(item.get("id"), str) or not item["id"]:
                    raise IntakeError("codex_message_identity_missing")
                content = item.get("content")
                if not isinstance(content, list) or not all(isinstance(part, dict) for part in content):
                    raise IntakeError("codex_message_format_unsupported")
                text_parts = [part.get("text") for part in content if part.get("type") in {"text", "Text"}]
                if not all(isinstance(part, str) for part in text_parts):
                    raise IntakeError("codex_message_format_unsupported")
                # Attachments have no text representation in this adapter.
                if not text_parts:
                    continue
                body = "\n".join(text_parts)
                message_id = "item-" + digest(canonical(item["id"]))
            else:
                continue
            if message_format is not None and message_format != current_format:
                raise IntakeError("codex_mixed_message_formats")
            message_format = current_format
            try:
                occurred_at = record["timestamp"]
                if week_of(timestamp(occurred_at), timezone_name) != week:
                    continue
                if not isinstance(body, str) or not body.strip():
                    raise ValueError()
                messages.append(Message(message_id=message_id, role=role, occurred_at=occurred_at, text=body))
            except (ValueError, TypeError, KeyError) as error:
                raise IntakeError("codex_message_format_unsupported") from error
            if len(messages) > 400:
                raise IntakeError("codex_message_limit")
        if not messages:
            return None
        return Conversation(conversation_id=session_id, revision=digest(canonical([item.model_dump() for item in messages])),
                            source_reference=f"codex-local:{session_id}", messages=messages)
    finally:
        records.close()


def collect(binding: Binding, project_id: str, week: str, timezone_name: str) -> Bundle:
    validate_week(week)
    if binding.source != "codex_local" or not binding.session_roots:
        raise IntakeError("codex_session_roots_missing")
    conversations: dict[str, Conversation] = {}
    failures: set[str] = set()
    visited = 0
    budget = [MAX_SCAN_BYTES]
    for raw_root in binding.session_roots:
        root = Path(raw_root).expanduser()
        if root.name not in {"sessions", "archived_sessions"}:
            raise IntakeError("codex_root_must_be_session_directory")
        if not root.is_absolute() or not root.is_dir():
            failures.add("codex_session_root_unavailable")
            continue
        if any(parent.is_symlink() or getattr(parent, "is_junction", lambda: False)()
               for parent in (root, *root.parents)):
            failures.add("codex_session_links_forbidden")
            continue
        def walk_error(_: OSError) -> None:
            failures.add("codex_directory_unreadable")
        for directory, subdirs, names in os.walk(root, followlinks=False, onerror=walk_error):
            allowed_subdirs = sorted(name for name in subdirs if not (
                (Path(directory) / name).is_symlink() or getattr(Path(directory) / name, "is_junction", lambda: False)()
            ))
            if len(allowed_subdirs) != len(subdirs):
                failures.add("codex_session_links_forbidden")
            subdirs[:] = allowed_subdirs
            for name in sorted(names):
                if not name.startswith("rollout-") or not name.endswith(".jsonl"):
                    continue
                visited += 1
                if visited > MAX_FILES:
                    raise IntakeError("codex_file_limit")
                path = Path(directory) / name
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                    failures.add("codex_session_links_forbidden")
                    continue
                try:
                    item = read_session(path, binding, week, timezone_name, budget)
                    if item:
                        prior = conversations.get(item.conversation_id)
                        if prior and prior != item:
                            raise IntakeError("codex_duplicate_session_conflict")
                        conversations[item.conversation_id] = item
                        if len(conversations) > 40:
                            raise IntakeError("codex_conversation_limit")
                except IntakeError as error:
                    if str(error) in {"codex_duplicate_session_conflict", "codex_conversation_limit", "codex_scan_limit"}:
                        raise
                    failures.add(str(error))
                except (OSError, ValueError, TypeError):
                    failures.add("codex_session_unreadable")
    note = "Local retained user and final assistant text only; cloud, tools, attachments and unavailable history are not covered."
    if failures:
        note += " Gaps: " + ", ".join(sorted(failures)) + "."
    # Partial describes the product coverage even when all readable local files passed.
    return Bundle(schema_version=1, project_id=project_id, member_id=binding.member_id,
                  source="codex_local", week=week, timezone=timezone_name,
                  collected_at=datetime.now(timezone.utc).isoformat(), coverage="partial",
                  coverage_note=note, conversations=sorted(conversations.values(), key=lambda item: item.conversation_id))
