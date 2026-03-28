#!/usr/bin/env python3
"""Check that deterministic eval output is stable across repeated runs."""

from __future__ import annotations

import json

from lab.eval.agent_scorer import score_all as score_all_agents
from lab.eval.scorer import score_core
from lab.eval.trigger_scorer import score_all as score_all_triggers


def snapshot() -> dict:
    return {
        "skills": score_core(),
        "agents": score_all_agents(),
        "triggers": score_all_triggers(),
    }


def main() -> None:
    first = snapshot()
    second = snapshot()
    stable = first == second
    payload = {
        "stable": stable,
        "first": first,
        "second": second if not stable else None,
    }
    print(json.dumps(payload, indent=2))
    if not stable:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
