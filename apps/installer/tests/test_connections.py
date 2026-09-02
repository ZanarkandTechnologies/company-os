from __future__ import annotations

import ast
import unittest
from pathlib import Path

from apps.installer import connection_evals as run_connection_evals


ROOT = Path(__file__).resolve().parents[3]


class SetupCertifyUXTests(unittest.TestCase):
    def test_real_retry_selector_cannot_shadow_the_ui_selector(self) -> None:
        source = (
            ROOT / "apps" / "installer" / "cli" / "flows" / "connections.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        recovery = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_certify_with_recovery"
        )
        nested_names = {
            node.name
            for node in recovery.body
            if isinstance(node, ast.FunctionDef)
        }
        called_names = {
            node.func.id
            for node in ast.walk(recovery)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("choose_action", nested_names)
        self.assertNotIn("choose_option", nested_names)
        self.assertIn("choose_option", called_names)

    def test_failed_certification_can_retry_in_place_until_passed(self) -> None:
        receipts = [{"status": "failed"}, {"status": "passed"}]
        rendered = []
        result = run_connection_evals.resolve_certification(
            lambda: receipts.pop(0),
            rendered.append,
            lambda: "retry",
            lambda receipt: {**receipt, "status": "deferred"},
            interactive=True,
        )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(len(rendered), 2)

    def test_failed_certification_can_defer_without_aborting_setup(self) -> None:
        failed = {"status": "failed", "run_id": "test-run"}
        deferred = []
        result = run_connection_evals.resolve_certification(
            lambda: failed,
            lambda receipt: None,
            lambda: "defer",
            lambda receipt: deferred.append(receipt)
            or {**receipt, "status": "deferred"},
            interactive=True,
        )
        self.assertEqual(result["status"], "deferred")
        self.assertEqual(deferred, [failed])


if __name__ == "__main__":
    unittest.main()
