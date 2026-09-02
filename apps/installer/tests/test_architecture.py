from __future__ import annotations

import ast
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "apps" / "installer" / "cli"


class SetupArchitectureTests(unittest.TestCase):
    def test_public_entry_point_is_only_a_dependency_bootstrap(self) -> None:
        source = (ROOT / "setup.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        self.assertLessEqual(len(source.splitlines()), 80)
        self.assertEqual(functions, {"_ensure_ui_runtime", "main"})
        self.assertIn("apps.installer.cli.app", source)

    def test_public_help_preserves_the_customer_command_surface(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "setup.py"), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("feature wizard saves resumable answers", result.stdout)
        for command in (
            "init",
            "configure",
            "features",
            "launch",
            "install",
            "update",
            "verify",
            "certify",
            "doctor",
            "webhook-enabled",
            "webhook-ingress-ready",
            "webhook-commit",
            "webhook-rollback",
        ):
            self.assertIn(command, result.stdout)

    def test_setup_responsibilities_have_named_owner_modules(self) -> None:
        required = {
            "app.py",
            "ui.py",
            "paths.py",
            "process.py",
            "flows/workspace.py",
            "flows/lifecycle.py",
            "flows/connections.py",
            "flows/verification.py",
            "flows/doctor.py",
        }
        self.assertTrue(required.issubset({
            path.relative_to(PACKAGE).as_posix()
            for path in PACKAGE.rglob("*.py")
        }))
        self.assertTrue((ROOT / "plugins/platforms/notion/onboarding.py").is_file())

    def test_only_ui_module_reads_interactive_input(self) -> None:
        forbidden = ("Prompt.ask", "Confirm.ask", "getpass.getpass")
        offenders = []
        for path in PACKAGE.rglob("*.py"):
            if path.name == "ui.py":
                continue
            source = path.read_text(encoding="utf-8")
            for marker in forbidden:
                if marker in source:
                    offenders.append(f"{path.relative_to(ROOT)}:{marker}")
        self.assertEqual(offenders, [])

    def test_deterministic_backends_do_not_import_interactive_flows(self) -> None:
        backends = (
            ROOT / "apps/installer/runtime.py",
            ROOT / "apps/installer/profile.py",
            ROOT / "apps/installer/workspace.py",
            ROOT / "apps/installer/provider_catalog.py",
            ROOT / "apps/installer/composio_session.py",
            ROOT / "apps/installer/connection_evals.py",
        )
        offenders = []
        for path in backends:
            if "apps.installer.cli" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
