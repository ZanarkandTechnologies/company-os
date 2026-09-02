from __future__ import annotations

import argparse
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.doctor import run as doctor


class CompanyDoctorTests(unittest.TestCase):
    def test_prompt_delegates_analysis_to_native_tools_without_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / "automations").mkdir()
            (workspace / ".hermes.md").write_text("company context\n", encoding="utf-8")
            (workspace / "automations/daily-operating-update.md").write_text(
                "# Daily\n\n- [ ] **1 — Fetch.**\n\n- [ ] **4 — Apply authorized effects.**\n"
                "sync provider\n\n## Output\nlocal files\n",
                encoding="utf-8",
            )
            prompt = doctor.analysis_prompt(workspace, "daily")
        self.assertIn("company context", prompt)
        self.assertIn("**1 — Fetch.**", prompt)
        self.assertIn("local files", prompt)
        self.assertNotIn("Apply authorized effects", prompt)
        self.assertNotIn("sync provider", prompt)
        self.assertIn("every changed local file path", prompt)
        self.assertNotIn("Read /", prompt)

    def test_parser_exposes_only_profile_and_cadence(self) -> None:
        args = doctor.parser().parse_args(["--cadence", "weekly"])
        self.assertEqual(args.cadences, ["weekly"])
        self.assertFalse(hasattr(args, "sync_to_provider"))
        self.assertFalse(hasattr(args, "bindings"))

    def test_operate_calls_native_hermes_once_per_requested_cadence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            workspace = profile / "workspace"
            (workspace / "automations").mkdir(parents=True)
            (workspace / ".hermes.md").write_text("company\n", encoding="utf-8")
            (workspace / "automations/daily-operating-update.md").write_text(
                "# Daily\n\n- [ ] **1 — Fetch.**\n\n"
                "- [ ] **4 — Apply authorized effects.**\n\nsync\n\n"
                "## Output\nlocal files\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(profile_home=profile, cadences=["daily"])
            completed = subprocess.CompletedProcess([], 0, "analysis\n", "")
            with patch.object(doctor.runtime, "run_command", return_value=completed) as invoked:
                self.assertEqual(doctor.operate(args), 0)
            self.assertEqual(invoked.call_count, 1)
            self.assertEqual(invoked.call_args.args[0][:2], ["hermes", "chat"])
            self.assertEqual(invoked.call_args.kwargs["timeout"], 900)
