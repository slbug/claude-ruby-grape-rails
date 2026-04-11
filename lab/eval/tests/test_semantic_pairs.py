"""Tests for semantic confusable pair parsing, dedup, merge, and cache."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        """Simulate the parsing logic from _fetch_semantic_pairs."""
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
            try:
                score = int(parts[2]) / 10.0 if len(parts) >= 3 else 0.5
            except ValueError:
                score = 0.5
            reason = parts[3] if len(parts) > 3 else ""
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
