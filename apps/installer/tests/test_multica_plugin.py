from __future__ import annotations

import json
import subprocess
import unittest
from unittest.mock import patch

from plugins import multica


class MulticaPluginTests(unittest.TestCase):
    def test_issue_list_is_bounded_and_uses_exact_workspace(self) -> None:
        completed = subprocess.CompletedProcess([], 0, '{"issues": []}', "")
        with (
            patch.object(multica, "_binary", return_value="/opt/multica"),
            patch.object(multica.subprocess, "run", return_value=completed) as run,
        ):
            payload = json.loads(multica._list_issues({
                "workspace_id": "workspace-1", "project": "project-1", "limit": 500,
            }))
        self.assertEqual(payload, {"issues": []})
        command = run.call_args.args[0]
        self.assertIn("workspace-1", command)
        self.assertIn("project-1", command)
        self.assertEqual(command[command.index("--limit") + 1], "100")
        self.assertFalse(run.call_args.kwargs["shell"] if "shell" in run.call_args.kwargs else False)

    def test_create_uses_title_flag_and_never_invokes_a_shell(self) -> None:
        completed = subprocess.CompletedProcess([], 0, '{"id": "issue-1"}', "")
        with (
            patch.object(multica, "_binary", return_value="/opt/multica"),
            patch.object(multica.subprocess, "run", return_value=completed) as run,
        ):
            payload = json.loads(multica._create_issue({
                "workspace_id": "workspace-1", "title": "Weekly review",
            }))
        self.assertEqual(payload["id"], "issue-1")
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--title") + 1], "Weekly review")
        self.assertNotIn("--allow-duplicate", command)


if __name__ == "__main__":
    unittest.main()
