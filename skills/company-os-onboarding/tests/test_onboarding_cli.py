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
                "Kamdar AI",
                "--company-description",
                "Twenty-person AI company.",
                "--output",
                str(output),
            )
            second = self.run_cli(
                "init",
                "--company-name",
                "Kamdar AI",
                "--company-description",
                "Twenty-person AI company.",
                "--output",
                str(output),
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 2)
            self.assertIn("Kamdar AI", output.read_text(encoding="utf-8"))

    def test_check_reports_unfinished_template_as_structured_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "company.hermes.md"
            self.run_cli(
                "init",
                "--company-name",
                "Kamdar AI",
                "--company-description",
                "Twenty-person AI company.",
                "--output",
                str(output),
            )
            result = self.run_cli("check", "--file", str(output))
            receipt = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(receipt["state"], "needs_review")
            self.assertIn("onboarding_comments_remain", receipt["issues"])


if __name__ == "__main__":
    unittest.main()
