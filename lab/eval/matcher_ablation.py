"""Leave-one-out matcher ablation for Ruby plugin eval framework.

Identifies which structural matchers provide signal vs noise by removing
each check type one at a time and measuring the impact on composite scores.

Purely deterministic -- no LLM calls.
"""


import argparse
import json
import sys
from pathlib import Path

from .schemas import EvalDefinition, EvalDimension, SubjectScore
from .scorer import default_eval, find_all_skills, find_eval, score_skill


RESULTS_PATH = Path(__file__).resolve().parent / "matcher_ablation_results.json"


def build_ablated_eval(
    eval_def: EvalDefinition,
    dim_name: str,
    check_idx: int,
) -> EvalDefinition | None:
    """Return a new EvalDefinition with one check removed.

    If removing the check empties the dimension, that dimension is dropped.
    Returns None only if the dimension/check is invalid or if no dimensions
    would remain.
    """
    dimension = eval_def.dimensions.get(dim_name)
    if dimension is None or check_idx >= len(dimension.checks):
        return None

    new_checks = [c for i, c in enumerate(dimension.checks) if i != check_idx]
    if not new_checks:
        # Removing last check in dimension -- drop the whole dimension
        new_dims = {k: v for k, v in eval_def.dimensions.items() if k != dim_name}
        if not new_dims:
            return None
        return EvalDefinition(
            subject=eval_def.subject,
            subject_path=eval_def.subject_path,
            dimensions=new_dims,
        )

    new_dim = EvalDimension(
        name=dimension.name,
        weight=dimension.weight,
        checks=new_checks,
    )
    new_dims = dict(eval_def.dimensions)
    new_dims[dim_name] = new_dim
    return EvalDefinition(
        subject=eval_def.subject,
        subject_path=eval_def.subject_path,
        dimensions=new_dims,
    )


def _get_eval_def(skill_path: str) -> EvalDefinition:
    """Load the eval definition for a skill (custom or default)."""
    skill_name = Path(skill_path).resolve().parent.name
    eval_path = find_eval(skill_name)
    if eval_path:
        return EvalDefinition.from_file(eval_path)
    return default_eval(skill_path)


def enumerate_checks(eval_defs: dict[str, EvalDefinition]) -> list[tuple[str, str]]:
    """List all unique (dimension, check_type) pairs across all eval definitions."""
    seen: set[tuple[str, str]] = set()
    for eval_def in eval_defs.values():
        for dim_name, dimension in eval_def.dimensions.items():
            for check in dimension.checks:
                seen.add((dim_name, check.check_type))
    return sorted(seen)


def _score_all_skills(
    skill_paths: list[str],
    eval_defs: dict[str, EvalDefinition],
) -> dict[str, SubjectScore]:
    """Score all skills and return SubjectScore objects keyed by skill path."""
    scores: dict[str, SubjectScore] = {}
    for path in skill_paths:
        scores[path] = score_skill(path, eval_defs[path])
    return scores


def run_ablation(
    skill_paths: list[str] | None = None,
) -> dict[str, list[dict]]:
    """Run the full leave-one-out ablation pipeline.

    Returns a classification dict with 'signal', 'guardrails', and 'noise' keys.
    """
    if skill_paths is None:
        skill_paths = find_all_skills()

    # Build eval definitions for each skill
    eval_defs: dict[str, EvalDefinition] = {}
    for path in skill_paths:
        eval_defs[path] = _get_eval_def(path)

    # Baseline scores
    baseline_scores = _score_all_skills(skill_paths, eval_defs)

    # Enumerate unique check types
    unique_checks = enumerate_checks(eval_defs)

    # Ablate each check type
    signal: list[dict] = []
    guardrails: list[dict] = []
    noise: list[dict] = []

    for dim_name, check_type in unique_checks:
        deltas: list[float] = []
        skills_affected = 0
        pass_count = 0
        fail_count = 0
        total_applicable = 0

        for path in skill_paths:
            eval_def = eval_defs[path]
            dimension = eval_def.dimensions.get(dim_name)
            if dimension is None:
                continue

            # Find the check index for this check_type in this dimension
            check_idx = None
            for i, check in enumerate(dimension.checks):
                if check.check_type == check_type:
                    check_idx = i
                    break
            if check_idx is None:
                continue

            total_applicable += 1

            # Check if this check passes in baseline (use cached result)
            baseline_result = baseline_scores[path]
            dim_result = baseline_result.dimensions.get(dim_name)
            if dim_result:
                for assertion in dim_result.assertions:
                    if assertion.check_type == check_type:
                        if assertion.passed:
                            pass_count += 1
                        else:
                            fail_count += 1
                        break

            # Build ablated eval and score
            ablated = build_ablated_eval(eval_def, dim_name, check_idx)
            if ablated is None:
                continue

            ablated_result = score_skill(path, ablated)
            delta = ablated_result.composite - baseline_result.composite
            deltas.append(delta)
            if abs(delta) > 0.001:
                skills_affected += 1

        if not deltas:
            continue

        avg_delta = sum(abs(d) for d in deltas) / len(deltas)
        pass_rate = pass_count / total_applicable if total_applicable else 0.0

        entry: dict[str, object] = {
            "check": check_type,
            "dimension": dim_name,
        }

        if skills_affected > 0:
            # Signal: removal changes composite for at least one skill
            entry["avg_delta"] = round(avg_delta, 4)
            entry["skills_affected"] = skills_affected
            signal.append(entry)
        elif pass_rate >= 0.999 and total_applicable > 0:
            # Guardrail: always passes, never affects composite
            entry["pass_rate"] = round(pass_rate, 4)
            guardrails.append(entry)
        else:
            # Noise: fails sometimes but never affects composite
            entry["fail_count"] = fail_count
            entry["avg_delta"] = round(avg_delta, 4)
            noise.append(entry)

    # Sort signal by impact (highest first)
    signal.sort(key=lambda x: x.get("avg_delta", 0), reverse=True)

    return {
        "signal": signal,
        "guardrails": guardrails,
        "noise": noise,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Leave-one-out matcher ablation for structural eval checks"
    )
    parser.add_argument(
        "--pretty", action="store_true",
        help="Pretty-print JSON output",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save results to matcher_ablation_results.json",
    )
    args = parser.parse_args()

    results = run_ablation()

    indent = 2 if args.pretty else None
    output = json.dumps(results, indent=indent)
    print(output)

    if args.save:
        RESULTS_PATH.write_text(output + "\n", encoding="utf-8")
        print(f"\nResults saved to {RESULTS_PATH}", file=sys.stderr, flush=True)

    # Print summary to stderr so stdout stays valid JSON
    print(f"\nSummary: {len(results['signal'])} signal, "
          f"{len(results['guardrails'])} guardrails, "
          f"{len(results['noise'])} noise", file=sys.stderr)


if __name__ == "__main__":
    main()
