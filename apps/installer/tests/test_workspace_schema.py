from __future__ import annotations

import unittest
from pathlib import Path

from pydantic import ValidationError

from apps.installer.schemas.workspace import (
    ArtifactSyncBinding,
    ArtifactSyncProvider,
    ArtifactType,
    CommunicationBinding,
    DeliveryBehavior,
    MessageType,
    MessagingApp,
    RecipientRule,
    configuration_hash,
    parse_workspace_artifact_sync,
    parse_workspace_communications,
    render_workspace_artifact_sync,
)


class WorkspaceSchemaTests(unittest.TestCase):
    def binding(self, **overrides: object) -> CommunicationBinding:
        values: dict[str, object] = {
            "message": MessageType.OWNER_REPORT,
            "app": MessagingApp.TELEGRAM,
            "send_to": "company owner",
            "behavior": DeliveryBehavior.PREPARE_DRAFTS,
        }
        values.update(overrides)
        return CommunicationBinding.model_validate(values)

    def test_owner_policy_is_derived_instead_of_customer_input(self) -> None:
        binding = self.binding()
        self.assertEqual(binding.recipient_rule, RecipientRule.NAMED_OWNER)
        self.assertNotIn("recipient_rule", binding.model_dump())

    def test_employee_automatic_send_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "People-directory"):
            self.binding(
                message=MessageType.EMPLOYEE_FOLLOW_UP,
                behavior=DeliveryBehavior.SEND_AUTOMATICALLY,
            )

    def test_connection_test_is_not_a_durable_message_type(self) -> None:
        with self.assertRaises(ValueError):
            MessageType("connection test")

    def test_managed_table_parses_customer_fields_only(self) -> None:
        content = """
<!-- hermes:managed communications -->
| Message | App | Send to | Behavior |
| --- | --- | --- | --- |
| `owner report` | telegram | company owner | prepare drafts for approval |
<!-- /hermes:managed communications -->
"""
        config = parse_workspace_communications(content)
        self.assertEqual(len(config.communications), 1)
        self.assertNotIn("mode", config.communications[0].model_dump())

    def test_empty_messaging_selection_is_valid(self) -> None:
        content = """
<!-- hermes:managed communications -->
| Message | App | Send to | Behavior |
| --- | --- | --- | --- |
<!-- /hermes:managed communications -->
"""
        self.assertEqual(parse_workspace_communications(content).communications, [])

    def test_distributed_workspace_template_is_private_by_default(self) -> None:
        root = Path(__file__).resolve().parents[3]
        for filename in ("workspace.hermes.template.md", "workspace.hermes.md"):
            with self.subTest(filename=filename):
                content = root.joinpath(filename).read_text(encoding="utf-8")
                self.assertEqual(
                    parse_workspace_communications(content).communications, []
                )
                self.assertEqual(
                    parse_workspace_artifact_sync(content).artifact_sync, []
                )
        template = root.joinpath("workspace.hermes.template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("| `projects` | REPLACE_ME | REPLACE_ME | read-write |", template)
        self.assertIn("| `tasks` | REPLACE_ME | REPLACE_ME | read-write |", template)
        self.assertIn("| `people` | REPLACE_ME | REPLACE_ME | read |", template)

    def test_configuration_hash_changes_with_behavior(self) -> None:
        draft = [self.binding()]
        automatic = [self.binding(behavior=DeliveryBehavior.SEND_AUTOMATICALLY)]
        self.assertNotEqual(configuration_hash(draft), configuration_hash(automatic))

    def test_missing_artifact_sync_block_means_local_only(self) -> None:
        self.assertEqual(parse_workspace_artifact_sync("# Workspace").artifact_sync, [])

    def test_artifact_sync_parses_complete_provider_destination_pairs(self) -> None:
        content = """
<!-- hermes:managed artifact-sync -->
| Artifact | Provider | Destination |
| --- | --- | --- |
| `long-term memory` | notion | https://notion.example.test/private-memory |
| `reports` | google-drive | https://drive.example.test/management-reports |
<!-- /hermes:managed artifact-sync -->
"""
        config = parse_workspace_artifact_sync(content)
        self.assertEqual(
            [binding.artifact for binding in config.artifact_sync],
            [ArtifactType.LONG_TERM_MEMORY, ArtifactType.REPORTS],
        )
        self.assertNotIn("default", config.model_dump(mode="json"))

    def test_partial_duplicate_and_non_https_artifact_sync_are_rejected(self) -> None:
        partial = """
<!-- hermes:managed artifact-sync -->
| Artifact | Provider | Destination |
| --- | --- | --- |
| `short-term memory` | notion | — |
<!-- /hermes:managed artifact-sync -->
"""
        with self.assertRaisesRegex(ValueError, "incomplete"):
            parse_workspace_artifact_sync(partial)
        with self.assertRaisesRegex(ValidationError, "exact HTTPS"):
            ArtifactSyncBinding(
                artifact=ArtifactType.REPORTS,
                provider=ArtifactSyncProvider.NOTION,
                destination="notion://reports",
            )
        duplicate = partial.replace(
            "| `short-term memory` | notion | — |",
            "| `reports` | notion | https://notion.example.test/a |\n"
            "| `reports` | notion | https://notion.example.test/b |",
        )
        with self.assertRaisesRegex(ValidationError, "only one sync destination"):
            parse_workspace_artifact_sync(duplicate)
        malformed = partial.replace(
            "| `short-term memory` | notion | — |",
            "| `short-term memory` | notion |",
        )
        with self.assertRaisesRegex(ValueError, "exactly Artifact, Provider, and Destination"):
            parse_workspace_artifact_sync(malformed)

    def test_artifact_sync_renderer_has_no_enabled_or_default_column(self) -> None:
        rendered = render_workspace_artifact_sync([
            ArtifactSyncBinding(
                artifact=ArtifactType.SHORT_TERM_MEMORY,
                provider=ArtifactSyncProvider.NOTION,
                destination="https://notion.example.test/private-weekly",
            )
        ])
        self.assertEqual(
            rendered.splitlines()[0], "| Artifact | Provider | Destination |"
        )


if __name__ == "__main__":
    unittest.main()
