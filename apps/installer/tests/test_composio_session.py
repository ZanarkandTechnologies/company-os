from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from apps.installer import composio_session
from apps.installer import provider_catalog


class FakeComposio:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []

    def __call__(self, method, path, api_key, payload=None):
        self.asserted_key = api_key
        self.calls.append((method, path, payload))
        if method == "POST" and path == composio_session.SESSION_API:
            return {
                "session_id": "trs_test",
                "mcp": {
                    "type": "http",
                    "url": "https://app.composio.dev/tool_router/v3/trs_test/mcp",
                },
            }
        if path.endswith("/link"):
            return {"redirect_url": "https://app.composio.dev/link/test"}
        if "/toolkits?" in path:
            return {
                "items": [
                    {
                        "slug": "gmail",
                        "connected_account": {"status": "ACTIVE"},
                    },
                    {"slug": "googledrive", "connected_account": None},
                ]
            }
        return {"session_id": "trs_test"}


class ComposioSessionTests(unittest.TestCase):
    @staticmethod
    def providers() -> list[dict]:
        catalog = provider_catalog.load_catalog()
        gmail = catalog["operator_email"]["providers"][0]
        drive = {
            "id": "google-drive",
            "mcp": {
                "source": "composio_session",
                "name": "composio-google",
                "toolkit": "googledrive",
                "tools": ["GOOGLEDRIVE_FIND_FILE"],
            },
        }
        return [gmail, drive]

    def test_session_is_fixed_tool_restricted_private_and_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            fake = FakeComposio()
            state = composio_session.ensure_session(
                profile, self.providers(), "secret-test-key", request=fake
            )
            create = fake.calls[0]
            self.assertEqual(create[:2], ("POST", composio_session.SESSION_API))
            payload = create[2]
            self.assertEqual(
                payload["toolkits"]["enable"], ["gmail", "googledrive"]
            )
            self.assertFalse(payload["workbench"]["enable"])
            self.assertEqual(
                set(payload["tools"]), {"gmail", "googledrive"}
            )
            self.assertNotIn("secret-test-key", str(state))
            state_path = profile / composio_session.STATE_PATH
            self.assertEqual(stat.S_IMODE(state_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(state_path.parent.stat().st_mode), 0o700)

            reused = composio_session.ensure_session(
                profile, self.providers(), "secret-test-key", request=fake
            )
            self.assertEqual(reused["session_id"], "trs_test")
            self.assertEqual(
                [call[0:2] for call in fake.calls].count(
                    ("POST", composio_session.SESSION_API)
                ),
                1,
            )

    def test_connection_status_and_link_use_the_existing_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            fake = FakeComposio()
            state = composio_session.ensure_session(
                profile, self.providers(), "secret-test-key", request=fake
            )
            connected = composio_session.connected_toolkits(
                state, "secret-test-key", request=fake
            )
            self.assertEqual(connected, {"gmail"})
            status_call = next(call for call in fake.calls if "/toolkits?" in call[1])
            self.assertIn("is_connected=true", status_call[1])
            url = composio_session.create_connect_link(
                state, "googledrive", "secret-test-key", request=fake
            )
            self.assertEqual(url, "https://app.composio.dev/link/test")

    def test_missing_api_key_fails_before_network(self) -> None:
        fake = FakeComposio()
        with self.assertRaisesRegex(
            composio_session.ComposioSessionError, "api_key_missing"
        ):
            composio_session.ensure_session(
                Path("/tmp/profile"), self.providers(), "", request=fake
            )
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
