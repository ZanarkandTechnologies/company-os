"""Validate source identity, explicit scope, and bounded conversation evidence.

Invariants live at the intake boundary: an untrusted file cannot widen the
operator's project/member scope, smuggle extra fields, or cross the selected
week. Prose instructions cannot enforce those properties before host data is
returned to a model. This module performs no semantic extraction.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=16000)]
Source = Literal["chatgpt_manual", "codex_manual", "codex_local"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def week_of(value: datetime, timezone: str) -> str:
    year, week, _ = value.astimezone(ZoneInfo(timezone)).isocalendar()
    return f"{year:04d}-W{week:02d}"


def validate_week(value: str) -> str:
    if not re.fullmatch(r"\d{4}-W\d{2}", value):
        raise ValueError("week_invalid")
    date.fromisocalendar(int(value[:4]), int(value[6:]), 1)
    return value


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp_requires_offset")
    return result


class Binding(StrictModel):
    source: Source
    member_id: Identifier
    cwd: str | None = Field(default=None, max_length=2048)
    session_roots: list[str] = Field(default_factory=list, max_length=2)


class Policy(StrictModel):
    schema_version: Literal[1]
    timezone: str
    projects: dict[Identifier, list[Binding]]

    @model_validator(mode="after")
    def check_policy(self) -> "Policy":
        ZoneInfo(self.timezone)
        if len(self.projects) > 100:
            raise ValueError("project_limit")
        for bindings in self.projects.values():
            keys = [(item.source, item.member_id) for item in bindings]
            if len(keys) > 100 or len(set(keys)) != len(keys):
                raise ValueError("binding_limit_or_duplicate")
            for item in bindings:
                if (item.source == "codex_local") != bool(item.cwd):
                    raise ValueError("codex_local_requires_exact_cwd")
                if item.session_roots and item.source != "codex_local":
                    raise ValueError("session_roots_require_codex_local")
                if item.cwd and not (PureWindowsPath(item.cwd).is_absolute() or PurePosixPath(item.cwd).is_absolute()):
                    raise ValueError("codex_cwd_must_be_absolute")
        return self


class Message(StrictModel):
    message_id: Identifier
    role: Literal["user", "assistant"]
    occurred_at: str
    text: Text


class Conversation(StrictModel):
    conversation_id: Identifier
    revision: Identifier
    source_reference: Annotated[str, StringConstraints(min_length=1, max_length=2048)]
    task_id: Identifier | None = None
    messages: list[Message] = Field(min_length=1, max_length=400)


class Bundle(StrictModel):
    schema_version: Literal[1]
    project_id: Identifier
    member_id: Identifier
    source: Source
    week: str
    timezone: str
    collected_at: str
    coverage: Literal["complete", "partial", "unavailable", "withdrawn"]
    coverage_note: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    conversations: list[Conversation] = Field(max_length=40)

    @model_validator(mode="after")
    def check_evidence(self) -> "Bundle":
        validate_week(self.week)
        ZoneInfo(self.timezone)
        collected = timestamp(self.collected_at)
        if self.coverage in {"withdrawn", "unavailable"} and self.conversations:
            raise ValueError("unavailable_evidence_must_be_empty")
        seen: set[str] = set()
        count = 0
        for conversation in self.conversations:
            if conversation.conversation_id in seen:
                raise ValueError("duplicate_conversation")
            seen.add(conversation.conversation_id)
            message_ids: set[str] = set()
            for message in conversation.messages:
                if message.message_id in message_ids:
                    raise ValueError("duplicate_message")
                message_ids.add(message.message_id)
                occurred = timestamp(message.occurred_at)
                if week_of(occurred, self.timezone) != self.week or occurred > collected:
                    raise ValueError("message_outside_collection_window")
                count += 1
        if count > 400:
            raise ValueError("message_limit")
        return self
