from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class CompanyOSTests(unittest.TestCase):
    def test_automation_markdown_contracts_exist(self) -> None:
        daily = (ROOT / "automations/daily-operating-update.md").read_text(encoding="utf-8")
        weekly = (ROOT / "automations/weekly-operating-review.md").read_text(encoding="utf-8")
        for automation, cadence in ((daily, "daily"), (weekly, "weekly")):
            self.assertIn(f"cadence: {cadence}", automation)
            self.assertIn("## Authority", automation)
            self.assertNotIn("workspace.hermes.md", automation)
            self.assertNotIn("ntn --help", automation)
            self.assertIn("hosted Notion MCP", automation)
            self.assertNotIn("skills/company-os", automation)
        self.assertIn("skills/pm-daily/SKILL.md", daily)
        self.assertIn("skills/pm-weekly/SKILL.md", weekly)
        self.assertIn("at most 1,900 characters", weekly)
        self.assertIn("[company-os:<token>:part <number>/<count>]", weekly)
        self.assertLess(daily.index("[Daily parent]"), daily.index("## Purpose"))
        self.assertIn("Run PM Daily once per packet in a native subagent", daily)
        self.assertNotIn("## Deployment values", daily)
        self.assertGreater(daily.index("<!-- setup:daily.projects -->"), daily.index("**1 — Build"))
        self.assertGreater(daily.index("<!-- setup:daily.people -->"), daily.index("**1 — Build"))
        self.assertGreater(daily.index("<!-- setup:daily.progress_route -->"), daily.index("**4 — Apply authorized effects"))
        self.assertIn("Record completeness facts", daily)
        self.assertIn("`contact_route_missing`", daily)
        self.assertIn("question plus the exact Work source", daily)
        self.assertIn("one attempt for each `notion_comment`, `gmail`, `telegram`, or", daily)
        self.assertIn("`whatsapp`", daily)
        self.assertIn("Reject overlapping write paths", daily)
        self.assertIn("Keep every `project_memory` file local", daily)
        self.assertIn("each `documentation_request` and `progress_followup`", daily)
        self.assertIn("`notion-fetch`", daily)
        self.assertIn("`notion-create-comment`", daily)
        self.assertIn("`notion-get-comments`", daily)
        self.assertIn("`conversations_list`", daily)
        self.assertIn("`conversation_get`", daily)
        self.assertNotIn("notion_create_page_comment", daily)
        self.assertNotIn("TASKS_URL=", daily)
        self.assertIn("one snapshot for every active Project", daily)
        self.assertIn("`raw_status`", daily)
        self.assertIn("`normalized_status`", daily)
        self.assertIn("`project_work_source_missing`", daily)
        self.assertIn("`task_schema_gap`", daily)
        self.assertIn("`templates/task.md` as the remediation template", daily)
        missing_source_policy = daily.split(
            "If a Project has no", 1
        )[1].split("- [ ] **2", 1)[0]
        self.assertIn("Do not create a follow-up", missing_source_policy)
        self.assertIn("Notion comment", missing_source_policy)
        for template_name, artifact_type in (
            ("documentation-request.md", "documentation_request"),
            ("employee-followups.md", "progress_followup"),
        ):
            template = (
                ROOT / "skills" / "pm-daily" / "templates" / template_name
            ).read_text(encoding="utf-8")
            self.assertIn(f"artifact_type: {artifact_type}", template)
            self.assertIn('work_id: "{{WORK_ID}}"', template)
            self.assertIn('source_provider: "{{SOURCE_PROVIDER}}"', template)
            self.assertIn('provider_record_id: "{{PROVIDER_RECORD_ID}}"', template)
            self.assertIn('source_reference: "{{SOURCE_REFERENCE}}"', template)
            self.assertIn('source_url: "{{SOURCE_URL_OR_EMPTY}}"', template)
        daily_integration_outputs = daily.split("## Integration outputs", 1)[1]
        self.assertIn("daily/context/daily-snapshot", daily_integration_outputs)
        self.assertIn("daily/receipts/daily-", daily_integration_outputs)
        self.assertNotIn("project-memory", daily_integration_outputs)
        self.assertNotIn("daily/messages", daily_integration_outputs)
        self.assertLess(weekly.index("[Weekly parent]"), weekly.index("## Purpose"))
        self.assertNotIn("## Deployment values", weekly)
        self.assertGreater(weekly.index("<!-- setup:weekly.projects -->"), weekly.index("**1 — Freeze"))
        self.assertIn("by Person ID", weekly)
        self.assertIn("by workflow_key", weekly)
        weekly_skill = (ROOT / "skills" / "pm-weekly" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for artifact_type in (
            "project_report",
            "department_report",
            "company_report",
            "employee_memory",
            "sop_memory",
            "issue_memory",
            "decision_memory",
            "next_week_project_memory",
            "executive_distribution",
        ):
            self.assertIn(f"`{artifact_type}`", weekly_skill)
            self.assertIn(f"`{artifact_type}`", weekly)
        sync_start = weekly.index("**4 — Sync authorized artifacts")
        self.assertGreater(weekly.index("<!-- setup:weekly.reports_destination -->", sync_start), sync_start)
        weekly_integration_outputs = weekly.split("## Integration outputs", 1)[1]
        self.assertIn("weekly/context/weekly-snapshot", weekly_integration_outputs)
        self.assertIn("weekly/receipts/weekly-", weekly_integration_outputs)
        self.assertNotIn("weeks/<week>/reports", weekly_integration_outputs)
        self.assertNotIn("memory/{employees", weekly_integration_outputs)
        self.assertNotIn("javascript", daily.lower())
        self.assertNotIn("javascript", weekly.lower())

    def test_runtime_setup_installs_only_the_two_pm_skills(self) -> None:
        skills = ROOT / "skills"
        packages = sorted(path.parent.name for path in skills.glob("*/SKILL.md")) if skills.exists() else []
        self.assertEqual(packages, ["pm-daily", "pm-weekly"])
        self.assertTrue((ROOT / "apps/installer/profile.py").is_file())
        self.assertTrue((ROOT / "apps/installer/workspace.py").is_file())

    def test_pm_eval_catalogs_are_capability_owned_and_feature_free(self) -> None:
        expected = {
            "pm-daily": {
                "documentation_quality_follow_up",
                "progress_chaser",
                "project_memory_update",
                "healthy_work_noop",
            },
            "pm-weekly": {
                "weekly_operating_reports",
                "knowledge_promotion",
                "next_week_carry_forward",
                "incomplete_project_set_blocks_rollup",
            },
        }
        for skill_name, expected_ids in expected.items():
            path = ROOT / "skills" / skill_name / "evals" / "evals.json"
            suite = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(suite["skill_name"], skill_name)
            self.assertEqual({row["id"] for row in suite["evals"]}, expected_ids)
            self.assertFalse((ROOT / "skills" / skill_name / "evals.json").exists())
            for row in suite["evals"]:
                self.assertNotIn("feature_ids", row)
                self.assertNotIn("priority", json.dumps(row).lower())
                self.assertTrue(row["metadata"]["title"])
                self.assertTrue(row["metadata"]["notes"])
                self.assertTrue(row["assertions"])
                for relative in row["files"]:
                    self.assertTrue((ROOT / "skills" / skill_name / relative).is_file(), relative)

    def test_live_context_is_ignored_but_reviewable_config_is_tracked(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/.hermes.md", ignored)
        proposal = (ROOT / "workspace.hermes.md").read_text(encoding="utf-8")
        self.assertIn('company_timezone: "UTC"', proposal)
        self.assertIn("skills/pm-daily/templates/project-memory.md", proposal)
        self.assertIn("Project Memory", proposal)
        self.assertIn("SOP Memory", proposal)
        self.assertIn("proposal-only", proposal)

    def test_product_docs_and_two_skills_own_product_behavior(self) -> None:
        docs = sorted(path.name for path in (ROOT / "docs").glob("*.md"))
        self.assertEqual(
            docs,
            [
                "autonomous-testing.md",
                "discord-v1-delivery-contract.md",
                "operator-guide.md",
                "prd.md",
                "tuning-sop.md",
            ],
        )
        for removed in ("features", "research", "systems"):
            self.assertFalse((ROOT / "docs" / removed).exists())
        prd = (ROOT / "docs/prd.md").read_text(encoding="utf-8")
        operator = (ROOT / "docs/operator-guide.md").read_text(encoding="utf-8")
        for skill in ("pm-daily", "pm-weekly"):
            self.assertIn(f"skills/{skill}/SKILL.md", prd)
            self.assertIn(f"skills/{skill}/SKILL.md", operator)

    def test_template_registry_has_pinned_and_derived_contracts(self) -> None:
        expected = {
            "templates/project.md": "company-os-project",
            "templates/person.md": "company-os-person",
            "templates/task.md": "company-os-task",
            "templates/feature.md": "company-os-feature",
            "templates/decision.md": "company-os-decision",
            "skills/pm-weekly/templates/weekly-report.md": "company-os-weekly-report",
            "skills/pm-weekly/templates/area-operating-rollup.md": "company-os-area-operating-rollup",
            "skills/pm-weekly/templates/company-operating-rollup.md": "company-os-company-operating-rollup",
            "skills/pm-daily/templates/employee-followups.md": "company-os-employee-followups",
            "skills/pm-daily/templates/documentation-request.md": "company-os-documentation-request",
            "templates/sop.md": "company-os-employee-sop",
            "skills/pm-weekly/templates/executive-distribution.md": "company-os-executive-distribution",
            "templates/issue.md": "company-os-issue",
            "templates/meeting.md": "company-os-meeting",
        }
        for filename, template_id in expected.items():
            content = (ROOT / filename).read_text(encoding="utf-8")
            self.assertIn(f"template_id: {template_id}", content, filename)
            self.assertIn("template_version:", content, filename)
        for filename in expected:
            content = (ROOT / filename).read_text(encoding="utf-8")
            self.assertNotIn("required_properties:", content, filename)
            self.assertNotIn("upstream_source:", content, filename)

        shared_work_fields = ("work_item_id", "project", "department", "owner", "type",
                              "status", "priority", "start_date", "due_date", "progress",
                              "last_meaningful_update")
        for filename in ("task.md", "feature.md", "issue.md", "meeting.md"):
            content = (ROOT / "templates" / filename).read_text(encoding="utf-8")
            for field in shared_work_fields:
                self.assertIn(f"{field}:", content, f"{filename}: {field}")

        for filename in (
            "templates/project.md", "templates/task.md", "templates/feature.md", "templates/issue.md", "templates/meeting.md",
            "skills/pm-weekly/templates/weekly-report.md", "skills/pm-weekly/templates/area-operating-rollup.md", "skills/pm-weekly/templates/company-operating-rollup.md",
            "templates/decision.md", "templates/sop.md",
        ):
            content = (ROOT / filename).read_text(encoding="utf-8")
            self.assertIn("GOLDEN EXAMPLE", content, filename)

        person = (ROOT / "templates/person.md").read_text(encoding="utf-8")
        for field in ("preferred_contact_channel", "approved_contact_channels",
                      "contact_endpoint", "contact_instructions", "timezone", "expertise"):
            self.assertIn(f"{field}:", person, field)
        self.assertIn("Persistent operating memory", person)
        self.assertIn("Latest weekly evidence", person)
        self.assertIn("private local context", person)

        sop = (ROOT / "templates/sop.md").read_text(encoding="utf-8")
        self.assertIn("Long-term context", sop)
        self.assertIn("Short-term interval context", sop)
        self.assertIn("same output and acceptance controls", sop)
        self.assertIn("explicit approval", sop)

        weekly = (ROOT / "skills/pm-weekly/templates/weekly-report.md").read_text(encoding="utf-8")
        for section in (
            "Summary", "Outcomes and open attention", "Accepted outputs by employee", "Problems and inefficiencies",
            "Decisions", "SOPs", "Next-week priorities",
        ):
            self.assertIn(f"## {section}", weekly)

        area = (ROOT / "skills/pm-weekly/templates/area-operating-rollup.md").read_text(encoding="utf-8")
        self.assertIn("## Accepted outputs by employee", area)
        self.assertIn("who produced what", area)

    def test_proposed_context_validates(self) -> None:
        result = subprocess.run(
             [sys.executable, str(ROOT / "apps/installer/validate_context.py"),
             "--context", str(ROOT / "workspace.hermes.md")],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("context_valid=true", result.stdout)

if __name__ == "__main__":
    unittest.main()
