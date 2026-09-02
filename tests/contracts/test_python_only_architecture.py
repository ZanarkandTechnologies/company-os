from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PythonOnlyArchitectureTests(unittest.TestCase):
    def test_repository_has_no_javascript_runtime_or_package_metadata(self) -> None:
        forbidden = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in {".git", "__pycache__"} for part in path.parts):
                continue
            if path.suffix in {".js", ".mjs", ".cjs", ".cts", ".ts"} or path.name in {"package.json", "package-lock.json"}:
                forbidden.append(str(path.relative_to(ROOT)))
        self.assertEqual(forbidden, [])

    def test_active_sources_and_docs_do_not_reference_retired_toolchain(self) -> None:
        findings: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".md", ".yaml", ".yml"}:
                continue
            relative = path.relative_to(ROOT)
            if relative.parts[:2] == ("tickets", "archive") or "artifacts" in relative.parts:
                continue
            if relative in {
                Path("tests/contracts/test_distribution.py"),
                Path("tests/contracts/test_python_only_architecture.py"),
            }:
                continue
            source = path.read_text(encoding="utf-8", errors="replace").lower()
            for retired in (".mjs", "from \"zod\"", "from 'zod'", "npm run"):
                if retired in source:
                    findings.append(f"{relative}:{retired}")
        self.assertEqual(findings, [])

if __name__ == "__main__":
    unittest.main()
