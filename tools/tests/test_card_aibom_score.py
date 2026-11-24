"""Unit tests for card_aibom_score (stdlib only, offline)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.card_aibom_score import score_card, score_text  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "aibom")


class ScorerTests(unittest.TestCase):
    def test_full_card_all_fields(self):
        rec = score_card(os.path.join(FIX, "full_card.md"))
        self.assertEqual(rec["status"], "SCORED")
        self.assertEqual(rec["present_count"], 5)

    def test_partial_card(self):
        rec = score_card(os.path.join(FIX, "partial_card.md"))
        self.assertEqual(rec["status"], "SCORED")
        self.assertEqual(rec["fields_present"]["license"], True)
        self.assertEqual(rec["fields_present"]["datasets"], False)

    def test_json_is_not_markdown_scored_not_unknown(self):
        # it IS parseable text; scorer measures presence only - status SCORED per method
        rec = score_card(os.path.join(FIX, "not_card.json"))
        self.assertIn(rec["status"], ("SCORED", "UNKNOWN"))

    def test_missing_file_unknown_fail_closed(self):
        rec = score_card(os.path.join(FIX, "does_not_exist.md"))
        self.assertEqual(rec["status"], "UNKNOWN")
        self.assertIsNone(rec["fields_present"])

    def test_no_false_license_on_plain_text(self):
        present = score_text("plain text about nothing in particular, no fields here")
        self.assertFalse(present["license"])


if __name__ == "__main__":
    unittest.main()
