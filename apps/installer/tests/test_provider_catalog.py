from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from apps.installer import provider_catalog


ROOT = Path(__file__).resolve().parents[3]


class ProviderCatalogTests(unittest.TestCase):
    def test_catalog_defines_setup_choices_and_eval_contracts(self) -> None:
        catalog = provider_catalog.load_catalog()
        self.assertEqual(
            set(catalog),
            {
                "decisions",
                "projects",
                "tasks",
                "people",
                "reports",
                "meetings",
                "operator_email",
                "sops",
                "storage",
            },
        )
        self.assertEqual(
            [provider["id"] for provider in catalog["projects"]["providers"]],
            ["notion", "linear"],
        )
        mcp_sources = set()
        for source in catalog.values():
            for provider in source["providers"]:
                mcp_sources.add(provider["mcp"]["source"])
                self.assertTrue(provider["test"]["prompt"])
                self.assertTrue(provider["test"]["expected_output"])
                self.assertTrue(provider["test"]["assertions"])
                self.assertIn(
                    provider["readiness"]["importance"],
                    {"core", "optional", "destination", "capability", "alias"},
                )
        self.assertEqual(mcp_sources, {"hermes_catalog", "composio_session"})
        gmail = catalog["operator_email"]["providers"][0]
        self.assertEqual(gmail["id"], "gmail")
        self.assertEqual(gmail["mcp"]["toolkit"], "gmail")
        self.assertEqual(
            [provider["id"] for provider in catalog["reports"]["providers"]],
            ["notion"],
        )
        self.assertEqual(catalog["storage"]["providers"][0]["id"], "google_drive")

    def test_workspace_bindings_resolve_provider_and_deduplicate_connection_key(self) -> None:
        catalog = provider_catalog.load_catalog()
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace.md"
            workspace.write_text(
                "<!-- hermes:managed data-sources -->\n"
                "| Role | Provider | Source | Access | Scope |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| `projects` | notion | https://notion.example.test/projects | read | test |\n"
                "| `tasks` | notion | https://notion.example.test/tasks | read | test |\n"
                "<!-- /hermes:managed data-sources -->\n",
                encoding="utf-8",
            )
            bindings = provider_catalog.selected_bindings(workspace, catalog)
            self.assertTrue(bindings)
            self.assertTrue(all(binding["provider"]["id"] == "notion" for binding in bindings))
            self.assertEqual(
                {provider_catalog.connection_key(binding["provider"]) for binding in bindings},
                {"hermes_catalog:notion"},
            )

    def test_generic_workspace_starts_without_provider_bindings(self) -> None:
        bindings = provider_catalog.selected_bindings(
            ROOT / "workspace.hermes.md", provider_catalog.load_catalog()
        )
        self.assertEqual(bindings, [])

    def test_unknown_provider_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace.md"
            workspace.write_text(
                "<!-- hermes:managed data-sources -->\n"
                "| Role | Provider | Source | Access | Scope |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| `projects` | unknown | https://example.invalid | read | test |\n"
                "<!-- /hermes:managed data-sources -->\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(provider_catalog.CatalogError, "unsupported_provider"):
                provider_catalog.selected_bindings(workspace, provider_catalog.load_catalog())

    def test_configuration_hash_includes_the_eval_contract(self) -> None:
        catalog = provider_catalog.load_catalog()
        binding = {
            "case_id": "projects:notion",
            "data_source": "projects",
            "source": "https://notion.example.test/projects",
            "provider": catalog["projects"]["providers"][0],
        }
        before = provider_catalog.configuration_hash([binding])
        changed = json.loads(json.dumps(binding))
        changed["provider"]["test"]["assertions"].append("A new required assertion.")
        self.assertNotEqual(before, provider_catalog.configuration_hash([changed]))

    def test_readiness_hash_is_separate_and_includes_role_contract(self) -> None:
        catalog = provider_catalog.load_catalog()
        binding = {
            "case_id": "tasks:notion",
            "data_source": "tasks",
            "source": "https://notion.example.test/tasks",
            "provider": catalog["tasks"]["providers"][0],
        }
        connection_before = provider_catalog.configuration_hash([binding])
        readiness_before = provider_catalog.readiness_hash([binding])
        changed = json.loads(json.dumps(binding))
        changed["provider"]["readiness"]["required_relations"].append("department")
        self.assertEqual(
            connection_before, provider_catalog.configuration_hash([changed])
        )
        self.assertNotEqual(
            readiness_before, provider_catalog.readiness_hash([changed])
        )

    def test_manifest_filename_and_id_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            payload = json.loads(
                (provider_catalog.DEFAULT_CATALOG / "people.json").read_text(encoding="utf-8")
            )
            payload["id"] = "other"
            (directory / "people.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(provider_catalog.CatalogError, "catalog_invalid"):
                provider_catalog.load_catalog(directory)

    def test_side_effecting_provider_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            payload = json.loads(
                (provider_catalog.DEFAULT_CATALOG / "projects.json").read_text(
                    encoding="utf-8"
                )
            )
            payload["providers"][0]["test"]["requires_confirmation"] = False
            (directory / "projects.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                provider_catalog.CatalogError, "side_effect_confirmation"
            ):
                provider_catalog.load_catalog(directory)

    def test_readiness_allowlist_rejects_lexical_wildcards(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            payload = json.loads(
                (provider_catalog.DEFAULT_CATALOG / "projects.json").read_text(
                    encoding="utf-8"
                )
            )
            payload["providers"][0]["readiness"]["allowed_read_tools"] = ["*fetch*"]
            (directory / "projects.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(
                provider_catalog.CatalogError, "allowed_read_tools"
            ):
                provider_catalog.load_catalog(directory)


if __name__ == "__main__":
    unittest.main()
