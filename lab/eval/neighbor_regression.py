"""Neighbor regression detection for confusable skill pairs.

Detects when changing one skill's description or triggers degrades
routing accuracy for confusable neighbors.

Usage:
    python3 -m lab.eval.neighbor_regression --skill plan       # Test skill + neighbors
    python3 -m lab.eval.neighbor_regression --changed           # Test git-changed skills
    python3 -m lab.eval.neighbor_regression --all               # Test all confusable skills
    python3 -m lab.eval.neighbor_regression --dry-run --changed # Show what would be tested
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from . import results_dir as rd
from .behavioral_scorer import score_skill
from .results_dir import SUPPORTED_PROVIDERS
from .trigger_scorer import (
    TRIGGERS_DIR,
    load_all_routing_descriptions,
    load_trigger_file,
    routing_descriptions_blob,
    RoutingDescriptions,
)


CONFUSABLE_PAIRS_PATH = TRIGGERS_DIR / "_confusable_pairs.json"
REGRESSION_THRESHOLD = 0.10  # Flag drops > 10%


def build_neighbor_map() -> dict[str, list[tuple[str, float]]]:
    """Parse _confusable_pairs.json into skill -> [(neighbor, overlap)] map.

    Returns bidirectional mapping: if A-B is a pair, both A->B and B->A appear.
    Neighbors are sorted by descending overlap score.
    """
    if not CONFUSABLE_PAIRS_PATH.is_file():
        return {}

    data = json.loads(CONFUSABLE_PAIRS_PATH.read_text(encoding="utf-8"))
    pairs = data.get("pairs", [])

    neighbors: dict[str, list[tuple[str, float]]] = {}
    for pair in pairs:
        left = pair["left"]
        right = pair["right"]
        overlap = pair["overlap"]
        neighbors.setdefault(left, []).append((right, overlap))
        neighbors.setdefault(right, []).append((left, overlap))

    # Sort each neighbor list by descending overlap
    for skill in neighbors:
        neighbors[skill].sort(key=lambda x: -x[1])

    return neighbors


def get_changed_skills() -> list[str]:
    """Detect changed skills from git diff of SKILL.md files (staged + unstaged)."""
    skills: set[str] = set()

    def _collect_from_diff(args: list[str]) -> None:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", *args],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line or "skills/" not in line or not line.endswith("SKILL.md"):
                continue
            parts = line.split("/")
            try:
                idx = parts.index("skills")
                if idx + 1 < len(parts):
                    skills.add(parts[idx + 1])
            except ValueError:
                continue

    _collect_from_diff(["HEAD"])  # staged
    _collect_from_diff([])        # unstaged

    return sorted(skills)


def get_test_set(
    skill_name: str,
    neighbor_map: dict[str, list[tuple[str, float]]],
    max_neighbors: int = 3,
) -> list[tuple[str, float | None]]:
    """Return skill + top N neighbors as [(name, overlap_or_None)].

    The primary skill has overlap=None. Neighbors are sorted by
    descending overlap score, limited to max_neighbors.
    """
    test_set: list[tuple[str, float | None]] = [(skill_name, None)]
    neighbors = neighbor_map.get(skill_name, [])
    for neighbor, overlap in neighbors[:max_neighbors]:
        test_set.append((neighbor, overlap))
    return test_set


def load_baseline(skill_name: str) -> dict | None:
    """Read cached result from results/{skill}.json."""
    cache_path = rd.active_results_dir() / f"{skill_name}.json"
    if not cache_path.is_file():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def compare_results(
    skill_name: str,
    baseline: dict,
    current: dict,
) -> dict:
    """Compare baseline vs current accuracy. Flag >10% drops as regressions."""
    baseline_acc = baseline.get("accuracy", 0.0)
    current_acc = current.get("accuracy", 0.0)
    delta = current_acc - baseline_acc
    regression = delta < -REGRESSION_THRESHOLD

    return {
        "skill": skill_name,
        "baseline_accuracy": baseline_acc,
        "current_accuracy": current_acc,
        "delta": round(delta, 4),
        "regression": regression,
    }


def _format_pct(value: float) -> str:
    return f"{value:.0%}"


def _format_delta(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.0%}"


def run_regression_check(
    skill_name: str,
    neighbor_map: dict[str, list[tuple[str, float]]],
    descriptions: RoutingDescriptions,
    descriptions_blob: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Run neighbor regression check for one skill. Returns True if passed."""
    test_set = get_test_set(skill_name, neighbor_map)

    print(f"Neighbor regression check: {skill_name}")
    neighbors = [(name, overlap) for name, overlap in test_set if overlap is not None]
    if neighbors:
        neighbor_str = ", ".join(f"{n} ({o:.2f})" for n, o in neighbors)
        print(f"  Neighbors: {neighbor_str}")
    else:
        print("  Neighbors: (none in confusable pairs)")

    if dry_run:
        print(f"  Would test: {', '.join(name for name, _ in test_set)}")
        print("  Result: DRY RUN (skipped)")
        return True

    regressions = []
    compared = 0
    for name, _overlap in test_set:
        baseline = load_baseline(name)

        # Check if skill has trigger file before scoring
        triggers = load_trigger_file(name)
        if not triggers:
            print(f"  {name}: no trigger file (skipped)")
            continue

        if baseline is None:
            print(f"  {name}: no baseline (skipped)")
            continue

        if verbose:
            print(f"  Scoring {name}...", file=sys.stderr)

        # Save baseline file before scoring (score_skill overwrites cache)
        baseline_path = rd.active_results_dir() / f"{name}.json"
        baseline_backup = baseline_path.read_bytes() if baseline_path.is_file() else None

        current, _ = score_skill(
            name,
            descriptions,
            verbose=verbose,
            descriptions_blob=descriptions_blob,
        )

        # Restore baseline so subsequent runs compare against stable reference
        if baseline_backup is not None:
            baseline_path.write_bytes(baseline_backup)

        if "error" in current:
            print(f"  {name}: error ({current['error']})")
            continue

        compared += 1
        comparison = compare_results(name, baseline, current)
        status = "REGRESSION" if comparison["regression"] else "ok"
        print(
            f"  {name}: baseline={_format_pct(comparison['baseline_accuracy'])} "
            f"current={_format_pct(comparison['current_accuracy'])} "
            f"\u0394={_format_delta(comparison['delta'])} "
            f"[{status}]"
        )

        if comparison["regression"]:
            regressions.append(comparison)

    if compared == 0:
        print("  Result: SKIP (no baselines to compare against)")
        return True
    if regressions:
        names = ", ".join(r["skill"] for r in regressions)
        print(f"  Result: FAIL (regressions in: {names})")
        return False
    else:
        print(f"  Result: PASS ({compared} skills compared, no regressions)")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect neighbor routing regressions for confusable skills"
    )
    parser.add_argument("--skill", help="Test a specific skill + its neighbors")
    parser.add_argument("--changed", action="store_true",
                        help="Test git-changed skills + their neighbors")
    parser.add_argument("--all", action="store_true",
                        help="Test all skills that have confusable pairs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be tested without making API calls")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed output")
    parser.add_argument("--provider", default=None,
                        choices=sorted(SUPPORTED_PROVIDERS),
                        help=(
                            "Routing provider for fresh scoring calls. "
                            "Default: RUBY_PLUGIN_EVAL_PROVIDER env var or ollama."
                        ))
    args = parser.parse_args()

    rd.set_active_provider(args.provider)

    neighbor_map = build_neighbor_map()
    descriptions = load_all_routing_descriptions()
    descriptions_blob = routing_descriptions_blob(descriptions)
    all_passed = True

    if args.skill:
        if args.skill not in descriptions:
            print(f"Unknown skill: {args.skill}", file=sys.stderr)
            raise SystemExit(1)
        passed = run_regression_check(
            args.skill, neighbor_map, descriptions,
            descriptions_blob=descriptions_blob,
            dry_run=args.dry_run, verbose=args.verbose,
        )
        if not passed:
            all_passed = False

    elif args.changed:
        changed = get_changed_skills()
        if not changed:
            print("No changed skills detected.")
            raise SystemExit(0)
        print(f"Changed skills: {', '.join(changed)}\n")
        for skill in changed:
            if skill not in descriptions:
                print(f"Skipping unknown skill: {skill}")
                continue
            passed = run_regression_check(
                skill, neighbor_map, descriptions,
                descriptions_blob=descriptions_blob,
                dry_run=args.dry_run, verbose=args.verbose,
            )
            if not passed:
                all_passed = False
            print()

    elif args.all:
        tested = set()
        for skill in sorted(neighbor_map.keys()):
            if skill in tested:
                continue
            if skill not in descriptions:
                continue
            passed = run_regression_check(
                skill, neighbor_map, descriptions,
                descriptions_blob=descriptions_blob,
                dry_run=args.dry_run, verbose=args.verbose,
            )
            if not passed:
                all_passed = False
            tested.add(skill)
            for neighbor, _ in neighbor_map.get(skill, []):
                tested.add(neighbor)
            print()

    else:
        parser.print_help()
        raise SystemExit(0)

    if not all_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
