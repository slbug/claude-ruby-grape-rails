"""Tests for semantic confusable pair parsing, dedup, merge, and cache."""


import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from lab.eval.trigger_scorer import (
    _descriptions_hash,
    _merge_pairs,
)


SAMPLE_DESCRIPTIONS = {
    "plan": "Plan implementation approach for Ruby/Rails features",
    "brainstorm": "Explore ideas interactively before planning",
    "work": "Execute plan tasks with structured progress tracking",
    "review": "Review code changes with parallel specialist agents",
    "investigate": "Structured bug investigation for Rails issues",
}


class TestDescriptionsHash(unittest.TestCase):
    """Tests for cache key hashing."""

    def test_stable(self):
        h1 = _descriptions_hash(SAMPLE_DESCRIPTIONS)
        h2 = _descriptions_hash(SAMPLE_DESCRIPTIONS)
        self.assertEqual(h1, h2)

    def test_changes_with_descriptions(self):
        modified = dict(SAMPLE_DESCRIPTIONS)
        modified["plan"] = "Completely different"
        self.assertNotEqual(
            _descriptions_hash(SAMPLE_DESCRIPTIONS),
            _descriptions_hash(modified),
        )


class TestMergePairs(unittest.TestCase):
    """Tests for token + semantic pair merging."""

    def _merge(self, token, semantic, desc_hash="hash123"):
        """Merge with _SEMANTIC_CACHE_PATH patched to a temp dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_cache = Path(tmpdir) / "_semantic_pairs.json"
            with patch("lab.eval.trigger_scorer._SEMANTIC_CACHE_PATH", tmp_cache):
                return _merge_pairs(token, semantic, desc_hash)

    def test_deduplicates(self):
        token = [{"left": "plan", "right": "work", "overlap": 0.3}]
        semantic = [{"left": "plan", "right": "work", "overlap": 0.7, "source": "semantic", "reason": "both modify code"}]
        merged = self._merge(token, semantic)
        plan_work = [p for p in merged if p["left"] == "plan" and p["right"] == "work"]
        self.assertEqual(len(plan_work), 1)

    def test_normalizes_order(self):
        """Pairs with reversed left/right should still deduplicate."""
        token = [{"left": "plan", "right": "work", "overlap": 0.3}]
        semantic = [{"left": "work", "right": "plan", "overlap": 0.7, "source": "semantic", "reason": ""}]
        merged = self._merge(token, semantic)
        plan_work = [p for p in merged if set([p["left"], p["right"]]) == {"plan", "work"}]
        self.assertEqual(len(plan_work), 1)

    def test_limits_to_15(self):
        token = [
            {"left": f"skill{i}", "right": f"skill{i+1}", "overlap": 0.5 - i * 0.01}
            for i in range(20)
        ]
        merged = self._merge(token, [])
        self.assertLessEqual(len(merged), 15)

    def test_sorted_by_overlap_desc(self):
        token = [
            {"left": "a", "right": "b", "overlap": 0.2},
            {"left": "c", "right": "d", "overlap": 0.8},
        ]
        merged = self._merge(token, [])
        self.assertGreaterEqual(merged[0]["overlap"], merged[-1]["overlap"])

    def test_empty_semantic_no_crash(self):
        token = [{"left": "plan", "right": "work", "overlap": 0.3}]
        merged = self._merge(token, [])
        self.assertEqual(len(merged), 1)

    def test_empty_token_no_crash(self):
        semantic = [{"left": "plan", "right": "brainstorm", "overlap": 0.8, "source": "semantic", "reason": ""}]
        merged = self._merge([], semantic)
        self.assertEqual(len(merged), 1)


class TestSemanticPairParsing(unittest.TestCase):
    """Tests for Haiku response parsing via _fetch_semantic_pairs mock."""

    def _parse_response_lines(self, lines: list[str], descriptions: dict[str, str]) -> list[dict]:
        """Simulate the parsing logic from _fetch_semantic_pairs.

        Must stay in sync with production code in trigger_scorer.py.
        """
        valid_skills = set(descriptions.keys())
        pairs = []
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 2:
                continue
            left, right = parts[0], parts[1]
            if left not in valid_skills or right not in valid_skills:
                continue
            if left == right:
                continue
            score = 0.5
            if len(parts) >= 3:
                raw = parts[2].strip()
                if "/" in raw:
                    raw = raw.split("/", 1)[0].strip()
                try:
                    score = max(1.0, min(10.0, float(raw))) / 10.0
                except ValueError:
                    score = 0.5
            reason = " | ".join(parts[3:]) if len(parts) > 3 else ""
            if left > right:
                left, right = right, left
            pairs.append({"left": left, "right": right, "overlap": round(score, 4),
                          "source": "semantic", "reason": reason})
        return pairs

    def test_valid_4_field_line(self):
        pairs = self._parse_response_lines(
            ["plan | brainstorm | 8 | both explore ideas"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["left"], "brainstorm")  # normalized order
        self.assertEqual(pairs[0]["overlap"], 0.8)
        self.assertEqual(pairs[0]["reason"], "both explore ideas")

    def test_2_field_line_default_score(self):
        pairs = self._parse_response_lines(
            ["plan | brainstorm"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["overlap"], 0.5)

    def test_invalid_skill_rejected(self):
        pairs = self._parse_response_lines(
            ["plan | nonexistent | 7 | reason"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 0)

    def test_self_pair_rejected(self):
        pairs = self._parse_response_lines(
            ["plan | plan | 10 | same skill"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 0)

    def test_malformed_line_skipped(self):
        pairs = self._parse_response_lines(
            ["just some random text", "", "plan | brainstorm | 7 | valid"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 1)

    def test_non_numeric_score_defaults(self):
        pairs = self._parse_response_lines(
            ["plan | brainstorm | high | reason"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["overlap"], 0.5)

    def test_float_score_parsed(self):
        pairs = self._parse_response_lines(
            ["plan | brainstorm | 7.5 | reason"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["overlap"], 0.75)

    def test_fraction_score_parsed(self):
        pairs = self._parse_response_lines(
            ["plan | brainstorm | 8/10 | reason"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["overlap"], 0.8)

    def test_reason_with_pipe_preserved(self):
        pairs = self._parse_response_lines(
            ["plan | brainstorm | 7 | both handle | pre-implementation work"],
            SAMPLE_DESCRIPTIONS,
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["reason"], "both handle | pre-implementation work")


class TestFetchSemanticPairs(unittest.TestCase):
    """Integration tests for _fetch_semantic_pairs with mocked subprocess."""

    def test_valid_response_parsed(self):
        """Mocked Haiku response produces valid semantic pairs."""
        from lab.eval.trigger_scorer import _fetch_semantic_pairs
        mock_response = json.dumps({
            "result": "plan | brainstorm | 8 | both explore ideas\nreview | work | 6 | sequential phases",
        })
        mock_run = MagicMock()
        mock_run.returncode = 0
        mock_run.stdout = mock_response
        with patch("subprocess.run", return_value=mock_run):
            with patch("lab.eval.behavioral_scorer._resolved_settings_path", "fake.json"):
                pairs = _fetch_semantic_pairs(SAMPLE_DESCRIPTIONS, [])
        self.assertEqual(len(pairs), 2)
        names = {(p["left"], p["right"]) for p in pairs}
        self.assertIn(("brainstorm", "plan"), names)

    def test_malformed_lines_skipped(self):
        """Malformed lines in Haiku response are skipped, valid ones kept."""
        from lab.eval.trigger_scorer import _fetch_semantic_pairs
        mock_response = json.dumps({
            "result": "garbage line\n\nplan | brainstorm | 7 | valid\ninvalid | fakeskill | 5 | bad",
        })
        mock_run = MagicMock()
        mock_run.returncode = 0
        mock_run.stdout = mock_response
        with patch("subprocess.run", return_value=mock_run):
            with patch("lab.eval.behavioral_scorer._resolved_settings_path", "fake.json"):
                pairs = _fetch_semantic_pairs(SAMPLE_DESCRIPTIONS, [])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["left"], "brainstorm")

    def test_subprocess_failure_returns_empty(self):
        """Failed subprocess returns empty list, not crash."""
        from lab.eval.trigger_scorer import _fetch_semantic_pairs
        mock_run = MagicMock()
        mock_run.returncode = 1
        mock_run.stdout = ""
        with patch("subprocess.run", return_value=mock_run):
            with patch("lab.eval.behavioral_scorer._resolved_settings_path", "fake.json"):
                pairs = _fetch_semantic_pairs(SAMPLE_DESCRIPTIONS, [])
        self.assertEqual(pairs, [])

    def test_timeout_returns_empty(self):
        """Subprocess timeout returns empty list."""
        import subprocess as sp
        from lab.eval.trigger_scorer import _fetch_semantic_pairs
        with patch("subprocess.run", side_effect=sp.TimeoutExpired("claude", 60)):
            with patch("lab.eval.behavioral_scorer._resolved_settings_path", "fake.json"):
                pairs = _fetch_semantic_pairs(SAMPLE_DESCRIPTIONS, [])
        self.assertEqual(pairs, [])


class TestBuildSemanticConfusablePairs(unittest.TestCase):
    """Integration test for the full build_semantic_confusable_pairs path."""

    def test_cache_hit_skips_fetch(self):
        """When cache is valid, no subprocess call is made."""
        from lab.eval.trigger_scorer import build_semantic_confusable_pairs
        desc_hash = _descriptions_hash(SAMPLE_DESCRIPTIONS)
        cached = {
            "descriptions_hash": desc_hash,
            "semantic_pairs": [{"left": "plan", "right": "brainstorm", "overlap": 0.8, "source": "semantic", "reason": ""}],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "_semantic_pairs.json"
            cache_path.write_text(json.dumps(cached))
            with patch("lab.eval.trigger_scorer._SEMANTIC_CACHE_PATH", cache_path):
                with patch("subprocess.run") as mock_run:
                    pairs = build_semantic_confusable_pairs(SAMPLE_DESCRIPTIONS, [])
                    mock_run.assert_not_called()
        # Should have the cached semantic pair merged with token pairs
        self.assertTrue(any(p.get("source") == "semantic" for p in pairs))

    def test_cache_miss_triggers_fetch(self):
        """When cache hash doesn't match, subprocess is called."""
        from lab.eval.trigger_scorer import build_semantic_confusable_pairs
        stale_cache = {
            "descriptions_hash": "stale_hash",
            "semantic_pairs": [],
        }
        mock_response = json.dumps({
            "result": "plan | brainstorm | 9 | both pre-implementation",
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = mock_response
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "_semantic_pairs.json"
            cache_path.write_text(json.dumps(stale_cache))
            with patch("lab.eval.trigger_scorer._SEMANTIC_CACHE_PATH", cache_path):
                with patch("subprocess.run", return_value=mock_result) as mock_run:
                    with patch("lab.eval.behavioral_scorer._resolved_settings_path", "fake.json"):
                        pairs = build_semantic_confusable_pairs(SAMPLE_DESCRIPTIONS, [])
                        self.assertTrue(mock_run.called)
        self.assertTrue(any(p.get("source") == "semantic" for p in pairs))


class TestSemanticPairCache(unittest.TestCase):
    """Tests for cache hit/miss behavior."""

    def test_cache_not_clobbered_on_empty_semantic(self):
        """Empty semantic pairs don't overwrite existing cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "_semantic_pairs.json"
            # Write a valid cache
            existing = {
                "descriptions_hash": _descriptions_hash(SAMPLE_DESCRIPTIONS),
                "semantic_pairs": [{"left": "plan", "right": "brainstorm", "overlap": 0.8, "source": "semantic", "reason": ""}],
            }
            cache_path.write_text(json.dumps(existing))

            # _merge_pairs with empty semantic should not clobber
            with patch("lab.eval.trigger_scorer._SEMANTIC_CACHE_PATH", cache_path):
                _merge_pairs([], [], _descriptions_hash(SAMPLE_DESCRIPTIONS))

            # Cache should still have the original data
            cached = json.loads(cache_path.read_text())
            self.assertEqual(len(cached["semantic_pairs"]), 1)


if __name__ == "__main__":
    unittest.main()
