"""Compare current deterministic eval results with a stored baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent_scorer import score_all as score_all_agents
from .scorer import score_core
from .trigger_scorer import score_all as score_all_triggers


BASELINES_DIR = Path(__file__).resolve().parent / "baselines"


def load_latest_baseline() -> dict:
    latest = BASELINES_DIR / "latest.json"
    if not latest.is_file():
        raise SystemExit("No baseline found. Run python3 -m lab.eval.baseline first.")
    return json.loads(latest.read_text(encoding="utf-8"))


def current_snapshot() -> dict:
    return {
        "skills": score_core(),
        "agents": score_all_agents(),
        "triggers": score_all_triggers(),
    }


def compare_snapshots(baseline: dict, current: dict) -> dict:
    results: dict[str, dict] = {}
    for subject in ("skills", "agents"):
        entries = {}
        for name, current_score in current[subject].items():
            baseline_score = baseline.get(subject, {}).get(name, {})
            before = float(baseline_score.get("composite", 0.0))
            after = float(current_score.get("composite", 0.0))
            entries[name] = {
                "baseline": round(before, 4),
                "current": round(after, 4),
                "delta": round(after - before, 4),
            }
        results[subject] = entries

    trigger_entries = {}
    baseline_triggers = baseline.get("triggers", {}).get("skills", {})
    current_triggers = current.get("triggers", {}).get("skills", {})
    for name, current_score in current_triggers.items():
        before = float(baseline_triggers.get(name, {}).get("score", 0.0))
        after = float(current_score.get("score", 0.0))
        trigger_entries[name] = {
            "baseline": round(before, 4),
            "current": round(after, 4),
            "delta": round(after - before, 4),
        }
    results["triggers"] = trigger_entries
    results["confusable_pairs"] = current.get("triggers", {}).get("confusable_pairs", [])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare current eval results to the latest baseline")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    baseline = load_latest_baseline()
    current = current_snapshot()
    comparison = compare_snapshots(baseline, current)
    print(json.dumps(comparison, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
