"""Create a baseline snapshot for skills, agents, and triggers."""


from datetime import datetime, timezone
import json
from pathlib import Path

from .agent_scorer import score_all as score_all_agents
from .scorer import score_core
from .trigger_scorer import score_all as score_all_triggers


BASELINES_DIR = Path(__file__).resolve().parent / "baselines"


def write_baseline() -> Path:
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    payload = {
        "timestamp": timestamp,
        "skills": score_core(),
        "agents": score_all_agents(),
        "triggers": score_all_triggers(),
    }
    target = BASELINES_DIR / f"{timestamp}.json"
    target.write_text(json.dumps(payload, indent=2) + "\n")
    latest = BASELINES_DIR / "latest.json"
    latest.write_text(json.dumps(payload, indent=2) + "\n")
    return target


if __name__ == "__main__":
    path = write_baseline()
    print(str(path))
