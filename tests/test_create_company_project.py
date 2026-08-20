from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/create_company_project.py"


class CreateCompanyProjectTests(unittest.TestCase):
    def run_create(self, target: Path, timezone: str = "Asia/Kuala_Lumpur") -> tuple[int, dict[str, object]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(target),
             "--company-name", "Example Textiles", "--company-description",
             "A fictional textiles company.", "--company-timezone", timezone],
            text=True, capture_output=True, check=False,
        )
        self.assertTrue(result.stdout, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_scaffold_composes_canonical_assets_into_lean_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "example-textiles"
            code, receipt = self.run_create(target)
            self.assertEqual(code, 0)
            self.assertEqual(receipt["state"], "created")
            context = (target / "workspace.hermes.md").read_text(encoding="utf-8")
            self.assertIn('company_name: "Example Textiles"', context)
            self.assertIn('company_timezone: "Asia/Kuala_Lumpur"', context)
            self.assertIn("status: proposed-owner-review", context)
            for expected in (
                "automations/daily-operating-update.md",
                "automations/weekly-operating-review.md",
                "skills/setup-company-workspace/SKILL.md",
                "evals/filesystem/ui/index.html",
                "tests/test_company_project.py",
            ):
                self.assertTrue((target / expected).is_file(), expected)
            for excluded in ("configs", "plugins", "profile", "workspaces"):
                self.assertFalse((target / excluded).exists(), excluded)
            self.assertFalse(any("{{COMPANY_" in path.read_text(encoding="utf-8", errors="ignore")
                                 for path in target.rglob("*") if path.is_file()))

    def test_existing_target_and_invalid_timezone_are_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            existing = root / "existing"
            existing.mkdir()
            code, receipt = self.run_create(existing)
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "target_must_not_exist")
            invalid = root / "invalid"
            code, receipt = self.run_create(invalid, "Moon/Sea")
            self.assertEqual(code, 2)
            self.assertEqual(receipt["blocker"], "invalid_company_timezone")
            self.assertFalse(invalid.exists())


if __name__ == "__main__":
    unittest.main()
