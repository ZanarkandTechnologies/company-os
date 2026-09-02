from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from apps.doctor import evaluation


ROOT = Path(__file__).resolve().parents[3]


class FakeHermes:
    def __init__(
        self, *, omit_eval: str | None = None, omit_judgment: str | None = None,
        narrative_first_judge: bool = False,
    ) -> None:
        self.omit_eval = omit_eval
        self.omit_judgment = omit_judgment
        self.generation_calls: list[list[str]] = []
        self.judge_calls: list[list[str]] = []
        self.exports = 0
        self.narrative_first_judge = narrative_first_judge

    def __call__(self, arguments, profile_home, **kwargs):
        del profile_home
        prompt = kwargs.get("input_text", "") or ""
        if arguments[:4] == ["hermes", "config", "get", "terminal.backend"]:
            return subprocess.CompletedProcess(arguments, 0, "docker\n", "")
        if arguments[:4] == [
            "hermes", "config", "get", "terminal.docker_mount_cwd_to_workspace"
        ]:
            return subprocess.CompletedProcess(arguments, 0, "true\n", "")
        if arguments[1:3] == ["sessions", "export"]:
            self.exports += 1
            session = arguments[arguments.index("--session-id") + 1]
            payload = {
                "id": session,
                "messages": [
                    {"role": "user", "content": "redacted eval prompt"},
                    {
                        "role": "assistant",
                        "tool_calls": [{"function": {"name": "write_file", "arguments": "{}"}}],
                    },
                    {"role": "tool", "tool_name": "write_file", "content": "wrote isolated output"},
                    {"role": "assistant", "content": "complete"},
                ],
            }
            return subprocess.CompletedProcess(arguments, 0, json.dumps(payload) + "\n", "")
        if "Judge this complete" in prompt or "Normalize the prior evaluator" in prompt:
            self.judge_calls.append(arguments)
            if self.narrative_first_judge and len(self.judge_calls) == 1:
                return subprocess.CompletedProcess(
                    arguments, 0, "All eight cases pass, but this is prose.", ""
                )
            if "Judge this complete" in prompt:
                source = json.loads(prompt.split("INPUT:\n", 1)[1])
                source_cases = source["cases"]
            else:
                repair = json.loads(prompt.split("\n\n", 1)[1])
                source_cases = [
                    {
                        "eval_id": case["eval_id"],
                        "assertions": [None] * case["assertion_count"],
                        "artifacts": [{"path": "normalized-result.md"}],
                    }
                    for case in repair["cases"]
                ]
            rows = []
            for case in source_cases:
                if case["eval_id"] == self.omit_judgment:
                    continue
                rows.append(
                    {
                        "eval_id": case["eval_id"],
                        "status": "passed",
                        "assertions": [
                            {
                                "index": index,
                                "met": True,
                                "evidence": [f"{case['artifacts'][0]['path']}: observed"],
                            }
                            for index, _ in enumerate(case["assertions"])
                        ],
                        "reason": "all evidence present",
                    }
                )
            return subprocess.CompletedProcess(
                arguments, 0, json.dumps({"overall": "passed", "eval_results": rows}), ""
            )
        self.generation_calls.append(arguments)
        manifest = json.loads(prompt.split("MANIFEST:\n", 1)[1])
        working_directory = Path(arguments[arguments.index("--in") + 1])
        for case in manifest:
            if case["eval_id"] == self.omit_eval:
                continue
            container_scenario = Path(case["scenario"])
            output = (
                working_directory
                / container_scenario.relative_to("/workspace")
                / "outputs/result.md"
            )
            output.write_text(f"# {case['eval_id']}\n\nObserved fixture evidence.\n", encoding="utf-8")
        cadence = "daily" if "PM daily" in prompt else "weekly"
        return subprocess.CompletedProcess(arguments, 0, "complete", f"\nsession_id: {cadence}-session\n")


class EvaluationRunnerTests(unittest.TestCase):
    def test_shared_run_invokes_each_cadence_once_and_one_no_tools_judge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            fake = FakeHermes()
            receipt = evaluation.run_evaluation(
                profile, root=ROOT, command_runner=fake, run_id="test-run", timeout=30
            )
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["run_mode"], "analysis_only")
            self.assertEqual(receipt["provider_mutations"], 0)
            self.assertEqual(receipt["judge_calls"], 1)
            self.assertEqual(set(receipt["automation_runs"]), {"daily", "weekly"})
            self.assertTrue(all(row["status"] == "passed" for row in receipt["automation_runs"].values()))
            self.assertEqual(len(fake.generation_calls), 2)
            self.assertEqual(fake.exports, 2)
            self.assertEqual(len(fake.judge_calls), 1)
            self.assertTrue(all(call[call.index("--toolsets") + 1] == "file" for call in fake.generation_calls))
            judge = fake.judge_calls[0]
            self.assertEqual(judge[judge.index("--toolsets") + 1], "context_engine")
            self.assertEqual(judge[judge.index("--reasoning") + 1], "none")
            self.assertEqual(judge[judge.index("--max-turns") + 1], "1")
            expected_ids = {
                case["id"]
                for cases in evaluation.load_catalog(ROOT).values()
                for case in cases
            }
            self.assertEqual({row["eval_id"] for row in receipt["eval_results"]}, expected_ids)
            self.assertEqual(len(receipt["eval_results"]), 8)
            run = profile / "workspace/.company-os/eval-runs/test-run"
            self.assertTrue((run / "dossier/index.html").is_file())
            self.assertTrue((run / "traces/daily.json").is_file())
            self.assertEqual(stat.S_IMODE((run / "eval-receipt.json").stat().st_mode), 0o600)
            self.assertEqual(
                stat.S_IMODE(
                    (profile / "workspace/.company-os/eval-runs/latest.json").stat().st_mode
                ),
                0o600,
            )

    def test_mutually_exclusive_scenarios_receive_private_fixture_copies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            run, suites = evaluation.prepare_run(profile, root=ROOT, run_id="isolated")
            daily = run / "daily/scenarios"
            for case in suites["daily"]:
                scenario = daily / case["id"]
                self.assertTrue((scenario / "case.json").is_file())
                self.assertEqual(stat.S_IMODE(scenario.stat().st_mode), 0o700)
                for relative in case["files"]:
                    copied = scenario / "inputs" / relative
                    self.assertTrue(copied.is_file())
                    self.assertEqual(stat.S_IMODE(copied.stat().st_mode), 0o600)
            first = daily / suites["daily"][0]["id"] / "inputs/evals/fixtures/daily-snapshot.json"
            second = daily / suites["daily"][1]["id"] / "inputs/evals/fixtures/daily-snapshot.json"
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_missing_scenario_output_fails_before_judgment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake = FakeHermes(omit_eval="healthy_work_noop")
            with self.assertRaisesRegex(evaluation.EvaluationError, "eval_output_missing"):
                evaluation.run_evaluation(
                    Path(temporary), root=ROOT, command_runner=fake, run_id="missing", timeout=30
                )
            self.assertEqual(fake.judge_calls, [])

    def test_missing_judgment_or_assertion_evidence_fails_closed(self) -> None:
        suites = evaluation.load_catalog(ROOT)
        rows = []
        for cases in suites.values():
            for case in cases:
                rows.append(
                    {
                        "eval_id": case["id"],
                        "status": "passed",
                        "assertions": [
                            {"index": index, "met": True, "evidence": ["result.md: observed"]}
                            for index, _ in enumerate(case["assertions"])
                        ],
                        "reason": "all evidence present",
                    }
                )
        with self.assertRaisesRegex(evaluation.EvaluationError, "missing_case"):
            evaluation.validate_judgment(
                {"overall": "passed", "eval_results": rows[:-1]}, suites
            )
        rows[0]["assertions"][0]["evidence"] = []
        with self.assertRaisesRegex(evaluation.EvaluationError, "invalid_assertion"):
            evaluation.validate_judgment(
                {"overall": "passed", "eval_results": rows}, suites
            )

    def test_open_latest_validates_receipt_and_uses_file_uri(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            evaluation.run_evaluation(
                profile, root=ROOT, command_runner=FakeHermes(), run_id="openable", timeout=30
            )
            opened: list[str] = []
            uri = evaluation.open_latest_dossier(
                profile, root=ROOT, opener=lambda value: opened.append(value) or True
            )
            self.assertEqual(opened, [uri])
            self.assertTrue(uri.startswith("file://"))
            receipt = profile / "workspace/.company-os/eval-runs/openable/eval-receipt.json"
            receipt.write_text(receipt.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaisesRegex(evaluation.EvaluationError, "receipt_stale"):
                evaluation.open_latest_dossier(profile, root=ROOT, opener=lambda _: True)

    def test_open_latest_rejects_tampered_output_or_dossier(self) -> None:
        for relative in (
            "daily/scenarios/healthy_work_noop/outputs/result.md",
            "dossier/index.html",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temporary:
                profile = Path(temporary)
                evaluation.run_evaluation(
                    profile, root=ROOT, command_runner=FakeHermes(),
                    run_id="tampered", timeout=30,
                )
                artifact = profile / "workspace/.company-os/eval-runs/tampered" / relative
                artifact.write_text(
                    artifact.read_text(encoding="utf-8") + "\ntampered\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(evaluation.EvaluationError, "artifact_stale"):
                    evaluation.latest_valid_index(profile, root=ROOT)

    def test_trace_with_non_file_tool_fails_safety_boundary(self) -> None:
        raw = json.dumps(
            {
                "messages": [
                    {"role": "assistant", "tool_calls": [{"function": {"name": "mcp_notion", "arguments": "{}"}}]},
                    {"role": "tool", "tool_name": "mcp_notion", "content": "called"},
                ]
            }
        )
        trace = evaluation._compact_trace(raw)
        self.assertFalse(evaluation._tool_names(trace).issubset(evaluation.ALLOWED_GENERATION_TOOLS))

    def test_eval_fails_before_generation_without_persistent_workspace_mount(self) -> None:
        calls: list[list[str]] = []

        def missing_mount(arguments, profile_home, **kwargs):
            del profile_home, kwargs
            calls.append(arguments)
            output = "docker\n" if arguments[-1] == "terminal.backend" else "false\n"
            return subprocess.CompletedProcess(arguments, 0, output, "")

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                evaluation.EvaluationError,
                "eval_runtime_config_invalid:terminal.docker_mount_cwd_to_workspace",
            ):
                evaluation.run_evaluation(
                    Path(temporary), root=ROOT, command_runner=missing_mount,
                    run_id="no-mount", timeout=30,
                )
        self.assertEqual(len(calls), 2)

    def test_narrative_judge_is_repaired_once_into_strict_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fake = FakeHermes(narrative_first_judge=True)
            receipt = evaluation.run_evaluation(
                Path(temporary), root=ROOT, command_runner=fake,
                run_id="judge-repair", timeout=30,
            )
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["judge_calls"], 2)
        self.assertEqual(len(fake.judge_calls), 2)


if __name__ == "__main__":
    unittest.main()
