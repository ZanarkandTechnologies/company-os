from __future__ import annotations

import unittest

from apps.installer import model_output


class ModelOutputTests(unittest.TestCase):
    def test_fenced_json_survives_hermes_reasoning_presentation(self) -> None:
        raw = (
            "Reasoning panel echoed {\"schema\":\"example\"}\n"
            "```json\n{\"overall\":\"passed\",\"cases\":[]}\n```\n"
        )
        self.assertEqual(
            model_output.json_object(raw, ValueError("invalid")),
            {"overall": "passed", "cases": []},
        )

    def test_last_complete_raw_object_wins_without_a_fence(self) -> None:
        raw = 'thinking {"draft":true}\nfinal {"ok":true}'
        self.assertEqual(
            model_output.json_object(raw, ValueError("invalid")), {"ok": True}
        )

    def test_missing_object_raises_caller_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid"):
            model_output.json_object("not json", ValueError("invalid"))


if __name__ == "__main__":
    unittest.main()
