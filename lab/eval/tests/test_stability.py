from __future__ import annotations

import unittest

from lab.eval.agent_scorer import score_all as score_all_agents
from lab.eval.scorer import score_core
from lab.eval.trigger_scorer import score_all as score_all_triggers


class StabilityTests(unittest.TestCase):
    def test_repeated_snapshots_match(self) -> None:
        first = {
            "skills": score_core(),
            "agents": score_all_agents(),
            "triggers": score_all_triggers(),
        }
        second = {
            "skills": score_core(),
            "agents": score_all_agents(),
            "triggers": score_all_triggers(),
        }
        self.assertEqual(first, second)
