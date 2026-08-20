from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CompanyProjectContractTests(unittest.TestCase):
    def test_lean_source_layout(self) -> None:
        self.assertTrue((ROOT / "workspace.hermes.md").is_file())
        for expected in ("automations", "skills", "evals", "scripts", "tests"):
            self.assertTrue((ROOT / expected).is_dir(), expected)
        for excluded in ("configs", "plugins", "profile", "workspaces"):
            self.assertFalse((ROOT / excluded).exists(), excluded)
        self.assertTrue((ROOT / "skills/setup-company-workspace/SKILL.md").is_file())
        self.assertTrue((ROOT / "scripts/validate_company_context.py").is_file())


if __name__ == "__main__":
    unittest.main()
