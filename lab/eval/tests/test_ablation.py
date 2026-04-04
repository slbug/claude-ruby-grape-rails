"""Tests for the matcher ablation tooling."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from lab.eval.matcher_ablation import (
    build_ablated_eval,
    enumerate_checks,
    run_ablation,
)
from lab.eval.schemas import EvalCheck, EvalDefinition, EvalDimension


def _make_eval(checks_by_dim: dict[str, list[str]]) -> EvalDefinition:
    """Build a minimal EvalDefinition from {dim_name: [check_type, ...]}."""
    dims = {}
    for dim_name, check_types in checks_by_dim.items():
        checks = [
            EvalCheck(check_type=ct, description=f"desc-{ct}", params={})
            for ct in check_types
        ]
        dims[dim_name] = EvalDimension(name=dim_name, weight=0.5, checks=checks)
    return EvalDefinition(subject="test", subject_path="/fake/SKILL.md", dimensions=dims)


class TestBuildAblatedEval(unittest.TestCase):
    """Verify that build_ablated_eval removes the correct check."""

    def test_removes_single_check(self):
        """Removing one check from a two-check dimension leaves one check."""
        eval_def = _make_eval({"clarity": ["action_density", "no_duplication"]})
        ablated = build_ablated_eval(eval_def, "clarity", 0)
        self.assertIsNotNone(ablated)
        self.assertEqual(len(ablated.dimensions["clarity"].checks), 1)
        self.assertEqual(ablated.dimensions["clarity"].checks[0].check_type, "no_duplication")

    def test_removes_last_check_drops_dimension(self):
        """Removing the only check in a dimension drops the entire dimension."""
        eval_def = _make_eval({"safety": ["no_dangerous_patterns"], "clarity": ["action_density"]})
        ablated = build_ablated_eval(eval_def, "safety", 0)
        self.assertIsNotNone(ablated)
        self.assertNotIn("safety", ablated.dimensions)
        self.assertIn("clarity", ablated.dimensions)

    def test_returns_none_for_invalid_dimension(self):
        """Returns None when dimension name doesn't exist."""
        eval_def = _make_eval({"clarity": ["action_density"]})
        result = build_ablated_eval(eval_def, "nonexistent", 0)
        self.assertIsNone(result)

    def test_returns_none_for_invalid_index(self):
        """Returns None when check index is out of bounds."""
        eval_def = _make_eval({"clarity": ["action_density"]})
        result = build_ablated_eval(eval_def, "clarity", 5)
        self.assertIsNone(result)

    def test_preserves_other_dimensions(self):
        """Other dimensions are unchanged after ablation."""
        eval_def = _make_eval({
            "clarity": ["action_density", "no_duplication"],
            "safety": ["no_dangerous_patterns"],
        })
        ablated = build_ablated_eval(eval_def, "clarity", 0)
        self.assertEqual(
            len(ablated.dimensions["safety"].checks),
            len(eval_def.dimensions["safety"].checks),
        )


class TestEnumerateChecks(unittest.TestCase):
    """Verify dedup of (dimension, check_type) pairs across skills."""

    def test_deduplicates_across_evals(self):
        """Same check type in same dimension from two evals appears once."""
        e1 = _make_eval({"clarity": ["action_density", "no_duplication"]})
        e2 = _make_eval({"clarity": ["action_density"], "safety": ["no_dangerous_patterns"]})
        pairs = enumerate_checks({"s1": e1, "s2": e2})
        self.assertEqual(len(pairs), 3)
        self.assertIn(("clarity", "action_density"), pairs)
        self.assertIn(("clarity", "no_duplication"), pairs)
        self.assertIn(("safety", "no_dangerous_patterns"), pairs)

    def test_empty_input(self):
        """Empty eval dict returns empty list."""
        self.assertEqual(enumerate_checks({}), [])

    def test_sorted_output(self):
        """Results are sorted by (dimension, check_type)."""
        e1 = _make_eval({"z_dim": ["b_check"], "a_dim": ["a_check"]})
        pairs = enumerate_checks({"s1": e1})
        self.assertEqual(pairs[0], ("a_dim", "a_check"))
        self.assertEqual(pairs[1], ("z_dim", "b_check"))


class TestClassification(unittest.TestCase):
    """Verify signal/guardrail/noise classification with mocked scores."""

    @patch("lab.eval.matcher_ablation.score_skill")
    @patch("lab.eval.matcher_ablation.find_all_skills")
    @patch("lab.eval.matcher_ablation._get_eval_def")
    def test_classification(self, mock_get_eval, mock_find_skills, mock_score):
        """Checks are classified correctly based on score deltas and pass rates."""
        skill_path = "/fake/skills/plan/SKILL.md"
        mock_find_skills.return_value = [skill_path]

        # Build eval with three check types to test all three classifications
        eval_def = _make_eval({
            "clarity": ["signal_check", "guardrail_check", "noise_check"],
        })
        mock_get_eval.return_value = eval_def

        # Mock score_skill to return different composites based on the eval
        from lab.eval.schemas import AssertionResult, DimensionResult, SubjectScore

        def fake_score(path, eval_def):
            check_types = {c.check_type for d in eval_def.dimensions.values() for c in d.checks}

            # Baseline: all three checks present -> 0.80
            # Without signal_check -> 0.90 (delta = +0.10, signal)
            # Without guardrail_check -> 0.80 (delta = 0, always passes)
            # Without noise_check -> 0.80 (delta = 0, but fails)

            if "signal_check" not in check_types:
                composite = 0.90
            else:
                composite = 0.80

            # Build assertions for dimension result
            assertions = []
            for _, dim in eval_def.dimensions.items():
                for check in dim.checks:
                    passed = check.check_type != "noise_check"
                    assertions.append(AssertionResult(
                        check_type=check.check_type,
                        description=check.description,
                        passed=passed,
                        evidence="mocked",
                    ))

            dim_result = DimensionResult(
                name="clarity",
                score=composite,
                assertions=assertions,
            )
            return SubjectScore(
                subject_name="plan",
                subject_path=path,
                composite=composite,
                dimensions={"clarity": dim_result},
            )

        mock_score.side_effect = fake_score

        results = run_ablation([skill_path])

        # signal_check should be classified as signal (removal changes composite)
        signal_types = [c["check"] for c in results["signal"]]
        self.assertIn("signal_check", signal_types)

        # guardrail_check always passes and removal doesn't change composite
        guardrail_types = [c["check"] for c in results["guardrails"]]
        self.assertIn("guardrail_check", guardrail_types)

        # noise_check fails but removal doesn't change composite
        noise_types = [c["check"] for c in results["noise"]]
        self.assertIn("noise_check", noise_types)


if __name__ == "__main__":
    unittest.main()
