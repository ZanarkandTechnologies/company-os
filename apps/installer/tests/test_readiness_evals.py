from __future__ import annotations

import json
import stat
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from apps.installer import provider_catalog
from apps.installer import readiness_evals


class FakeHermes:
    def __init__(
        self,
        verdicts: dict[str, dict[str, object]],
        *,
        write_tool: bool = False,
        orphan_tool_result: bool = False,
    ) -> None:
        self.verdicts = verdicts
        self.write_tool = write_tool
        self.orphan_tool_result = orphan_tool_result
        self.judge_calls = 0
        self.judge_arguments: list[list[str]] = []
        self.executor_calls = 0
        self.config_calls: list[list[str]] = []
        self.lock = threading.Lock()

    def __call__(self, arguments, profile_home, **kwargs):
        del profile_home
        prompt = kwargs.get("input_text", "") or ""
        if arguments[1:3] == ["config", "get"]:
            self.config_calls.append(arguments)
            return subprocess.CompletedProcess(arguments, 1, "", "missing")
        if arguments[1] == "config":
            self.config_calls.append(arguments)
            return subprocess.CompletedProcess(arguments, 0, "", "")
        if arguments[1:3] == ["mcp", "test"]:
            return subprocess.CompletedProcess(arguments, 0, "✓ Connected", "")
        if arguments[1:3] == ["sessions", "export"]:
            tool = (
                "mcp__notion__notion_create_pages"
                if self.write_tool
                else "mcp__notion__notion_fetch"
            )
            payload = {
                "messages": [
                    *([] if self.orphan_tool_result else [
                        {"role": "assistant", "tool_calls": [{"function": {"name": tool}}]}
                    ]),
                    {"role": "tool", "tool_name": tool, "content": "redacted provider result"},
                ]
            }
            return subprocess.CompletedProcess(arguments, 0, json.dumps(payload) + "\n", "")
        if "Judge this batch" in prompt:
            self.judge_calls += 1
            self.judge_arguments.append(arguments)
            source = json.loads(prompt.split("INPUT:\n", 1)[1])
            rows = []
            for case in source["cases"]:
                verdict = self.verdicts[case["case_id"]]
                rows.append({"case_id": case["case_id"], "status": "passed", **verdict})
            return subprocess.CompletedProcess(arguments, 0, json.dumps({"cases": rows}), "")
        with self.lock:
            self.executor_calls += 1
        return subprocess.CompletedProcess(
            arguments,
            0,
            '{"source_state":"populated"}',
            "\nsession_id: readiness-session\n",
        )


class ReadinessEvalTests(unittest.TestCase):
    def _catalog_and_workspace(self, temporary: Path, roles: list[str]) -> tuple[Path, Path]:
        catalog = temporary / "catalog"
        catalog.mkdir()
        for role in roles:
            source = provider_catalog.DEFAULT_CATALOG / f"{role}.json"
            (catalog / source.name).write_bytes(source.read_bytes())
        workspace = temporary / "workspace.md"
        rows = {
            "projects": "| `projects` | notion | project-source | read | test |",
            "tasks": "| `tasks` | notion | task-source | read | test |",
            "meetings": "| `meetings` | notion | tasks embedded page content | read | test |",
            "people": "| `people` | notion | people-source | read | test |",
            "operator_email": "| `operator_email` | gmail | operator@example.test | read | test |",
        }
        workspace.write_text(
            "<!-- hermes:managed data-sources -->\n"
            "| Role | Provider | Source | Access | Scope |\n"
            "| --- | --- | --- | --- | --- |\n"
            + "\n".join(rows[role] for role in roles)
            + "\n<!-- /hermes:managed data-sources -->\n",
            encoding="utf-8",
        )
        return catalog, workspace

    def test_core_empty_optional_empty_and_meetings_alias_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog, workspace = self._catalog_and_workspace(
                root, ["projects", "tasks", "meetings", "people"]
            )
            fake = FakeHermes(
                {
                    "projects:notion": {
                        "source_state": "populated", "record_count": 2,
                        "available_fields": ["id", "name", "status"],
                        "relations_with_values": [], "meeting_evidence": "not_applicable",
                        "warnings": [],
                    },
                    "tasks:notion": {
                        "source_state": "empty", "record_count": 0,
                        "available_fields": ["id", "name", "status", "project", "owner"],
                        "relations_with_values": ["project", "owner"],
                        "meeting_evidence": "absent", "warnings": [],
                    },
                    "people:notion": {
                        "source_state": "empty", "record_count": 0,
                        "available_fields": ["id", "name"],
                        "relations_with_values": [], "meeting_evidence": "not_applicable",
                        "warnings": [],
                    },
                }
            )
            receipt = readiness_evals.run_readiness_evals(
                root, workspace, catalog_directory=catalog, command_runner=fake
            )
            cases = {case["data_source"]: case for case in receipt["cases"]}
            self.assertEqual(receipt["status"], "needs_setup")
            self.assertEqual(cases["tasks"]["issues"], ["core_source_empty"])
            self.assertEqual(cases["people"]["status"], "needs_setup")
            self.assertEqual(cases["people"]["issues"], ["selected_source_empty"])
            self.assertEqual(cases["meetings"]["evidence"]["separate_fetch"], False)
            self.assertEqual(cases["meetings"]["warnings"], ["meetings_not_observed"])
            self.assertEqual(fake.executor_calls, 3)
            self.assertEqual(fake.judge_calls, 1)
            self.assertEqual(
                fake.judge_arguments[0][fake.judge_arguments[0].index("--toolsets") + 1],
                "context_engine",
            )

    def test_missing_core_relation_needs_setup_with_exact_issue(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog, workspace = self._catalog_and_workspace(root, ["tasks"])
            fake = FakeHermes(
                {
                    "tasks:notion": {
                        "source_state": "populated", "record_count": 3,
                        "available_fields": ["id", "name", "status"],
                        "relations_with_values": ["project"],
                        "meeting_evidence": "absent", "warnings": [],
                    }
                }
            )
            receipt = readiness_evals.run_readiness_evals(
                root, workspace, catalog_directory=catalog, command_runner=fake
            )
            case = next(
                item for item in receipt["cases"] if item["data_source"] == "tasks"
            )
            self.assertEqual(case["status"], "needs_setup")
            self.assertEqual(case["missing_required_relations"], ["owner"])
            self.assertEqual(case["issues"], ["required_relation_missing:owner"])

    def test_capability_uses_current_connection_receipt_without_scanning_email(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog_dir, workspace = self._catalog_and_workspace(root, ["operator_email"])
            bindings = provider_catalog.selected_bindings(
                workspace, provider_catalog.load_catalog(catalog_dir)
            )
            proof = {
                "status": "passed",
                "configuration_sha256": provider_catalog.configuration_hash(bindings),
                "judgment": {
                    "cases": [{"case_id": "operator_email:gmail", "status": "passed"}]
                },
            }
            fake = FakeHermes({})
            receipt = readiness_evals.run_readiness_evals(
                root,
                workspace,
                catalog_directory=catalog_dir,
                command_runner=fake,
                connection_receipt=proof,
            )
            self.assertEqual(receipt["status"], "needs_setup")
            cases = {case["data_source"]: case for case in receipt["cases"]}
            self.assertEqual(cases["operator_email"]["source_state"], "capability_confirmed")
            self.assertEqual(cases["projects"]["issues"], ["core_source_not_configured"])
            self.assertEqual(cases["tasks"]["issues"], ["core_source_not_configured"])
            self.assertEqual(fake.executor_calls, 0)
            self.assertEqual(fake.judge_calls, 0)

    def test_write_tool_fails_and_receipt_is_private_redacted_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog, workspace = self._catalog_and_workspace(root, ["projects"])
            fake = FakeHermes(
                {
                    "projects:notion": {
                        "source_state": "populated", "record_count": 1,
                        "available_fields": ["id", "name", "status"],
                        "relations_with_values": [], "meeting_evidence": "not_applicable",
                        "warnings": [],
                    }
                },
                write_tool=True,
            )
            receipt = readiness_evals.run_readiness_evals(
                root,
                workspace,
                catalog_directory=catalog,
                command_runner=fake,
                run_id="fixed-run",
            )
            self.assertEqual(receipt["status"], "failed")
            project = next(
                item for item in receipt["cases"] if item["data_source"] == "projects"
            )
            self.assertEqual(project["issues"], ["non_read_tool_observed"])
            self.assertIn(
                ["hermes", "config", "set", "mcp_servers.notion.trust", "untrusted"],
                fake.config_calls,
            )
            self.assertIn(
                ["hermes", "config", "unset", "mcp_servers.notion.trust"],
                fake.config_calls,
            )
            destination = readiness_evals.write_receipt(root, receipt)
            latest = root / readiness_evals.STATE_DIRECTORY / "latest.json"
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(latest.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(destination.parent.stat().st_mode), 0o700)
            stored = latest.read_text(encoding="utf-8")
            self.assertIn('"configuration_sha256"', stored)
            self.assertIn('"readiness_sha256"', stored)
            self.assertNotIn("redacted provider result", stored)
            self.assertNotIn("project-source", stored)
            self.assertNotIn('"response"', stored)
            self.assertNotIn('"trace"', stored)

    def test_orphan_tool_result_fails_strict_trace_precheck(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog, workspace = self._catalog_and_workspace(root, ["projects"])
            fake = FakeHermes(
                {
                    "projects:notion": {
                        "source_state": "populated", "record_count": 1,
                        "available_fields": ["id", "name", "status"],
                        "relations_with_values": [], "meeting_evidence": "not_applicable",
                        "warnings": [],
                    }
                },
                orphan_tool_result=True,
            )
            receipt = readiness_evals.run_readiness_evals(
                root, workspace, catalog_directory=catalog, command_runner=fake
            )
            project = next(
                item for item in receipt["cases"] if item["data_source"] == "projects"
            )
            self.assertEqual(project["status"], "failed")
            self.assertEqual(project["issues"], ["tool_result_without_call"])

    def test_activation_validator_rejects_stale_or_tampered_readiness_proof(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, workspace = self._catalog_and_workspace(root, ["projects"])
            bindings = provider_catalog.selected_bindings(
                workspace, provider_catalog.load_catalog()
            )
            receipt = {
                "schema_version": 1,
                "run_id": "passed-run",
                "status": "passed",
                "configuration_sha256": provider_catalog.configuration_hash(bindings),
                "readiness_sha256": provider_catalog.readiness_hash(bindings),
                "cases": [],
            }
            immutable = readiness_evals.write_receipt(root, receipt)
            validated, _ = readiness_evals.latest_valid_passed_receipt(root, workspace)
            self.assertEqual(validated, immutable)

            workspace.write_text(
                workspace.read_text(encoding="utf-8").replace(
                    "project-source", "changed-project-source"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                readiness_evals.ReadinessEvalError, "readiness_configuration_stale"
            ):
                readiness_evals.latest_valid_passed_receipt(root, workspace)

            workspace.write_text(
                workspace.read_text(encoding="utf-8").replace(
                    "changed-project-source", "project-source"
                ),
                encoding="utf-8",
            )
            latest = root / readiness_evals.STATE_DIRECTORY / "latest.json"
            altered = json.loads(latest.read_text(encoding="utf-8"))
            altered["cases"] = [{"tampered": True}]
            latest.write_text(json.dumps(altered), encoding="utf-8")
            with self.assertRaisesRegex(
                readiness_evals.ReadinessEvalError, "readiness_latest_stale"
            ):
                readiness_evals.latest_valid_passed_receipt(root, workspace)


if __name__ == "__main__":
    unittest.main()
