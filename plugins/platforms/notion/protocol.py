"""Pure protocol and state helpers for the Notion webhook adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

MAX_BODY_BYTES = 1_048_576
MAX_SEEN_EVENTS = 512
SEEN_TTL_SECONDS = 86_400
MAX_REPLY_TARGETS = 512
REPLY_TARGET_TTL_SECONDS = 86_400


def valid_signature(raw_body: bytes, header: str, verification_token: str) -> bool:
    if not header.startswith("sha256=") or not verification_token:
        return False
    expected = "sha256=" + hmac.new(
        verification_token.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected.encode("ascii"), header.encode("ascii", "ignore"))


class WebhookState:
    """Owner-only token storage plus bounded, persistent event deduplication."""

    def __init__(self, path: Path, now=time.time):
        self.path = path
        self.now = now

    def load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {"verification_token": "", "workspace_id": "", "seen": {}, "reply_targets": {}, "last_reply": {}}
        return {
            "verification_token": str(data.get("verification_token") or ""),
            "workspace_id": str(data.get("workspace_id") or ""),
            "seen": data.get("seen") if isinstance(data.get("seen"), dict) else {},
            "reply_targets": data.get("reply_targets") if isinstance(data.get("reply_targets"), dict) else {},
            "last_reply": data.get("last_reply") if isinstance(data.get("last_reply"), dict) else {},
        }

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix="notion-webhook-", dir=self.path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(data, stream, separators=(",", ":"))
                stream.write("\n")
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def capture_token(self, token: str) -> bool:
        token = token.strip()
        if not token:
            return False
        data = self.load()
        if data["verification_token"]:
            return hmac.compare_digest(data["verification_token"], token)
        data["verification_token"] = token
        self.save(data)
        return True

    def remember_workspace(self, workspace_id: str) -> bool:
        workspace_id = workspace_id.strip()
        if not workspace_id:
            return False
        data = self.load()
        if data["workspace_id"]:
            return hmac.compare_digest(data["workspace_id"], workspace_id)
        data["workspace_id"] = workspace_id
        self.save(data)
        return True

    def mark_once(self, event_id: str) -> bool:
        event_id = event_id.strip()
        if not event_id:
            return False
        data = self.load()
        cutoff = self.now() - SEEN_TTL_SECONDS
        seen = {
            str(key): float(value)
            for key, value in data["seen"].items()
            if isinstance(value, (int, float)) and float(value) >= cutoff
        }
        if event_id in seen:
            return False
        seen[event_id] = self.now()
        data["seen"] = dict(sorted(seen.items(), key=lambda item: item[1])[-MAX_SEEN_EVENTS:])
        self.save(data)
        return True

    def remember_reply_target(
        self,
        comment_id: str,
        discussion_id: str,
        *,
        allow_silence: bool = False,
    ) -> bool:
        """Persist the exact reply destination and whether silence is allowed."""
        comment_id = comment_id.strip()
        discussion_id = discussion_id.strip()
        if not comment_id or not discussion_id:
            return False
        data = self.load()
        cutoff = self.now() - REPLY_TARGET_TTL_SECONDS
        targets = {
            str(key): value
            for key, value in data["reply_targets"].items()
            if isinstance(value, dict)
            and isinstance(value.get("saved_at"), (int, float))
            and float(value["saved_at"]) >= cutoff
            and str(value.get("discussion_id") or "").strip()
        }
        targets[comment_id] = {
            "discussion_id": discussion_id,
            "allow_silence": bool(allow_silence),
            "saved_at": self.now(),
        }
        data["reply_targets"] = dict(
            sorted(targets.items(), key=lambda item: float(item[1]["saved_at"]))[-MAX_REPLY_TARGETS:]
        )
        self.save(data)
        return True

    def _reply_target_value(self, comment_id: str) -> dict[str, Any] | None:
        value = self.load()["reply_targets"].get(comment_id.strip())
        if not isinstance(value, dict):
            return None
        saved_at = value.get("saved_at")
        if not isinstance(saved_at, (int, float)) or float(saved_at) < self.now() - REPLY_TARGET_TTL_SECONDS:
            return None
        return value

    def reply_target(self, comment_id: str) -> str:
        value = self._reply_target_value(comment_id)
        if value is None:
            return ""
        return str(value.get("discussion_id") or "").strip()

    def reply_may_be_silent(self, comment_id: str) -> bool:
        value = self._reply_target_value(comment_id)
        return bool(value and value.get("allow_silence") is True)

    def remember_sent_reply(self, comment_id: str, message_id: str) -> bool:
        comment_id = comment_id.strip()
        message_id = message_id.strip()
        if not comment_id or not message_id:
            return False
        data = self.load()
        data["last_reply"] = {
            "comment_id": comment_id,
            "message_id": message_id,
            "sent_at": self.now(),
        }
        self.save(data)
        return True
