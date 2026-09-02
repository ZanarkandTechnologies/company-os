from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from apps.doctor import evaluation
from apps.installer import readiness_evals, runtime
from apps.installer.cli.flows import doctor


class DoctorActivationTests(unittest.TestCase):
    def _profile_with_proof(self, root: Path, readiness_status: str = "passed") -> Path:
        profile = root / "profile"
        (profile / runtime.RECEIPT_DIRECTORY).mkdir(parents=True)
        (profile / readiness_evals.STATE_DIRECTORY).mkdir(parents=True)
        (profile / runtime.RECEIPT_DIRECTORY / "setup-live.json").write_text(
            json.dumps({"live": True, "status": "ready"}), encoding="utf-8"
        )
        (profile / readiness_evals.STATE_DIRECTORY / "latest.json").write_text(
            json.dumps({"status": readiness_status, "run_id": "readiness-run"}),
            encoding="utf-8",
        )
        return profile

    def test_activate_resumes_only_after_all_proof_receipts_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self._profile_with_proof(Path(temporary))
            index = profile / evaluation.STATE_DIRECTORY / "eval-run" / "dossier" / "index.html"
            receipt = profile / "state" / "setup-proof.json"
            with (
                patch.object(doctor, "resolve_profile_home", return_value=profile),
                patch.object(
                    readiness_evals,
                    "latest_valid_passed_receipt",
                    return_value=(profile / "readiness.json", {"run_id": "readiness-run"}),
                ),
                patch.object(evaluation, "latest_valid_index", return_value=index),
                patch.object(doctor.profile_setup, "activate_managed_schedules", return_value=receipt) as activate,
            ):
                result = doctor.activate_command(argparse.Namespace(profile_home=profile))
            self.assertEqual(result, 0)
            proof = activate.call_args.args[1]
            self.assertEqual(proof["readiness_run_id"], "readiness-run")
            self.assertEqual(proof["eval_run_id"], "eval-run")

    def test_activate_leaves_schedules_paused_when_readiness_did_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self._profile_with_proof(Path(temporary), readiness_status="needs_setup")
            with (
                patch.object(doctor, "resolve_profile_home", return_value=profile),
                patch.object(
                    readiness_evals,
                    "latest_valid_passed_receipt",
                    side_effect=readiness_evals.ReadinessEvalError("readiness_receipt_not_passed"),
                ),
                patch.object(doctor.profile_setup, "activate_managed_schedules") as activate,
            ):
                result = doctor.activate_command(argparse.Namespace(profile_home=profile))
            self.assertEqual(result, 2)
            activate.assert_not_called()

    def test_activate_names_a_failed_live_health_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = self._profile_with_proof(Path(temporary))
            health = profile / runtime.RECEIPT_DIRECTORY / "setup-live.json"
            health.write_text(
                json.dumps({"live": True, "status": "blocked"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                doctor.profile_setup.ProfileSetupError,
                "live_health_receipt_not_ready:blocked",
            ):
                doctor._latest_live_health(profile)


if __name__ == "__main__":
    unittest.main()
