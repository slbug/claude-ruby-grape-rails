from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab.eval.agent_scorer import find_all_agents, score_agent
from lab.eval.compare import compare_snapshots
from lab.eval.scorer import find_all_skills, score_skill
from lab.eval.schemas import EvalDefinition
from lab.eval.trigger_scorer import build_confusable_pairs, load_all_descriptions, score_all


class ScorerTests(unittest.TestCase):
    def test_plan_skill_scores(self) -> None:
        plan_path = next(path for path in find_all_skills() if path.endswith("/plan/SKILL.md"))
        result = score_skill(plan_path)
        self.assertGreater(result.composite, 0.5)

    def test_verification_runner_agent_scores(self) -> None:
        agent_path = next(path for path in find_all_agents() if path.endswith("/verification-runner.md"))
        result = score_agent(agent_path)
        self.assertGreater(result.composite, 0.5)

    def test_trigger_scoring_and_overlap(self) -> None:
        trigger_results = score_all()
        self.assertIn("plan", trigger_results["skills"])
        pairs = build_confusable_pairs(load_all_descriptions(), limit=5)
        self.assertLessEqual(len(pairs), 5)

    def test_build_confusable_pairs_reuses_loaded_trigger_data(self) -> None:
        descriptions = {"plan": "Plan work", "verify": "Verify changes"}
        trigger_payloads = {
            "plan": {"should_trigger": ["plan a migration"], "hard_should_trigger": []},
            "verify": {"should_trigger": ["verify a fix"], "hard_should_trigger": []},
        }
        calls: list[str] = []

        def fake_load_trigger_file(skill: str) -> dict[str, object] | None:
            calls.append(skill)
            return trigger_payloads.get(skill)

        with patch("lab.eval.trigger_scorer.load_trigger_file", side_effect=fake_load_trigger_file):
            pairs = build_confusable_pairs(descriptions, limit=5)

        self.assertEqual(calls, ["plan", "verify"])
        self.assertEqual(pairs, [])

    def test_score_skill_reports_unknown_check_types_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "SKILL.md"
            skill_path.write_text("---\nname: rb:test\ndescription: test\n---\n# Test\n", encoding="utf-8")
            eval_def = EvalDefinition.from_dict(
                {
                    "skill": "test",
                    "skill_path": str(skill_path),
                    "dimensions": {
                        "safety": {
                            "weight": 1.0,
                            "checks": [
                                {
                                    "type": "not_a_real_check",
                                    "desc": "invalid check type",
                                }
                            ],
                        }
                    },
                }
            )

            with self.assertRaises(ValueError) as ctx:
                score_skill(str(skill_path), eval_def)

        self.assertIn("Unknown check type", str(ctx.exception))
        self.assertIn("not_a_real_check", str(ctx.exception))

    def test_score_agent_reports_unknown_check_types_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_path = Path(tmpdir) / "sample-agent.md"
            agent_path.write_text(
                "---\nname: sample-agent\ndescription: test agent\ntools: Read\neffort: medium\n---\n# Agent\n",
                encoding="utf-8",
            )
            eval_def = EvalDefinition.from_dict(
                {
                    "agent": "sample-agent",
                    "agent_path": str(agent_path),
                    "dimensions": {
                        "safety": {
                            "weight": 1.0,
                            "checks": [
                                {
                                    "type": "not_a_real_check",
                                    "desc": "invalid check type",
                                }
                            ],
                        }
                    },
                }
            )

            with self.assertRaises(ValueError) as ctx:
                score_agent(str(agent_path), eval_def)

        self.assertIn("Unknown check type", str(ctx.exception))
        self.assertIn("not_a_real_check", str(ctx.exception))

    def test_compare_snapshots_includes_removed_items(self) -> None:
        baseline = {
            "skills": {"plan": {"composite": 1.0}, "verify": {"composite": 0.9}},
            "agents": {"worker": {"composite": 0.8}},
            "triggers": {"skills": {"plan": {"score": 1.0}, "verify": {"score": 0.7}}},
        }
        current = {
            "skills": {"plan": {"composite": 0.95}},
            "agents": {},
            "triggers": {"skills": {"plan": {"score": 0.9}}},
        }

        result = compare_snapshots(baseline, current)

        self.assertIn("verify", result["skills"])
        self.assertTrue(result["skills"]["verify"]["removed"])
        self.assertEqual(result["skills"]["verify"]["current"], 0.0)
        self.assertIn("worker", result["agents"])
        self.assertTrue(result["agents"]["worker"]["removed"])
        self.assertIn("verify", result["triggers"])
        self.assertTrue(result["triggers"]["verify"]["removed"])


if __name__ == "__main__":
    unittest.main()
