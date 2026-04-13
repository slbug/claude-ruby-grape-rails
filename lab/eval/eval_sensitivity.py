"""Eval-set sensitivity analysis — leave-one-out metric fragility.

Recomputes accuracy from cached behavioral results, removing one prompt
at a time. No API calls, $0 cost, instant execution.

Usage:
    python3 -m lab.eval.eval_sensitivity --skill plan
    python3 -m lab.eval.eval_sensitivity --all --summary
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .results_dir import results_dir


# Same provider-scoped cache directory the behavioral scorer writes to.
# Tests patch this attribute directly.
RESULTS_DIR = results_dir()

LEVERAGE_THRESHOLD = 0.05  # 5% accuracy swing


def classify_prompt_impact(delta: float) -> str:
    """Classify a prompt's metric impact based on leave-one-out delta."""
    if delta < -LEVERAGE_THRESHOLD:
        return "high-leverage"  # Removal drops accuracy — metric depends on this case
    elif delta > LEVERAGE_THRESHOLD:
        return "drag"  # Removal improves accuracy — consistently failing, investigate
    elif abs(delta) < 0.01:
        return "redundant"  # No metric impact
    else:
        return "contributing"  # Modest healthy impact


def analyze_skill(skill_name: str) -> dict | None:
    """Leave-one-out sensitivity analysis for one skill's cached results."""
    cache_path = RESULTS_DIR / f"{skill_name}.json"
    if not cache_path.is_file():
        return None

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"skill": skill_name, "error": f"invalid cached results JSON: {exc}"}
    except OSError as exc:
        return {"skill": skill_name, "error": f"failed to read cached results: {exc}"}

    results = data.get("results", [])
    if len(results) < 3:
        return {"skill": skill_name, "error": f"too few results ({len(results)}) for sensitivity analysis"}

    baseline_correct = sum(1 for r in results if r.get("correct"))
    baseline_accuracy = baseline_correct / len(results)

    prompt_impacts = []
    for i, result in enumerate(results):
        # Recompute accuracy without this prompt
        remaining = results[:i] + results[i + 1:]
        remaining_correct = sum(1 for r in remaining if r.get("correct"))
        loo_accuracy = remaining_correct / len(remaining) if remaining else 0.0
        delta = loo_accuracy - baseline_accuracy

        prompt_impacts.append({
            "prompt": result.get("prompt", "")[:100],
            "expected": result.get("expected"),
            "correct": result.get("correct"),
            "tier": result.get("tier", "easy"),
            "delta": round(delta, 4),
            "impact": classify_prompt_impact(delta),
        })

    deltas = [abs(p["delta"]) for p in prompt_impacts]
    fragility_max = max(deltas) if deltas else 0.0
    fragility_mean = sum(deltas) / len(deltas) if deltas else 0.0
    redundant_count = sum(1 for p in prompt_impacts if p["impact"] == "redundant")
    redundancy_ratio = redundant_count / len(prompt_impacts) if prompt_impacts else 0.0

    high_leverage = [p for p in prompt_impacts if p["impact"] == "high-leverage"]
    drags = [p for p in prompt_impacts if p["impact"] == "drag"]

    return {
        "skill": skill_name,
        "baseline_accuracy": round(baseline_accuracy, 4),
        "total_prompts": len(results),
        "fragility_max": round(fragility_max, 4),
        "fragility_mean": round(fragility_mean, 4),
        "redundancy_ratio": round(redundancy_ratio, 4),
        "high_leverage_count": len(high_leverage),
        "drag_count": len(drags),
        "high_leverage": high_leverage,
        "drags": drags,
        "prompt_impacts": prompt_impacts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval-set sensitivity analysis (leave-one-out)")
    parser.add_argument("--skill", help="Analyze one skill")
    parser.add_argument("--all", action="store_true", help="Analyze all skills with cached results")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    if args.skill:
        result = analyze_skill(args.skill)
        if result is None:
            print(f"No cached results for {args.skill}", file=sys.stderr)
            raise SystemExit(1)
        if "error" in result:
            print(f"{args.skill}: {result['error']}", file=sys.stderr)
            raise SystemExit(1)
        if args.summary:
            _print_summary(args.skill, result)
        else:
            print(json.dumps(result, indent=2 if args.pretty else None))

    elif args.all:
        all_results = {}
        for path in sorted(RESULTS_DIR.glob("*.json")):
            if path.name.startswith("_"):
                continue
            result = analyze_skill(path.stem)
            if result and "error" not in result:
                all_results[path.stem] = result

        if args.summary:
            for name, result in sorted(all_results.items()):
                _print_summary(name, result)
            fragile = [n for n, r in all_results.items() if r["fragility_max"] >= 0.10]
            print(f"\n{len(all_results)} skills analyzed, "
                  f"{len(fragile)} with fragility >= 0.10: {fragile or 'none'}",
                  file=sys.stderr)
        else:
            print(json.dumps(all_results, indent=2 if args.pretty else None))

    else:
        parser.print_help()


def _print_summary(name: str, result: dict) -> None:
    """Print one-line summary for a skill."""
    fmax = result.get("fragility_max", 0)
    fmean = result.get("fragility_mean", 0)
    hl = result.get("high_leverage_count", 0)
    drags = result.get("drag_count", 0)
    redundancy = result.get("redundancy_ratio", 0)
    flag = " FRAGILE" if fmax >= 0.10 else ""
    print(f"  {name}: fragility={fmax:.2f} (mean={fmean:.2f}) "
          f"high-leverage={hl} drags={drags} "
          f"redundancy={redundancy:.0%}{flag}")


if __name__ == "__main__":
    main()
