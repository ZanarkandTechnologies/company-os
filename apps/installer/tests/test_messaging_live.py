"""Explicitly gated provider-backed Telegram acceptance test."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from apps.installer.schemas.workspace import MessageType, parse_workspace_communications
from apps.installer.cli.flows.messaging import send_connection_test


ROOT = Path(__file__).resolve().parents[3]
LIVE_ENABLED = os.environ.get("COMPANY_OS_RUN_TELEGRAM_LIVE") == "1"
PROFILE = os.environ.get("COMPANY_OS_PROFILE", "").strip()


@unittest.skipUnless(
    LIVE_ENABLED and PROFILE,
    "set COMPANY_OS_RUN_TELEGRAM_LIVE=1 and COMPANY_OS_PROFILE to send one live test",
)
class LiveTelegramMessagingTest(unittest.TestCase):
    def test_configured_owner_receives_one_bounded_telegram_message(self) -> None:
        profile_home = Path(PROFILE).expanduser().resolve()
        config = parse_workspace_communications(
            (ROOT / "workspace.hermes.md").read_text(encoding="utf-8")
        )
        owner_reports = [
            binding
            for binding in config.communications
            if binding.message is MessageType.OWNER_REPORT
        ]
        self.assertEqual(len(owner_reports), 1)

        receipt, provider_success = send_connection_test(
            profile_home,
            owner_reports[0],
            config.communications,
        )

        self.assertTrue(provider_success)
        self.assertEqual(receipt.app.value, "telegram")
        self.assertIsNotNone(receipt.exact_target)
        self.assertIsNotNone(receipt.target_sha256)
        self.assertIsNotNone(receipt.message_id)


if __name__ == "__main__":
    unittest.main()
