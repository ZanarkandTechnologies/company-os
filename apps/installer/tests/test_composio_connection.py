from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import call, patch

from apps.installer import composio_session, runtime
from apps.installer.cli.flows import connections


PROFILE = Path("/tmp/company-os-profile")
PROVIDERS = [
    {
        "mcp": {"name": "composio-google"},
    }
]
STATE = {
    "mcp_url": "https://app.composio.dev/tool_router/v3/test/mcp",
    "toolkits": {"gmail": ["GMAIL_GET_PROFILE"]},
}


class ComposioConnectionTests(unittest.TestCase):
    def test_rejected_saved_key_is_replaced_only_after_validation(self) -> None:
        with patch.object(runtime, "read_profile_secret", return_value="old-key"):
            with patch.object(connections, "_prompt_secret", return_value="new-key"):
                with patch.object(
                    composio_session,
                    "ensure_session",
                    side_effect=[
                        composio_session.ComposioSessionError("composio_http_401"),
                        STATE,
                    ],
                ) as ensure_session:
                    with patch.object(runtime, "save_profile_secret") as save_secret:
                        with patch.object(runtime, "configure_remote_mcp") as configure:
                            with patch.object(
                                composio_session,
                                "connected_toolkits",
                                return_value={"gmail"},
                            ):
                                with patch.object(
                                    connections, "run_mcp_test_visible", return_value=0
                                ):
                                    connections._configure_composio_connection(
                                        PROFILE, PROVIDERS, non_interactive=False
                                    )

        self.assertEqual(
            ensure_session.call_args_list,
            [call(PROFILE, PROVIDERS, "old-key"), call(PROFILE, PROVIDERS, "new-key")],
        )
        save_secret.assert_called_once_with(PROFILE, "COMPOSIO_API_KEY", "new-key")
        configure.assert_called_once_with(
            PROFILE,
            "composio-google",
            STATE["mcp_url"],
            headers={"x-api-key": "${COMPOSIO_API_KEY}"},
        )

    def test_missing_toolkit_connection_fails_closed(self) -> None:
        with patch.object(runtime, "read_profile_secret", return_value="key"):
            with patch.object(composio_session, "ensure_session", return_value=STATE):
                with patch.object(runtime, "configure_remote_mcp"):
                    with patch.object(
                        composio_session, "connected_toolkits", return_value=set()
                    ):
                        with patch.object(connections, "pause"):
                            with patch.object(
                                composio_session,
                                "create_connect_link",
                                return_value="https://app.composio.dev/link/test",
                            ):
                                with self.assertRaisesRegex(
                                    runtime.RuntimeSetupError,
                                    "composio_connections_incomplete:gmail",
                                ):
                                    connections._configure_composio_connection(
                                        PROFILE, PROVIDERS, non_interactive=False
                                    )

    def test_mcp_transport_failure_fails_closed(self) -> None:
        with patch.object(runtime, "read_profile_secret", return_value="key"):
            with patch.object(composio_session, "ensure_session", return_value=STATE):
                with patch.object(runtime, "configure_remote_mcp"):
                    with patch.object(
                        composio_session,
                        "connected_toolkits",
                        return_value={"gmail"},
                    ):
                        with patch.object(
                            connections, "run_mcp_test_visible", return_value=1
                        ):
                            with self.assertRaisesRegex(
                                runtime.RuntimeSetupError,
                                "composio_mcp_connection_test_failed",
                            ):
                                connections._configure_composio_connection(
                                    PROFILE, PROVIDERS, non_interactive=False
                                )

    def test_failed_replacement_preserves_the_saved_key(self) -> None:
        with patch.object(runtime, "read_profile_secret", return_value="old-key"):
            with patch.object(connections, "_prompt_secret", return_value="bad-key"):
                with patch.object(
                    composio_session,
                    "ensure_session",
                    side_effect=[
                        composio_session.ComposioSessionError("composio_http_401"),
                        composio_session.ComposioSessionError("composio_http_403"),
                    ],
                ):
                    with patch.object(runtime, "save_profile_secret") as save_secret:
                        with patch.object(runtime, "configure_remote_mcp") as configure:
                            with self.assertRaisesRegex(
                                runtime.RuntimeSetupError, "composio_http_403"
                            ):
                                connections._configure_composio_connection(
                                    PROFILE, PROVIDERS, non_interactive=False
                                )

        save_secret.assert_not_called()
        configure.assert_not_called()

    def test_new_key_is_not_saved_when_validation_fails(self) -> None:
        with patch.object(runtime, "read_profile_secret", return_value=None):
            with patch.object(connections, "_prompt_secret", return_value="bad-key"):
                with patch.object(
                    composio_session,
                    "ensure_session",
                    side_effect=composio_session.ComposioSessionError(
                        "composio_http_401"
                    ),
                ):
                    with patch.object(runtime, "save_profile_secret") as save_secret:
                        with self.assertRaisesRegex(
                            runtime.RuntimeSetupError, "composio_http_401"
                        ):
                            connections._configure_composio_connection(
                                PROFILE, PROVIDERS, non_interactive=False
                            )

        save_secret.assert_not_called()

    def test_non_auth_errors_and_noninteractive_runs_do_not_prompt(self) -> None:
        for non_interactive, error_code in (
            (False, "composio_unavailable"),
            (True, "composio_http_401"),
        ):
            with self.subTest(non_interactive=non_interactive, error=error_code):
                with patch.object(runtime, "read_profile_secret", return_value="old-key"):
                    with patch.object(connections, "_prompt_secret") as prompt:
                        with patch.object(
                            composio_session,
                            "ensure_session",
                            side_effect=composio_session.ComposioSessionError(error_code),
                        ):
                            with patch.object(runtime, "save_profile_secret") as save_secret:
                                with self.assertRaisesRegex(
                                    runtime.RuntimeSetupError, error_code
                                ):
                                    connections._configure_composio_connection(
                                        PROFILE,
                                        PROVIDERS,
                                        non_interactive=non_interactive,
                                    )
                prompt.assert_not_called()
                save_secret.assert_not_called()


if __name__ == "__main__":
    unittest.main()
