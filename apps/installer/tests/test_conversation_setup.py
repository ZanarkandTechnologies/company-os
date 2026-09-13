from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.installer.conversation_setup import (
    default_intake_root,
    discover_codex_session_roots,
    enabled_sources,
    load_policy_if_present,
    save_policy,
)


class ConversationSetupTests(unittest.TestCase):
    def test_feature_answers_select_only_supported_sources(self) -> None:
        self.assertEqual(enabled_sources("Conversation context is disabled. Do not read conversation sources."), ())
        self.assertEqual(enabled_sources("Enable only chatgpt_manual bindings."), ("chatgpt_manual",))
        self.assertEqual(
            enabled_sources("Enable chatgpt_manual, codex_local or codex_manual bindings."),
            ("chatgpt_manual", "codex_local", "codex_manual"),
        )

    def test_default_storage_is_private_profile_state(self) -> None:
        profile = Path("C:/Hermes/profiles/company-os")
        root = default_intake_root(profile)
        self.assertEqual(root.name, "conversations")
        self.assertIn("company-os", root.parts)

    def test_codex_discovery_returns_only_existing_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            (home / ".codex" / "sessions").mkdir(parents=True)
            self.assertEqual(discover_codex_session_roots(home), [str((home / ".codex" / "sessions").absolute())])

    def test_policy_write_validates_and_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch(
            "apps.installer.conversation_setup.private_root", side_effect=lambda path: path.resolve()
        ):
            root = Path(temporary)
            saved = save_policy(
                root,
                timezone="Asia/Kuala_Lumpur",
                projects={"PROJ-ONE": [{
                    "source": "codex_local",
                    "member_id": "PERSON-ONE",
                    "cwd": str(root.resolve()),
                    "session_roots": [],
                }]},
            )
            payload = json.loads(saved.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(load_policy_if_present(root), payload)


if __name__ == "__main__":
    unittest.main()
