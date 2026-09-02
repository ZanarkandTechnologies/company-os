from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from apps.eval_viewer.build import build_static_evidence_viewer, render_evidence_html, render_markdown
from apps.eval_viewer.model import ViewerError, build_evidence_model


ROOT = Path(__file__).resolve().parents[3]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def catalog() -> list[tuple[str, dict]]:
    rows = []
    for cadence in ("daily", "weekly"):
        suite = json.loads((ROOT / f"skills/pm-{cadence}/evals/evals.json").read_text(encoding="utf-8"))
        rows.extend((cadence, row) for row in suite["evals"])
    return rows


def fixture(root: Path) -> None:
    (root / "outputs").mkdir(parents=True, exist_ok=True)
    (root / "outputs/daily.md").write_text("# Daily output\n\nGrounded daily artifact.\n", encoding="utf-8")
    (root / "outputs/weekly.md").write_text("# Weekly output\n\nGrounded weekly artifact.\n", encoding="utf-8")
    results = []
    for cadence, case in catalog():
        results.append({
            "eval_id": case["id"],
            "outputs": [f"outputs/{cadence}.md"] if case["metadata"]["tags"][-1] == "showcase" else [],
            "assertions": [
                {"index": index, "met": True, "evidence": [f"{cadence} shared run"]}
                for index, _ in enumerate(case["assertions"])
            ],
        })
    write_json(root / "eval-receipt.json", {
        "status": "passed",
        "run_mode": "analysis_only",
        "provider_mutations": 0,
        "automation_runs": {"daily": {"status": "passed"}, "weekly": {"status": "passed"}},
        "eval_results": results,
    })


class EvidenceViewerTests(unittest.TestCase):
    def test_failed_shared_run_renders_every_owned_eval_without_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / "eval-receipt.json", {
                "run_mode": "analysis_only",
                "provider_mutations": 0,
                "automation_runs": {"daily": {"status": "failed"}, "weekly": {"status": "not_run"}},
            })
            model = build_static_evidence_viewer(out_dir=root, eval_run_root=root)
            self.assertEqual(len(model["evaluations"]), 8)
            self.assertEqual([row["status"] for row in model["evaluations"]].count("fail"), 4)
            self.assertEqual([row["status"] for row in model["evaluations"]].count("not_run"), 4)

    def test_setup_block_renders_without_loading_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / "eval-receipt.json", {
                "status": "needs_information",
                "run_mode": "analysis_only",
                "provider_mutations": 0,
                "automation_runs": {"daily": {"status": "blocked_by_setup"}, "weekly": {"status": "blocked_by_setup"}},
            })
            model = build_evidence_model(project_root=ROOT, eval_run_root=root)
            self.assertTrue(all(row["status"] == "not_run" for row in model["evaluations"]))
            self.assertTrue(all(not row["outputs"] for row in model["evaluations"]))

    def test_shared_summary_joins_eval_ids_and_showcases_first(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root)
            model = build_evidence_model(project_root=ROOT, eval_run_root=root)
            self.assertEqual(model["runKind"], "shared-automation-eval")
            self.assertEqual(model["metrics"]["evaluations"], {"total": 8, "passed": 8})
            self.assertTrue(all(row["showcase"] for row in model["evaluations"][:6]))
            self.assertTrue(all(not row["showcase"] for row in model["evaluations"][6:]))
            self.assertEqual(model["evaluations"][0]["name"], "Documentation-quality follow-up")
            self.assertIn("right owner", model["evaluations"][0]["description"])
            self.assertFalse(any(row["id"].startswith("FEAT-") for row in model["evaluations"]))

    def test_html_renders_eval_descriptions_and_resultant_artifacts_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root)
            model = build_evidence_model(project_root=ROOT, eval_run_root=root)
            rendered = render_markdown("# Preview\n\n<script>alert(1)</script>")
            self.assertIn("<h1>Preview</h1>", rendered)
            self.assertIn("&lt;script&gt;", rendered)
            html = render_evidence_html(model)
            self.assertIn("evals · grouped by automation", html)
            self.assertIn("PM Daily", html)
            self.assertIn("PM Weekly", html)
            self.assertIn("Documentation-quality follow-up", html)
            self.assertIn("Shows that PM Daily asks the right owner", html)
            self.assertIn("Resultant artifacts", html)
            self.assertNotIn("Meeting Intake", html)
            self.assertNotIn("FEAT-0001", html)
            self.assertIn('href="eval-receipt.json"', html)
            build_static_evidence_viewer(out_dir=root, eval_run_root=root)
            self.assertEqual(os.stat(root / "index.html").st_mode & 0o777, 0o600)

    def test_unknown_eval_result_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / "eval-receipt.json", {
                "run_mode": "analysis_only",
                "provider_mutations": 0,
                "automation_runs": {"daily": {"status": "passed"}, "weekly": {"status": "passed"}},
                "eval_results": [{"eval_id": "unknown", "assertions": []}],
            })
            with self.assertRaisesRegex(ViewerError, "unknown eval"):
                build_evidence_model(project_root=ROOT, eval_run_root=root)

    def test_mutations_require_verified_isolated_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root)
            receipt = json.loads((root / "eval-receipt.json").read_text(encoding="utf-8"))
            receipt.update({"run_mode": "analysis_only", "provider_mutations": 1})
            write_json(root / "eval-receipt.json", receipt)
            with self.assertRaisesRegex(ViewerError, "isolated eval scope"):
                build_evidence_model(project_root=ROOT, eval_run_root=root)
            receipt.update({
                "run_mode": "isolated_eval",
                "isolation_scope": "notion-eval-2026-09-01",
                "read_back_verified": True,
            })
            write_json(root / "eval-receipt.json", receipt)
            self.assertEqual(build_evidence_model(project_root=ROOT, eval_run_root=root)["deliveryStatus"], "isolated_eval")

    def test_viewer_copies_linked_run_artifacts_when_output_directory_differs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            out = root / "viewer"
            run.mkdir()
            fixture(run)
            (run / "activity.jsonl").write_text('{"event":"complete"}\n', encoding="utf-8")
            build_static_evidence_viewer(out_dir=out, eval_run_root=run)
            self.assertTrue((out / "eval-receipt.json").is_file())
            self.assertTrue((out / "activity.jsonl").is_file())
            self.assertTrue((out / "outputs/daily.md").is_file())
            self.assertTrue((out / "outputs/weekly.md").is_file())

    def test_passing_assertion_requires_evidence_and_both_automation_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root)
            receipt = json.loads((root / "eval-receipt.json").read_text(encoding="utf-8"))
            receipt["eval_results"][0]["assertions"][0]["evidence"] = []
            write_json(root / "eval-receipt.json", receipt)
            with self.assertRaisesRegex(ViewerError, "without evidence"):
                build_evidence_model(project_root=ROOT, eval_run_root=root)
            receipt["eval_results"] = []
            receipt.pop("automation_runs")
            write_json(root / "eval-receipt.json", receipt)
            with self.assertRaisesRegex(ViewerError, "exactly one Daily and one Weekly"):
                build_evidence_model(project_root=ROOT, eval_run_root=root)


if __name__ == "__main__":
    unittest.main()
