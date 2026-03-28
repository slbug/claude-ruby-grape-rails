from __future__ import annotations

import unittest

from lab.eval.agent_scorer import find_all_agents, score_agent
from lab.eval.scorer import find_all_skills, score_skill
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


if __name__ == "__main__":
    unittest.main()
