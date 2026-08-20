from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "scripts" / "onboard_company.py"


class CompanyOnboardingCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_stages_template_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "company.hermes.md"
            first = self.run_cli(
                "init",
                "--company-name",
                "Example Co",
                "--company-description",
                "Twenty-person AI company.",
                "--company-timezone",
                "Asia/Kuala_Lumpur",
                "--output",
                str(output),
            )
            second = self.run_cli(
                "init",
                "--company-name",
                "Example Co",
                "--company-description",
                "Twenty-person AI company.",
                "--company-timezone",
                "Asia/Kuala_Lumpur",
                "--output",
                str(output),
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 2)
            self.assertIn("Example Co", output.read_text(encoding="utf-8"))

    def test_check_reports_unfinished_template_as_structured_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "company.hermes.md"
            self.run_cli(
                "init",
                "--company-name",
                "Example Co",
                "--company-description",
                "Twenty-person AI company.",
                "--company-timezone",
                "Asia/Kuala_Lumpur",
                "--output",
                str(output),
            )
            result = self.run_cli("check", "--file", str(output))
            receipt = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(receipt["state"], "needs_review")
            self.assertIn("onboarding_comments_remain", receipt["issues"])

    def test_init_rejects_non_iana_timezone_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "company.hermes.md"
            result = self.run_cli(
                "init", "--company-name", "Example Co", "--company-description", "Example.",
                "--company-timezone", "Kuala Lumpur", "--output", str(output),
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())
            self.assertEqual(json.loads(result.stdout)["blocker"], "invalid_company_timezone")

    def test_check_rejects_hand_edited_invalid_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "company.hermes.md"
            self.run_cli(
                "init", "--company-name", "Example Co", "--company-description", "Example.",
                "--company-timezone", "Asia/Kuala_Lumpur", "--output", str(output),
            )
            content = output.read_text(encoding="utf-8").replace("Asia/Kuala_Lumpur", "Kuala Lumpur")
            output.write_text(content, encoding="utf-8")
            result = self.run_cli("check", "--file", str(output))
            self.assertIn("invalid_company_timezone", json.loads(result.stdout)["issues"])


if __name__ == "__main__":
    unittest.main()
