from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(
    os.environ.get("COMPANY_OS_RUN_DOCKER_E2E") == "1",
    "set COMPANY_OS_RUN_DOCKER_E2E=1 to operate the real pinned-image lane",
)
class RealDockerSetupE2E(unittest.TestCase):
    def test_fresh_setup_dashboard_and_restart(self) -> None:
        with tempfile.TemporaryDirectory(prefix="company-os-real-docker-") as directory:
            receipt = Path(directory) / "docker-receipt.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "apps" / "installer" / "e2e.py"),
                    "safe-docker",
                    "--receipt",
                    str(receipt),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=1800,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["cleanup"], "complete_and_verified")
            guard = payload["detail"]["guard"]
            self.assertNotIn("company-os-hermes-data", guard["resolved_volumes"])
            self.assertNotIn(9119, guard["published_ports"])
            self.assertEqual(payload["detail"]["launch_state"], "interactive_answers_required")
            self.assertEqual(
                set(payload["detail"]["services_after_restart"]),
                {"gateway", "dashboard"},
            )


if __name__ == "__main__":
    unittest.main()
