"""Tests for eval-set sensitivity analysis."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lab.eval.eval_sensitivity import analyze_skill, classify_prompt_impact


class TestClassifyPromptImpact(unittest.TestCase):
    """Tests for the 4-tier impact classification."""

    def test_high_leverage(self):
        """Removal drops accuracy by more than 5%."""
        self.assertEqual(classify_prompt_impact(-0.06), "high-leverage")
        self.assertEqual(classify_prompt_impact(-0.15), "high-leverage")

    def test_drag(self):
        """Removal improves accuracy by more than 5%."""
        self.assertEqual(classify_prompt_impact(0.06), "drag")
        self.assertEqual(classify_prompt_impact(0.20), "drag")

    def test_redundant(self):
        """Removal has negligible effect."""
        self.assertEqual(classify_prompt_impact(0.0), "redundant")
        self.assertEqual(classify_prompt_impact(0.005), "redundant")
        self.assertEqual(classify_prompt_impact(-0.005), "redundant")

    def test_contributing(self):
        """Modest healthy impact between thresholds."""
        self.assertEqual(classify_prompt_impact(0.03), "contributing")
        self.assertEqual(classify_prompt_impact(-0.03), "contributing")

    def test_boundary_values(self):
        """Exact threshold values."""
        self.assertEqual(classify_prompt_impact(-0.05), "contributing")
        self.assertEqual(classify_prompt_impact(0.05), "contributing")
        self.assertEqual(classify_prompt_impact(0.01), "contributing")
        self.assertEqual(classify_prompt_impact(-0.01), "contributing")


class TestAnalyzeSkill(unittest.TestCase):
    """Tests for leave-one-out analysis."""

    def _write_cache(self, tmpdir: str, skill: str, results: list[dict]) -> None:
        path = Path(tmpdir) / f"{skill}.json"
        path.write_text(json.dumps({"results": results}))

    def test_missing_cache_returns_none(self):
        """No cache file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.results_dir.active_results_dir", return_value=Path(tmpdir)):
                self.assertIsNone(analyze_skill("nonexistent"))

    def test_corrupted_cache_returns_error(self):
        """Invalid JSON returns structured error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "plan.json"
            path.write_text("not json{{{")
            with patch("lab.eval.results_dir.active_results_dir", return_value=Path(tmpdir)):
                result = analyze_skill("plan")
                if result is None:
                    self.fail("analyze_skill returned None")
                self.assertIn("error", result)
                self.assertIn("invalid cached results JSON", result["error"])

    def test_too_few_results(self):
        """Fewer than 3 results returns error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_cache(tmpdir, "plan", [
                {"prompt": "a", "correct": True},
                {"prompt": "b", "correct": True},
            ])
            with patch("lab.eval.results_dir.active_results_dir", return_value=Path(tmpdir)):
                result = analyze_skill("plan")
                if result is None:
                    self.fail("analyze_skill returned None")
                self.assertIn("error", result)
                self.assertIn("too few", result["error"])

    def test_all_correct_low_fragility(self):
        """All-correct results have low fragility."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_cache(tmpdir, "plan", [
                {"prompt": f"p{i}", "correct": True} for i in range(6)
            ])
            with patch("lab.eval.results_dir.active_results_dir", return_value=Path(tmpdir)):
                result = analyze_skill("plan")
                if result is None:
                    self.fail("analyze_skill returned None")
                self.assertEqual(result["baseline_accuracy"], 1.0)
                self.assertEqual(result["fragility_max"], 0.0)
                self.assertEqual(result["high_leverage_count"], 0)
                self.assertEqual(result["drag_count"], 0)

    def test_single_failure_creates_drag(self):
        """One failing prompt in a small set is a drag candidate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = [{"prompt": f"p{i}", "correct": True} for i in range(4)]
            results.append({"prompt": "bad", "correct": False})
            self._write_cache(tmpdir, "plan", results)
            with patch("lab.eval.results_dir.active_results_dir", return_value=Path(tmpdir)):
                result = analyze_skill("plan")
                if result is None:
                    self.fail("analyze_skill returned None")
                # Removing the failing prompt improves accuracy
                self.assertGreater(result["drag_count"], 0)

    def test_single_success_creates_high_leverage(self):
        """One passing prompt among failures is high-leverage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results = [{"prompt": f"p{i}", "correct": False} for i in range(4)]
            results.append({"prompt": "good", "correct": True})
            self._write_cache(tmpdir, "plan", results)
            with patch("lab.eval.results_dir.active_results_dir", return_value=Path(tmpdir)):
                result = analyze_skill("plan")
                if result is None:
                    self.fail("analyze_skill returned None")
                # Removing the passing prompt drops accuracy
                self.assertGreater(result["high_leverage_count"], 0)

    def test_prompt_impacts_length(self):
        """One impact entry per result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_cache(tmpdir, "plan", [
                {"prompt": f"p{i}", "correct": i % 2 == 0} for i in range(6)
            ])
            with patch("lab.eval.results_dir.active_results_dir", return_value=Path(tmpdir)):
                result = analyze_skill("plan")
                if result is None:
                    self.fail("analyze_skill returned None")
                self.assertEqual(len(result["prompt_impacts"]), 6)
                self.assertEqual(result["total_prompts"], 6)


if __name__ == "__main__":
    unittest.main()
