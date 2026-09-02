from __future__ import annotations

import json
import stat
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from apps.installer import provider_catalog
from apps.installer import connection_evals as run_connection_evals
from apps.installer import runtime as setup_runtime


class FakeHermes:
    def __init__(self, *, include_tool_result: bool = True) -> None:
        self.include_tool_result = include_tool_result
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.executor_calls = 0
        self.judge_calls = 0
        self.executor_arguments: list[list[str]] = []

    def __call__(self, arguments, profile_home, **kwargs):
        del profile_home
        input_text = kwargs.get("input_text", "") or ""
        if arguments[1:3] == ["sessions", "export"]:
            messages = [
                {"role": "user", "content": "connection test"},
                {"role": "assistant", "tool_calls": [{"function": {"name": "mcp_test", "arguments": "{}"}}]},
            ]
            if self.include_tool_result:
                messages.append({"role": "tool", "tool_name": "mcp_test", "content": "provider read-back succeeded"})
            messages.append({"role": "assistant", "content": "Provider object ID and URL matched."})
            payload = {"id": arguments[arguments.index("--session-id") + 1], "messages": messages}
            return subprocess.CompletedProcess(arguments, 0, json.dumps(payload) + "\n", "")
        if "Judge this batch" in input_text:
            self.judge_calls += 1
            source = json.loads(input_text.split("INPUT:\n", 1)[1])
            rows = []
            for case in source["cases"]:
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "status": "passed",
                        "assertions": [
                            {"index": index, "passed": True, "evidence": "observed in redacted trace"}
                            for index, _ in enumerate(case["assertions"])
                        ],
                        "reason": "all assertions observed",
                    }
                )
            return subprocess.CompletedProcess(
                arguments,
                0,
                json.dumps({"overall": "passed", "cases": rows}),
                "\nsession_id: judge-session\n",
            )
        with self.lock:
            self.executor_calls += 1
            self.executor_arguments.append(arguments)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            session = f"case-{self.executor_calls}"
        time.sleep(0.02)
        with self.lock:
            self.active -= 1
        return subprocess.CompletedProcess(
            arguments,
            0,
            "Provider object ID and URL matched.",
            f"\nsession_id: {session}\n",
        )


def workspace(path: Path) -> Path:
    path.write_text(
        "<!-- hermes:managed data-sources -->\n"
        "| Role | Provider | Source | Access | Scope |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `projects` | notion | https://notion.example.test/projects | read | test |\n"
        "| `tasks` | linear | https://linear.example.test/team | read | test |\n"
        "<!-- /hermes:managed data-sources -->\n",
        encoding="utf-8",
    )
    return path


class ConnectionEvalTests(unittest.TestCase):
    def test_cases_run_in_parallel_and_use_one_batch_judge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeHermes()
            receipt = run_connection_evals.run_connection_evals(
                root,
                workspace(root / "workspace.md"),
                command_runner=fake,
                allow_side_effects=True,
                run_id="test-run",
            )
            self.assertEqual(receipt["status"], "passed")
            self.assertEqual(receipt["judge_calls"], 1)
            self.assertEqual(fake.judge_calls, 1)
            self.assertEqual(fake.executor_calls, 2)
            self.assertGreaterEqual(fake.max_active, 2)
            self.assertEqual({case["precheck"] for case in receipt["cases"]}, {"passed"})
            self.assertEqual(
                {
                    arguments[arguments.index("--toolsets") + 1]
                    for arguments in fake.executor_arguments
                },
                {"notion", "linear"},
            )
            self.assertTrue(
                all("--ignore-rules" in arguments for arguments in fake.executor_arguments)
            )

    def test_missing_tool_result_cannot_be_overridden_by_judge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeHermes(include_tool_result=False)
            receipt = run_connection_evals.run_connection_evals(
                root,
                workspace(root / "workspace.md"),
                command_runner=fake,
                allow_side_effects=True,
                run_id="test-run",
            )
            self.assertEqual(receipt["status"], "failed")
            self.assertEqual(fake.judge_calls, 1)
            self.assertTrue(all(case["precheck"] == "failed" for case in receipt["cases"]))
            self.assertTrue(all(row["status"] == "failed" for row in receipt["judgment"]["cases"]))

    def test_failed_assertion_cannot_keep_a_passing_case_status(self) -> None:
        cases = [
            {
                "case_id": "projects:notion",
                "assertions": ["created", "fetched"],
                "precheck": "passed",
            }
        ]
        judgment = {
            "overall": "passed",
            "cases": [
                {
                    "case_id": "projects:notion",
                    "status": "passed",
                    "assertions": [
                        {"index": 0, "passed": True, "evidence": "created"},
                        {"index": 1, "passed": False, "evidence": "not fetched"},
                    ],
                    "reason": "inconsistent judge output",
                }
            ],
        }
        normalized = run_connection_evals._validate_judgment(judgment, cases)
        self.assertEqual(normalized["overall"], "failed")
        self.assertEqual(normalized["cases"][0]["status"], "failed")

    def test_reversible_cases_require_explicit_side_effect_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeHermes()
            receipt = run_connection_evals.run_connection_evals(
                root,
                workspace(root / "workspace.md"),
                command_runner=fake,
                allow_side_effects=False,
                run_id="test-run",
            )
            self.assertEqual(receipt["status"], "human_required")
            self.assertEqual([row["case_id"] for row in receipt["blocked"]], ["projects:notion"])
            self.assertEqual(fake.executor_calls, 1)
            self.assertEqual(fake.judge_calls, 1)

    def test_receipt_is_owner_only_and_health_binds_to_configuration_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            workspace_path = workspace(profile / "workspace.hermes.md")
            fake = FakeHermes()
            receipt = run_connection_evals.run_connection_evals(
                profile,
                workspace_path,
                command_runner=fake,
                allow_side_effects=True,
                run_id="test-run",
            )
            path = run_connection_evals.write_receipt(profile, receipt)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
            lane = setup_runtime._connection_eval_lane(profile, live=True)
            self.assertEqual(lane["status"], "pass")
            workspace_path.write_text(
                workspace_path.read_text(encoding="utf-8").replace(
                    "https://linear.example.test/team", "https://linear.example.test/other"
                ),
                encoding="utf-8",
            )
            stale = setup_runtime._connection_eval_lane(profile, live=True)
            self.assertEqual(stale["status"], "fail")
            self.assertIn("stale", stale["detail"])

    def test_invalid_execution_limits_fail_before_running_hermes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = FakeHermes()
            with self.assertRaisesRegex(
                run_connection_evals.ConnectionEvalError,
                "max_workers_must_be_positive",
            ):
                run_connection_evals.run_connection_evals(
                    root,
                    workspace(root / "workspace.md"),
                    command_runner=fake,
                    max_workers=0,
                )
            self.assertEqual(fake.executor_calls, 0)

    def test_deferred_certification_is_retryable_and_health_is_partial_not_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            workspace_path = workspace(profile / "workspace.hermes.md")
            deferred = run_connection_evals.defer_connection_evals(
                profile, workspace_path
            )
            self.assertEqual(deferred["status"], "deferred")
            self.assertEqual(deferred["last_attempt_status"], "not_run")
            lane = setup_runtime._connection_eval_lane(profile, live=True)
            self.assertEqual(lane["status"], "fail")
            self.assertFalse(lane["required"])
            self.assertIn("Test integrations", lane["detail"])

    def test_deferring_after_failure_preserves_the_failed_run_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            workspace_path = workspace(profile / "workspace.hermes.md")
            previous = {
                "run_id": "failed-run",
                "status": "failed",
                "cases": [{"case_id": "projects:notion", "status": "failed"}],
            }
            run_connection_evals.write_receipt(profile, previous)
            deferred = run_connection_evals.defer_connection_evals(
                profile, workspace_path, previous=previous
            )
            self.assertNotEqual(deferred["run_id"], previous["run_id"])
            self.assertEqual(deferred["previous_run_id"], previous["run_id"])
            self.assertEqual(
                json.loads(
                    (profile / "state/connection-evals/failed-run.json").read_text()
                )["status"],
                "failed",
            )


if __name__ == "__main__":
    unittest.main()
