"""Tests for the behavioral eval dimension and scorer."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lab.eval.behavioral_scorer import (
    _ROUTING_SYSTEM_PROMPT,
    _check_correct,
    _extract_prompt_meta,
    build_routing_prompt,
    CallResult,
    content_hash,
    score_skill,
)
from lab.eval.dimensions.behavioral import score as behavioral_score


SAMPLE_DESCRIPTIONS = {
    "plan": "Plan implementation approach for Ruby/Rails features",
    "work": "Execute plan tasks with structured progress tracking",
    "review": "Review code changes with parallel specialist agents",
}


def _cr(skills: list[str] | None) -> CallResult:
    """Shorthand to build a CallResult for mocking run_haiku."""
    return CallResult(skills=skills)


def _unpack(score_result) -> dict:
    """Unpack score_skill (dict, call_results) tuple, return just the dict."""
    return score_result[0]


class TestContentHash(unittest.TestCase):
    """Tests for cache invalidation hashing."""

    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_hash_stability(self, mock_trigger):
        """Same inputs produce the same hash."""
        mock_trigger.return_value = {"should_trigger": ["plan a feature"]}
        h1 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        h2 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        self.assertEqual(h1, h2)

    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_hash_changes_with_description(self, mock_trigger):
        """Different descriptions produce different hashes."""
        mock_trigger.return_value = {"should_trigger": ["plan a feature"]}
        h1 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        modified = dict(SAMPLE_DESCRIPTIONS)
        modified["plan"] = "Completely different description"
        h2 = content_hash("plan", modified)
        self.assertNotEqual(h1, h2)

    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_hash_changes_with_triggers(self, mock_trigger):
        """Different trigger corpora produce different hashes."""
        mock_trigger.return_value = {"should_trigger": ["plan a feature"]}
        h1 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        mock_trigger.return_value = {"should_trigger": ["design architecture"]}
        h2 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        self.assertNotEqual(h1, h2)


class TestRoutingPrompt(unittest.TestCase):
    """Tests for the routing prompt builder."""

    def test_includes_all_descriptions(self):
        """Prompt contains all skill names and descriptions."""
        prompt = build_routing_prompt(SAMPLE_DESCRIPTIONS, "plan a feature")
        for name, desc in SAMPLE_DESCRIPTIONS.items():
            self.assertIn(name, prompt)
            self.assertIn(desc[:50], prompt)

    def test_includes_user_prompt(self):
        """Prompt contains the user's input."""
        user_input = "I need to plan a new authentication feature"
        prompt = build_routing_prompt(SAMPLE_DESCRIPTIONS, user_input)
        self.assertIn(user_input, prompt)

    def test_response_format_instructions(self):
        """System prompt asks for skill names only."""
        self.assertIn("ONLY", _ROUTING_SYSTEM_PROMPT)
        self.assertIn("skill name", _ROUTING_SYSTEM_PROMPT.lower())


class TestBehavioralDimension(unittest.TestCase):
    """Tests for the dimension scorer that reads cached results."""

    def test_neutral_without_cache(self):
        """Returns 1.0 when no cache exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path=f"{tmpdir}/nonexistent/SKILL.md",
                )
                self.assertEqual(result.score, 1.0)
                self.assertEqual(result.name, "behavioral")
                self.assertTrue(all(a.passed for a in result.assertions))

    def test_score_from_cached_passing(self):
        """Returns passing score from cached results above thresholds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_data = {
                "skill": "plan",
                "accuracy": 0.875,
                "precision": 0.857,
                "recall": 0.75,
                "total": 8,
                "correct": 7,
                "tp": 6, "fp": 1, "fn": 2,
            }
            cache_path = Path(tmpdir) / "plan.json"
            cache_path.write_text(json.dumps(cache_data))

            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path="/fake/skills/plan/SKILL.md",
                )
                self.assertGreater(result.score, 0.0)
                self.assertEqual(result.name, "behavioral")
                self.assertTrue(all(a.passed for a in result.assertions))

    def test_score_from_cached_failing(self):
        """Returns failing score from cached results below thresholds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_data = {
                "skill": "plan",
                "accuracy": 0.50,
                "precision": 0.50,
                "recall": 0.40,
                "total": 8,
                "correct": 4,
                "tp": 2, "fp": 2, "fn": 3,
            }
            cache_path = Path(tmpdir) / "plan.json"
            cache_path.write_text(json.dumps(cache_data))

            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path="/fake/skills/plan/SKILL.md",
                )
                self.assertLess(result.score, 1.0)
                self.assertFalse(all(a.passed for a in result.assertions))

    def test_error_in_cache_returns_neutral(self):
        """Returns neutral score when cache contains an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_data = {"skill": "plan", "error": "no trigger file"}
            cache_path = Path(tmpdir) / "plan.json"
            cache_path.write_text(json.dumps(cache_data))

            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path="/fake/skills/plan/SKILL.md",
                )
                self.assertEqual(result.score, 1.0)


class TestScoreSkill(unittest.TestCase):
    """Tests for the behavioral scorer's score_skill function."""

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_score_skill_with_mock_haiku(self, mock_triggers, mock_haiku):
        """Scores correctly with mocked haiku responses."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature", "design an implementation"],
            "should_not_trigger": ["review my code", "fix this bug"],
        }
        mock_haiku.side_effect = [
            _cr(["plan"]),    # should_trigger: correct
            _cr(["plan"]),    # should_trigger: correct
            _cr(["review"]),  # should_not_trigger: correct (plan not in list)
            _cr(["work"]),    # should_not_trigger: correct (plan not in list)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS))

        self.assertEqual(result["accuracy"], 1.0)
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["correct"], 4)


class TestDifficultyTiers(unittest.TestCase):
    """Tests for P1a difficulty-stratified reporting."""

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_hard_tier_included_in_results(self, mock_triggers, mock_haiku):
        """Hard-tier prompts are scored and reported separately."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature"],
            "should_not_trigger": ["fix this bug"],
            "hard_should_trigger": [{"prompt": "ambiguous planning request", "axis": "confusable"}],
            "hard_should_not_trigger": [{"prompt": "keep working on checklist", "axis": "confusable"}],
        }
        mock_haiku.side_effect = [
            _cr(["plan"]),  # easy should_trigger: correct
            _cr(["work"]),  # easy should_not: correct
            _cr(["plan"]),  # hard should_trigger: correct
            _cr(["work"]),  # hard should_not: correct
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS))

        self.assertEqual(result["tier_counts"]["easy"], 2)
        self.assertEqual(result["tier_counts"]["hard"], 2)
        self.assertEqual(result["easy_accuracy"], 1.0)
        self.assertEqual(result["hard_accuracy"], 1.0)
        self.assertEqual(result["total"], 4)

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_hard_tier_failure_reported(self, mock_triggers, mock_haiku):
        """Hard-tier misses show up in hard_accuracy."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature"],
            "should_not_trigger": ["fix this bug"],
            "hard_should_trigger": [{"prompt": "ambiguous request", "axis": "confusable"}],
            "hard_should_not_trigger": [{"prompt": "keep working", "axis": "confusable"}],
        }
        mock_haiku.side_effect = [
            _cr(["plan"]),       # easy should_trigger: correct
            _cr(["work"]),       # easy should_not: correct
            _cr(["brainstorm"]), # hard should_trigger: MISS
            _cr(["plan"]),       # hard should_not: MISS (plan in list)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS))

        self.assertEqual(result["easy_accuracy"], 1.0)
        self.assertEqual(result["hard_accuracy"], 0.0)

    def test_dimension_hard_tier_advisory(self):
        """Hard-tier assertion doesn't affect dim_score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_data = {
                "skill": "plan",
                "accuracy": 0.875,
                "precision": 0.857,
                "recall": 0.75,
                "total": 8,
                "correct": 7,
                "tp": 6, "fp": 1, "fn": 2,
                "easy_accuracy": 1.0,
                "easy_precision": 1.0,
                "easy_recall": 1.0,
                "hard_accuracy": 0.25,
                "hard_precision": 0.5,
                "hard_recall": 0.25,
                "tier_counts": {"easy": 4, "hard": 4},
            }
            cache_path = Path(tmpdir) / "plan.json"
            cache_path.write_text(json.dumps(cache_data))

            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path="/fake/skills/plan/SKILL.md",
                )
                # hard_tier is advisory — should not lower dim_score when other checks pass
                scored_assertions = [a for a in result.assertions if "advisory" not in a.description]
                advisory_assertions = [a for a in result.assertions if "advisory" in a.description]
                self.assertTrue(len(advisory_assertions) > 0)
                # dim_score based only on non-advisory
                expected_score = sum(1 for a in scored_assertions if a.passed) / len(scored_assertions)
                self.assertAlmostEqual(result.score, expected_score)


class TestForkLockRouting(unittest.TestCase):
    """Tests for P2 fork/lock correctness logic."""

    def test_extract_prompt_meta_string(self):
        """Plain string prompt has no routing annotation."""
        meta = _extract_prompt_meta("plan a feature")
        self.assertEqual(meta["prompt"], "plan a feature")
        self.assertIsNone(meta["routing"])
        self.assertEqual(meta["valid_skills"], [])

    def test_extract_prompt_meta_lock(self):
        """Dict with routing=lock."""
        meta = _extract_prompt_meta({"prompt": "debug this", "routing": "lock", "axis": "confusable"})
        self.assertEqual(meta["routing"], "lock")

    def test_extract_prompt_meta_fork(self):
        """Dict with routing=fork and valid_skills."""
        meta = _extract_prompt_meta({
            "prompt": "think through this",
            "routing": "fork",
            "valid_skills": ["plan", "brainstorm"],
        })
        self.assertEqual(meta["routing"], "fork")
        self.assertEqual(meta["valid_skills"], ["plan", "brainstorm"])

    def test_check_correct_lock_hit(self):
        """Lock routing: correct when expected skill in chosen."""
        self.assertTrue(_check_correct("plan", ["plan"], True, "lock", []))

    def test_check_correct_lock_miss(self):
        """Lock routing: incorrect when expected skill not in chosen."""
        self.assertFalse(_check_correct("plan", ["brainstorm"], True, "lock", []))

    def test_check_correct_fork_any_valid(self):
        """Fork routing: correct when any valid_skills in chosen."""
        self.assertTrue(_check_correct("plan", ["brainstorm"], True, "fork", ["plan", "brainstorm"]))

    def test_check_correct_fork_miss(self):
        """Fork routing: incorrect when no valid_skills in chosen."""
        self.assertFalse(_check_correct("plan", ["investigate"], True, "fork", ["plan", "brainstorm"]))

    def test_check_correct_should_not_trigger(self):
        """Should-not-trigger: correct when skill NOT in chosen, regardless of routing."""
        self.assertTrue(_check_correct("plan", ["work"], False, "lock", []))
        self.assertFalse(_check_correct("plan", ["plan"], False, "fork", ["plan"]))

    def test_check_correct_unannotated(self):
        """Unannotated (routing=None): falls through to exact match."""
        self.assertTrue(_check_correct("plan", ["plan"], True, None, []))
        self.assertFalse(_check_correct("plan", ["brainstorm"], True, None, []))

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_fork_prompt_scores_correct(self, mock_triggers, mock_haiku):
        """Fork prompt counts as correct when returned skill is in valid_skills."""
        mock_triggers.return_value = {
            "should_trigger": [],
            "should_not_trigger": [],
            "hard_should_trigger": [{
                "prompt": "think through billing approach",
                "axis": "confusable",
                "routing": "fork",
                "valid_skills": ["plan", "brainstorm"],
            }],
            "hard_should_not_trigger": [],
        }
        mock_haiku.return_value = _cr(["brainstorm"])  # not "plan" but in valid_skills

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS))

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["fork_accuracy"], 1.0)


class TestParallelWorkers(unittest.TestCase):
    """Tests for P5b parallel workers."""

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_workers_preserves_results(self, mock_triggers, mock_haiku):
        """--workers > 1 produces same results as sequential."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature", "design an approach"],
            "should_not_trigger": ["fix this bug", "review code"],
            "hard_should_trigger": [],
            "hard_should_not_trigger": [],
        }
        # Use a function so thread execution order doesn't matter
        mock_haiku.side_effect = lambda *a, **kw: _cr(["plan"])

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                seq_result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS, workers=1))

        mock_haiku.side_effect = lambda *a, **kw: _cr(["plan"])

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                par_result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS, workers=2))

        self.assertEqual(seq_result["accuracy"], par_result["accuracy"])
        self.assertEqual(seq_result["total"], par_result["total"])
        self.assertEqual(seq_result["correct"], par_result["correct"])

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_workers_all_prompts_processed(self, mock_triggers, mock_haiku):
        """All prompts are processed with parallel workers."""
        mock_triggers.return_value = {
            "should_trigger": ["p1", "p2", "p3", "p4"],
            "should_not_trigger": ["n1", "n2", "n3", "n4"],
            "hard_should_trigger": [],
            "hard_should_not_trigger": [],
        }
        mock_haiku.return_value = _cr(["plan"])

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS, workers=4))

        self.assertEqual(result["total"], 8)


class TestCyclicRotation(unittest.TestCase):
    """Tests for P1b cyclic rotation and majority vote."""

    def test_build_routing_prompt_rotation_zero(self):
        """Rotation 0 produces same order as default."""
        p0 = build_routing_prompt(SAMPLE_DESCRIPTIONS, "test")
        pr = build_routing_prompt(SAMPLE_DESCRIPTIONS, "test", rotation=0)
        self.assertEqual(p0, pr)

    def test_build_routing_prompt_rotation_shifts(self):
        """Non-zero rotation shifts the skill list."""
        p0 = build_routing_prompt(SAMPLE_DESCRIPTIONS, "test", rotation=0)
        p1 = build_routing_prompt(SAMPLE_DESCRIPTIONS, "test", rotation=1)
        self.assertNotEqual(p0, p1)
        # Both should contain all skill names
        for name in SAMPLE_DESCRIPTIONS:
            self.assertIn(name, p0)
            self.assertIn(name, p1)

    def test_build_routing_prompt_rotation_wraps(self):
        """Rotation wraps around: rotation=len produces same as rotation=0."""
        n = len(SAMPLE_DESCRIPTIONS)
        p0 = build_routing_prompt(SAMPLE_DESCRIPTIONS, "test", rotation=0)
        pw = build_routing_prompt(SAMPLE_DESCRIPTIONS, "test", rotation=n)
        self.assertEqual(p0, pw)

    def test_majority_vote_odd(self):
        """Majority vote with odd N."""
        from lab.eval.behavioral_scorer import _majority_vote
        self.assertTrue(_majority_vote([True, True, False]))
        self.assertFalse(_majority_vote([True, False, False]))
        self.assertTrue(_majority_vote([True, True, True, True, False]))

    def test_majority_vote_even_tie_fails(self):
        """Even N tie resolves to False (conservative)."""
        from lab.eval.behavioral_scorer import _majority_vote
        self.assertFalse(_majority_vote([True, False]))
        self.assertFalse(_majority_vote([True, True, False, False]))

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_rotations_expand_work_items(self, mock_triggers, mock_haiku):
        """--rotations 3 triples the number of haiku calls."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature"],
            "should_not_trigger": ["fix a bug"],
        }
        mock_haiku.side_effect = lambda *a, **kw: _cr(["plan"])

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS, rotations=3))

        # 2 base prompts, each run 3 times = 6 haiku calls
        self.assertEqual(mock_haiku.call_count, 6)
        # But aggregated to 2 results
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["rotations"], 3)
        self.assertIn("per_rotation_accuracy", result)
        self.assertIn("order_range", result)
        self.assertIn("routing_consistency", result)

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_rotations_majority_vote(self, mock_triggers, mock_haiku):
        """Majority vote across rotations determines correctness."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature"],
            "should_not_trigger": [],
        }
        # Rotation 0: correct, Rotation 1: miss, Rotation 2: correct → majority correct
        call_count = [0]
        def _side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 2:  # 2nd call misses
                return _cr(["brainstorm"])
            return _cr(["plan"])
        mock_haiku.side_effect = _side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS, rotations=3))

        self.assertEqual(result["accuracy"], 1.0)  # majority says correct


class TestPassAtK(unittest.TestCase):
    """Tests for P3 pass@k routing robustness."""

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_samples_expand_work_items(self, mock_triggers, mock_haiku):
        """--samples 3 triples the number of haiku calls."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature"],
            "should_not_trigger": ["fix a bug"],
        }
        mock_haiku.side_effect = lambda *a, **kw: _cr(["plan"])

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS, samples=3))

        self.assertEqual(mock_haiku.call_count, 6)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["samples"], 3)
        self.assertIn("pass_at_k", result)
        self.assertIn("sample_consistency", result)

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_pass_at_k_recovers_inconsistent(self, mock_triggers, mock_haiku):
        """pass@k is 1.0 when at least one sample is correct."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature"],
            "should_not_trigger": [],
        }
        # Sample 0: miss, Sample 1: correct, Sample 2: miss
        call_count = [0]
        def _side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 2:  # 2nd sample correct
                return _cr(["plan"])
            return _cr(["brainstorm"])
        mock_haiku.side_effect = _side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS, samples=3))

        # accuracy from sample 0 = 0% (miss), but pass@3 = 100% (one hit)
        self.assertEqual(result["accuracy"], 0.0)
        self.assertEqual(result["pass_at_k"], 1.0)
        self.assertEqual(result["sample_consistency"], 0.0)  # not all agree
        self.assertTrue(result["inconsistent_routing"])

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_sample_consistency_all_agree(self, mock_triggers, mock_haiku):
        """sample_consistency is 1.0 when all samples agree."""
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature"],
            "should_not_trigger": [],
        }
        mock_haiku.side_effect = lambda *a, **kw: _cr(["plan"])

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = _unpack(score_skill("plan", SAMPLE_DESCRIPTIONS, samples=3))

        self.assertEqual(result["sample_consistency"], 1.0)
        self.assertFalse(result["inconsistent_routing"])


class TestMutualExclusion(unittest.TestCase):
    """Tests for --rotations / --samples mutual exclusion."""

    def test_rotations_and_samples_both_gt_1_errors(self):
        """Cannot use both --rotations > 1 and --samples > 1."""
        from lab.eval.behavioral_scorer import main
        with patch("sys.argv", ["scorer", "--skill", "plan", "--rotations", "3", "--samples", "3"]):
            with self.assertRaises(SystemExit) as ctx:
                main()
            self.assertEqual(ctx.exception.code, 2)  # argparse error exit code


if __name__ == "__main__":
    unittest.main()
