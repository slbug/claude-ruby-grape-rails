"""Tests for the trigger contamination hygiene checker."""


import unittest

from lab.eval.triggers.hygiene import (
    check_description_echo,
    check_hard_corpus_quality,
    check_skill_name_leaks,
)




class TestSkillNameLeakDetected(unittest.TestCase):
    """Prompts containing /rb: prefixes should be flagged."""

    def test_rb_prefix_in_should_trigger(self):
        triggers = {
            "should_trigger": [{"prompt": "Help me pick the right /rb: command"}],
            "should_not_trigger": [],
        }
        flags = check_skill_name_leaks("intent-detection", triggers)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["type"], "skill_name_leak")
        self.assertIn("/rb:", flags[0]["reason"])

    def test_command_reference_flagged(self):
        triggers = {
            "should_trigger": [{"prompt": "Use rb:plan to create a plan"}],
            "should_not_trigger": [],
        }
        flags = check_skill_name_leaks("plan", triggers)
        self.assertEqual(len(flags), 1)
        self.assertIn("rb:plan", flags[0]["reason"])

    def test_single_common_word_not_flagged(self):
        triggers = {
            "should_trigger": [{"prompt": "Plan a new Sidekiq retry workflow"}],
            "should_not_trigger": [],
        }
        flags = check_skill_name_leaks("plan", triggers)
        self.assertEqual(len(flags), 0)

    def test_multi_word_skill_name_flagged(self):
        triggers = {
            "should_trigger": [{"prompt": "Help with active-record-patterns in my app"}],
            "should_not_trigger": [],
        }
        flags = check_skill_name_leaks("active-record-patterns", triggers)
        self.assertEqual(len(flags), 1)


class TestNoFalsePositiveOnCommonWords(unittest.TestCase):
    """Skill name in a non-target skill's corpus should not be flagged."""

    def test_plan_in_work_should_not_trigger(self):
        triggers = {
            "should_trigger": [],
            "should_not_trigger": [{"prompt": "Execute the plan tasks"}],
        }
        flags = check_skill_name_leaks("work", triggers)
        self.assertEqual(len(flags), 0)

    def test_other_skill_name_in_positive_bucket(self):
        triggers = {
            "should_trigger": [{"prompt": "Review the plan before starting implementation"}],
            "should_not_trigger": [],
        }
        # "plan" and "review" appear but the target is "deploy" — not flagged
        flags = check_skill_name_leaks("deploy", triggers)
        self.assertEqual(len(flags), 0)


class TestDescriptionEchoDetected(unittest.TestCase):
    """High keyword overlap between description and should_not_trigger should flag."""

    def test_high_overlap_flagged(self):
        description = "Quick small changes for Ruby Rails Grape config tweaks"
        triggers = {
            "should_not_trigger": [
                {"prompt": "Make a quick small change to the Ruby Rails config"},
            ],
        }
        flags = check_description_echo("quick", description, triggers, threshold=0.4)
        self.assertGreater(len(flags), 0)
        self.assertEqual(flags[0]["type"], "description_echo")
        self.assertGreater(flags[0]["overlap_ratio"], 0.4)

    def test_when_to_use_overlap_flagged(self):
        routing_description = {
            "description": "Plan implementation approach",
            "when_to_use": "Triggers: architecture breakdown sequencing risky refactor",
        }
        triggers = {
            "should_not_trigger": [
                {"prompt": "I need architecture breakdown sequencing help"},
            ],
        }
        flags = check_description_echo(
            "plan",
            routing_description,
            triggers,
            threshold=0.4,
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["type"], "description_echo")
        self.assertEqual(flags[0]["source"], "when_to_use")
        self.assertIn("when_to_use", flags[0]["reason"])

    def test_low_overlap_not_flagged(self):
        description = "Quick small changes for Ruby Rails Grape config tweaks"
        triggers = {
            "should_not_trigger": [
                {"prompt": "Deploy the application to production servers"},
            ],
        }
        flags = check_description_echo("quick", description, triggers, threshold=0.5)
        self.assertEqual(len(flags), 0)


class TestCleanTriggersPass(unittest.TestCase):
    """Clean trigger corpus should produce no flags."""

    def test_clean_corpus(self):
        triggers = {
            "should_trigger": [
                {"prompt": "Before coding, map out the safest way to split this billing flow"},
                {"prompt": "I need a multi-file approach for adding a new endpoint and migration"},
            ],
            "should_not_trigger": [
                {"prompt": "Run the project verification stack before I open a PR"},
                {"prompt": "Fix the failing test in the auth module"},
            ],
            "hard_should_trigger": [
                {"prompt": "Sequence the implementation work carefully", "axis": "confusable"},
                {"prompt": "What approach should we take for this risky refactor", "axis": "multi_step"},
            ],
            "hard_should_not_trigger": [
                {"prompt": "Keep working through the current checklist", "axis": "confusable"},
                {"prompt": "Just verify and review the existing patch", "axis": "multi_step"},
            ],
        }
        # Using a skill name that doesn't appear in the prompts
        leaks = check_skill_name_leaks("deploy", triggers)
        echo = check_description_echo(
            "deploy",
            "Deploy Ruby Rails applications with Docker and Fly.io",
            triggers,
        )
        quality = check_hard_corpus_quality(triggers)
        self.assertEqual(len(leaks), 0)
        self.assertEqual(len(echo), 0)
        self.assertEqual(len(quality), 0)


class TestHardCorpusMissing(unittest.TestCase):
    """Missing hard tier should be flagged."""

    def test_missing_hard_should_trigger(self):
        triggers = {
            "should_trigger": [{"prompt": "test"}],
            "should_not_trigger": [{"prompt": "test"}],
            "hard_should_trigger": [],
            "hard_should_not_trigger": [
                {"prompt": "ambiguous prompt", "axis": "confusable"},
                {"prompt": "another one", "axis": "multi_step"},
            ],
        }
        flags = check_hard_corpus_quality(triggers)
        self.assertGreater(len(flags), 0)
        types = [f["type"] for f in flags]
        self.assertIn("hard_corpus_missing", types)

    def test_missing_axis_annotation(self):
        triggers = {
            "hard_should_trigger": [
                {"prompt": "has axis", "axis": "confusable"},
                {"prompt": "missing axis"},
            ],
            "hard_should_not_trigger": [
                {"prompt": "has axis", "axis": "confusable"},
                {"prompt": "also has axis", "axis": "multi_step"},
            ],
        }
        flags = check_hard_corpus_quality(triggers)
        quality_flags = [f for f in flags if f["type"] == "hard_corpus_quality"]
        self.assertEqual(len(quality_flags), 1)
        self.assertIn("missing axis", quality_flags[0]["reason"])


if __name__ == "__main__":
    unittest.main()
