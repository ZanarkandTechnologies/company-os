from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from apps.installer.cli.flows.features import (
    QUESTIONS,
    QuestionAnswer,
    _ask_question,
    _ask_delivery_question,
    _ask_custom_providers,
    collect_answers,
    collect_identity,
)
from apps.installer.feature_setup import SLOT


ROOT = Path(__file__).resolve().parents[3]


class FeatureFlowTests(unittest.TestCase):
    def test_every_screen_has_explainer_presets_custom_and_back(self) -> None:
        self.assertEqual(len(QUESTIONS), 21)
        self.assertTrue(all(question.explainer.strip() for question in QUESTIONS))
        self.assertTrue(all(len(question.presets) >= 2 for question in QUESTIONS))
        self.assertTrue(all(question.custom_hint.strip() for question in QUESTIONS))
        source = (ROOT / "apps/installer/cli/flows/features.py").read_text(encoding="utf-8")
        self.assertIn("choose_many", source)
        self.assertIn('["back"]', source)

    def test_question_keys_cover_every_automation_slot(self) -> None:
        slots: set[str] = set()
        for path in (
            ROOT / "automations/daily-operating-update.md",
            ROOT / "automations/weekly-operating-review.md",
            ROOT / "automations/weekly-meeting-ticket.md",
        ):
            slots.update(match.group("key") for match in SLOT.finditer(path.read_text(encoding="utf-8")))
        question_keys = {question.key for question in QUESTIONS} | {"weekly.projects"}
        self.assertEqual(question_keys, slots)

    def test_project_memory_sync_is_the_final_feature_screen(self) -> None:
        self.assertEqual(QUESTIONS[-1].key, "weekly.project_memory_destination")

    def test_saved_answer_is_the_default_and_back_changes_no_value(self) -> None:
        question = QUESTIONS[0]
        with patch("apps.installer.cli.flows.features.choose", return_value="keep"):
            self.assertEqual(
                _ask_question(question, "saved answer", 1),
                QuestionAnswer("saved answer", "keep", (), {}),
            )
        with patch("apps.installer.cli.flows.features.choose", return_value="back"):
            self.assertIsNone(_ask_question(question, "saved answer", 1))

    def test_weekly_delivery_collects_each_selected_channel_target(self) -> None:
        question = next(item for item in QUESTIONS if item.key == "weekly.report_recipients")
        with (
            patch("apps.installer.cli.flows.features.choose_many", return_value=["Telegram", "WhatsApp"]),
            patch("apps.installer.cli.flows.features._required_text", side_effect=["telegram:1,telegram:2", "+60123456789"]),
        ):
            answer = _ask_delivery_question(question, None, 1)
        self.assertEqual(answer.providers, ("telegram", "whatsapp"))
        self.assertIn("telegram:1,telegram:2", answer.value)
        self.assertIn("+60123456789", answer.value)

    def test_custom_delivery_collects_required_integrations(self) -> None:
        question = next(
            item for item in QUESTIONS if item.key == "weekly.report_recipients"
        )
        with (
            patch(
                "apps.installer.cli.flows.features.choose_many",
                return_value=["Custom instructions"],
            ),
            patch(
                "apps.installer.cli.flows.features._required_text",
                return_value="Send through the approved executive channel.",
            ),
            patch(
                "apps.installer.cli.flows.features._ask_custom_providers",
                return_value=("telegram",),
            ),
        ):
            answer = _ask_delivery_question(question, None, 1)
        self.assertEqual(answer.providers, ("telegram",))

    def test_back_exits_custom_multiple_integrations_prompt(self) -> None:
        with (
            patch("apps.installer.cli.flows.features.choose", return_value="multiple"),
            patch("apps.installer.cli.flows.features._required_text", return_value="back"),
        ):
            self.assertIsNone(_ask_custom_providers("daily.progress_route"))

    def test_back_from_first_identity_screen_cancels_without_writing(self) -> None:
        with patch(
            "apps.installer.cli.flows.features._required_text", return_value="back"
        ):
            self.assertIsNone(collect_identity({}))

    def test_kept_direct_route_cannot_survive_disabling_people_contacts(self) -> None:
        answers = {question.key: f"saved {question.key}" for question in QUESTIONS}
        selections = {question.key: "preset_1" for question in QUESTIONS}
        requirements = {
            "daily.people": ("notion",),
            "daily.progress_route": ("notion", "gmail"),
            "daily.documentation_route": ("notion", "telegram"),
        }
        people_visits = 0

        def answer(question, current, position):
            nonlocal people_visits
            if question.key == "daily.people":
                people_visits += 1
                if people_visits == 1:
                    return QuestionAnswer(
                        "Do not fetch contacts.", "preset_2", (), {}
                    )
                return QuestionAnswer(
                    "Fetch People from https://notion.so/people.",
                    "preset_1",
                    ("notion",),
                    {"notion": "https://notion.so/people"},
                )
            return QuestionAnswer(current, "keep", (), {})

        with patch("apps.installer.cli.flows.features._ask_question", side_effect=answer):
            result = collect_answers(answers, selections, requirements, {})
        self.assertEqual(people_visits, 2)
        self.assertEqual(result[1]["daily.people"], "preset_1")


if __name__ == "__main__":
    unittest.main()
