from pathlib import Path
import re
import unittest


TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "templates"
    / "company-workspace.hermes.md"
)
PACKAGE_ROOT = TEMPLATE.parents[2]
SCRIPT = PACKAGE_ROOT / "scripts" / "onboard_company.py"
SURFACES = ("Work", "People", "Knowledge", "Communications", "Decisions")


class CompanyWorkspaceTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.content = TEMPLATE.read_text(encoding="utf-8")

    def test_metadata_names_template_and_runtime_target(self) -> None:
        self.assertIn("template_id: hermes-company-workspace", self.content)
        self.assertIn('template_version: "0.3.0"', self.content)
        self.assertIn("status: proposed-owner-review", self.content)
        self.assertIn("kind: hermes-project-context", self.content)
        self.assertIn("target_file: .hermes.md", self.content)

    def test_only_required_company_metadata_are_scalar_placeholders(self) -> None:
        placeholders = set(re.findall(r"{{([A-Z_]+)}}", self.content))
        self.assertEqual(placeholders, {"COMPANY_NAME", "COMPANY_DESCRIPTION", "COMPANY_TIMEZONE"})

    def test_work_row_binds_template_routing_and_comment_policy(self) -> None:
        self.assertIn("Work Item template", self.content)
        self.assertIn("Templates: Task/Issue/Meeting", self.content)
        self.assertIn("Internal comments: proposal-only or approved", self.content)

    def test_all_five_surfaces_have_repeatable_source_rows(self) -> None:
        for surface in SURFACES:
            self.assertEqual(self.content.count(f"## {surface}\n"), 1)
        self.assertEqual(
            self.content.count("| Platform | Use via (skill, CLI, or MCP) | Pages or sources | How it is structured |"),
            len(SURFACES),
        )
        self.assertGreaterEqual(self.content.count("Duplicate the row"), len(SURFACES))

    def test_template_carries_secret_and_write_boundaries(self) -> None:
        self.assertIn("Never store credentials, tokens, passwords, or private keys", self.content)
        self.assertIn("Confirm before sending messages", self.content)

    def test_package_exposes_no_component_skill_scaffolding(self) -> None:
        self.assertFalse((PACKAGE_ROOT / "scripts" / "company_skills.py").exists())
        self.assertFalse((PACKAGE_ROOT / "scripts" / "onboarding.py").exists())
        legacy_templates = sorted(
            (PACKAGE_ROOT / "assets" / "templates").glob("company-*/SKILL.md")
        )
        self.assertEqual(legacy_templates, [])

    def test_package_exposes_deterministic_onboarding_helper(self) -> None:
        self.assertTrue(SCRIPT.is_file())


if __name__ == "__main__":
    unittest.main()
