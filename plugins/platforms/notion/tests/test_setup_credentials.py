from __future__ import annotations

import io
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from apps.installer import runtime
from plugins.platforms.notion import api, onboarding


class _Response:
    status = 200

    def read(self) -> bytes:
        return b'{"object":"user","id":"test-bot"}'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class NotionSetupCredentialTests(unittest.TestCase):
    def test_candidate_token_is_sent_only_in_the_authorization_header(self) -> None:
        captured = []

        def open_request(request, timeout):
            captured.append((request, timeout))
            return _Response()

        with patch.object(api.urllib.request, "urlopen", side_effect=open_request):
            api.validate_token("secret-token")

        request, timeout = captured[0]
        self.assertEqual(request.full_url, "https://api.notion.com/v1/users/me")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")
        self.assertEqual(timeout, 15)

    def test_invalid_and_unavailable_token_failures_are_redacted(self) -> None:
        invalid = urllib.error.HTTPError(
            "https://api.notion.com/v1/users/me", 401, "no", {}, io.BytesIO()
        )
        unavailable = urllib.error.URLError("offline")
        for failure, code in (
            (invalid, "notion_token_invalid"),
            (unavailable, "notion_unavailable"),
        ):
            with self.subTest(code=code):
                with patch.object(api.urllib.request, "urlopen", side_effect=failure):
                    with self.assertRaisesRegex(api.NotionCredentialError, code):
                        api.validate_token("secret-token")

    def test_rejected_saved_token_is_replaced_only_after_validation(self) -> None:
        profile = Path("/tmp/company-os-profile")
        with patch.object(runtime, "read_profile_secret", return_value="old-token"):
            with patch.object(onboarding, "_prompt_secret", return_value="new-token"):
                with patch.object(
                    api,
                    "validate_token",
                    side_effect=[api.NotionCredentialError("notion_token_invalid"), None],
                ):
                    with patch.object(runtime, "save_profile_secret") as save_secret:
                        onboarding._configure_notion_token(profile)
        save_secret.assert_called_once_with(profile, "NOTION_TOKEN", "new-token")

    def test_network_failure_preserves_saved_token_without_prompting(self) -> None:
        profile = Path("/tmp/company-os-profile")
        with patch.object(runtime, "read_profile_secret", return_value="old-token"):
            with patch.object(onboarding, "_prompt_secret") as prompt:
                with patch.object(
                    api,
                    "validate_token",
                    side_effect=api.NotionCredentialError("notion_unavailable"),
                ):
                    with patch.object(runtime, "save_profile_secret") as save_secret:
                        with self.assertRaisesRegex(
                            runtime.RuntimeSetupError, "notion_unavailable"
                        ):
                            onboarding._configure_notion_token(profile)
        prompt.assert_not_called()
        save_secret.assert_not_called()

    def test_webhook_setup_requires_and_saves_a_valid_agent_trigger(self) -> None:
        profile = Path("/tmp/company-os-profile")
        with patch.object(onboarding, "_configure_notion_token"), patch.object(
            runtime, "read_profile_secret", return_value=None
        ), patch.object(
            onboarding,
            "_prompt_text",
            side_effect=["company os", "@companyos", "https://test.ngrok-free.app"],
        ), patch.object(
            onboarding, "_prompt_secret", return_value="ngrok-token"
        ), patch.object(
            runtime,
            "normalize_webhook_url",
            return_value="https://test.ngrok-free.app/notion/webhook",
        ), patch.object(runtime, "begin_ngrok_update"), patch.object(
            runtime, "configure_notion_webhook"
        ), patch.object(runtime, "save_ngrok_config"), patch.object(
            runtime, "save_profile_secret"
        ) as save:
            onboarding._configure_webhook(profile)
        save.assert_called_once_with(profile, "NOTION_COMMENT_TRIGGER", "@companyos")

if __name__ == "__main__":
    unittest.main()
