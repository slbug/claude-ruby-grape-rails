"""Tests for trigger expansion quality gates."""

from __future__ import annotations

import unittest

from lab.eval.trigger_expand import _quality_gate, _token_overlap


class TestTokenOverlap(unittest.TestCase):
    """Tests for Jaccard token overlap."""

    def test_identical_strings(self):
        self.assertAlmostEqual(_token_overlap("plan a feature", "plan a feature"), 1.0)

    def test_no_overlap(self):
        self.assertAlmostEqual(_token_overlap("plan a feature", "debug redis cache"), 0.0)

    def test_partial_overlap(self):
        score = _token_overlap("plan a new feature", "plan the feature set")
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_empty_string(self):
        self.assertAlmostEqual(_token_overlap("", "anything"), 0.0)
        self.assertAlmostEqual(_token_overlap("", ""), 0.0)


class TestQualityGate(unittest.TestCase):
    """Tests for candidate prompt quality gates."""

    def test_too_short(self):
        self.assertEqual(
            _quality_gate("hi", "plan", [], "Plan implementation"),
            "too_short",
        )

    def test_too_long(self):
        long = "x " * 300
        self.assertEqual(
            _quality_gate(long, "plan", [], "Plan implementation"),
            "too_long",
        )

    def test_skill_name_leak_rb_prefix(self):
        """Detects /rb: prefix as leak."""
        self.assertEqual(
            _quality_gate("Can you run /rb:plan for me?", "plan", [], "Plan implementation"),
            "skill_name_leak",
        )

    def test_skill_name_leak_command_ref(self):
        """Detects rb:skillname command reference as leak."""
        self.assertEqual(
            _quality_gate("Use rb:plan to create a plan", "plan", [], "Plan implementation"),
            "skill_name_leak",
        )

    def test_skill_name_leak_hyphenated(self):
        """Detects multi-word skill names as whole-word leak."""
        self.assertEqual(
            _quality_gate(
                "Use active-record-patterns for this",
                "active-record-patterns", [], "AR patterns",
            ),
            "skill_name_leak",
        )

    def test_single_word_skill_not_leak(self):
        """Single common words (plan, review) appearing naturally are NOT leaks."""
        self.assertIsNone(
            _quality_gate(
                "I need to plan a new authentication feature",
                "plan", [], "Plan implementation approach",
            ),
        )

    def test_description_echo(self):
        desc = "Plan implementation approach for Ruby Rails features"
        # Prompt that is >50% token overlap with description
        self.assertEqual(
            _quality_gate(
                "Plan implementation approach for Ruby Rails features and more",
                "some-skill", [], desc,
            ),
            "description_echo",
        )

    def test_near_duplicate(self):
        existing = ["I want to plan a new authentication feature for my Rails app"]
        self.assertEqual(
            _quality_gate(
                "I want to plan a new authentication feature for my Rails app please",
                "some-skill", existing, "Some description",
            ),
            "near_duplicate",
        )

    def test_passes_all_gates(self):
        self.assertIsNone(
            _quality_gate(
                "How should I structure the database migration for user roles?",
                "plan",
                ["Design a new API endpoint"],
                "Plan implementation approach",
            )
        )

    def test_case_insensitive_rb_prefix_leak(self):
        """Case-insensitive /rb: detection."""
        self.assertEqual(
            _quality_gate("Try /RB:plan for this task", "plan", [], "desc"),
            "skill_name_leak",
        )


if __name__ == "__main__":
    unittest.main()
