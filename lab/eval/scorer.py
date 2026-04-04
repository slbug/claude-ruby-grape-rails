"""Score Ruby plugin skills with deterministic structural checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import matchers
from .schemas import AssertionResult, DimensionResult, EvalCheck, EvalDefinition, EvalDimension, SubjectScore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = PROJECT_ROOT / "plugins" / "ruby-grape-rails"
SKILLS_DIR = PLUGIN_ROOT / "skills"
EVALS_DIR = Path(__file__).resolve().parent / "evals"
CORE_SKILLS = ("plan", "work", "review", "verify", "permissions", "research")


def default_eval(skill_path: str) -> EvalDefinition:
    name = Path(skill_path).resolve().parent.name
    return EvalDefinition.from_dict(
        {
            "skill": name,
            "skill_path": skill_path,
            "dimensions": {
                "completeness": {
                    "weight": 0.22,
                    "checks": [
                        {"type": "frontmatter_field", "field": "name", "desc": "Has command name"},
                        {"type": "frontmatter_field", "field": "description", "desc": "Has description"},
                    ],
                },
                "accuracy": {
                    "weight": 0.18,
                    "checks": [
                        {"type": "valid_skill_refs", "desc": "Valid skill refs"},
                        {"type": "valid_agent_refs", "desc": "Valid agent refs"},
                        {"type": "valid_file_refs", "desc": "Valid local refs"},
                    ],
                },
                "conciseness": {
                    "weight": 0.15,
                    "checks": [
                        {"type": "line_count", "target": 140, "tolerance": 220, "desc": "Reasonable length"},
                        {"type": "max_section_lines", "max": 60, "desc": "Sections not overgrown"},
                    ],
                },
                "triggering": {
                    "weight": 0.15,
                    "checks": [
                        {"type": "description_length", "min": 60, "max": 250, "desc": "Description length"},
                        {"type": "description_keywords", "min": 3, "desc": "Domain keywords"},
                        {"type": "description_structure", "desc": "Description has use/intent framing"},
                    ],
                },
                "safety": {
                    "weight": 0.12,
                    "checks": [
                        {"type": "no_dangerous_patterns", "desc": "No catastrophic patterns"},
                        {"type": "no_bash_blocks", "desc": "No executable bash blocks in SKILL.md"},
                    ],
                },
                "clarity": {
                    "weight": 0.18,
                    "checks": [
                        {"type": "action_density", "min_ratio": 0.14, "desc": "Actionable density"},
                        {"type": "no_duplication", "desc": "No repeated long lines"},
                        {"type": "workflow_step_coverage", "min_sections": 3, "desc": "Enough structure"},
                        {"type": "specificity_ratio", "min_ratio": 0.10, "desc": "Concrete guidance"},
                    ],
                },
            },
        }
    )


def _run_check(content: str, check: EvalCheck, skill_path: str) -> AssertionResult:
    fn = matchers.MATCHERS.get(check.check_type)
    if fn is None:
        available = ", ".join(sorted(matchers.MATCHERS))
        raise ValueError(f"Unknown check type: {check.check_type!r}. Available: {available}")
    passed, evidence = fn(
        content,
        skill_path=skill_path,
        plugin_root=str(PLUGIN_ROOT),
        **check.params,
    )
    return AssertionResult(
        check_type=check.check_type,
        description=check.description,
        passed=bool(passed),
        evidence=evidence,
    )


def score_skill(skill_path: str, eval_def: EvalDefinition | None = None) -> SubjectScore:
    path = Path(skill_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Missing skill file: {path}")
    content = path.read_text(encoding="utf-8")
    definition = eval_def or default_eval(str(path))
    dimensions: dict[str, DimensionResult] = {}
    total_weight = 0.0
    weighted = 0.0

    for name, dimension in definition.dimensions.items():
        assertions = [_run_check(content, check, str(path)) for check in dimension.checks]
        passed = sum(1 for item in assertions if item.passed)
        score = (passed / len(assertions)) if assertions else 0.0
        dimensions[name] = DimensionResult(name=name, score=score, assertions=assertions)
        weighted += score * dimension.weight
        total_weight += dimension.weight

    composite = weighted / total_weight if total_weight else 0.0
    return SubjectScore(
        subject_name=definition.subject or path.parent.name,
        subject_path=str(path),
        composite=composite,
        dimensions=dimensions,
    )


def find_all_skills() -> list[str]:
    return [str(path) for path in sorted(SKILLS_DIR.glob("*/SKILL.md"))]


def find_eval(skill_name: str) -> Path | None:
    path = EVALS_DIR / f"{skill_name}.json"
    return path if path.is_file() else None


def score_all(behavioral: bool = False) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for path in find_all_skills():
        skill_name = Path(path).parent.name
        eval_path = find_eval(skill_name)
        eval_def = EvalDefinition.from_file(eval_path) if eval_path else None
        if behavioral:
            eval_def = _inject_behavioral(eval_def or default_eval(path))
        results[skill_name] = score_skill(path, eval_def).to_dict()
    return results


def score_core(behavioral: bool = False) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for skill_name in CORE_SKILLS:
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        if not skill_path.is_file():
            raise FileNotFoundError(f"Missing core skill file: {skill_path}")
        eval_path = find_eval(skill_name)
        eval_def = EvalDefinition.from_file(eval_path) if eval_path else None
        if behavioral:
            eval_def = _inject_behavioral(eval_def or default_eval(str(skill_path)))
        results[skill_name] = score_skill(str(skill_path), eval_def).to_dict()
    return results


def _inject_behavioral(eval_def: EvalDefinition) -> EvalDefinition:
    """Add the behavioral dimension to an eval definition (opt-in)."""
    new_dims = dict(eval_def.dimensions)
    new_dims["behavioral"] = EvalDimension(
        name="behavioral",
        weight=0.08,
        checks=[EvalCheck(
            check_type="behavioral_routing",
            description="Trigger routing accuracy",
            params={},
        )],
    )
    return EvalDefinition(
        subject=eval_def.subject,
        subject_path=eval_def.subject_path,
        dimensions=new_dims,
    )


def _behavioral_check(content: str, skill_path: str = "", plugin_root: str = "", **_) -> tuple[bool, str]:
    """Run the behavioral dimension scorer and return a single pass/fail."""
    from .dimensions.behavioral import score as behavioral_score

    result = behavioral_score(content, skill_path=skill_path, plugin_root=plugin_root)
    all_passed = all(a.passed for a in result.assertions)
    evidence = "; ".join(a.evidence for a in result.assertions)
    return all_passed, evidence


def _compare_scores() -> None:
    """Print side-by-side base vs behavioral composite scores."""
    base = score_all(behavioral=False)

    matchers.MATCHERS["behavioral_routing"] = _behavioral_check
    behav = score_all(behavioral=True)

    print(f"{'Skill':<35} {'Base':>7} {'+Behav':>7} {'Δ':>7}")
    print("-" * 60)
    changed = 0
    for name in sorted(base.keys()):
        s1 = base[name]["composite"]
        s2 = behav[name]["composite"]
        delta = s2 - s1
        flag = " *" if abs(delta) > 0.001 else ""
        if flag:
            changed += 1
        print(f"{name:<35} {s1:>7.4f} {s2:>7.4f} {delta:>+7.4f}{flag}")
    total = len(base)
    avg_base = sum(v["composite"] for v in base.values()) / total if total else 0
    avg_behav = sum(v["composite"] for v in behav.values()) / total if total else 0
    print("-" * 60)
    print(f"{'Average':<35} {avg_base:>7.4f} {avg_behav:>7.4f} {avg_behav - avg_base:>+7.4f}")
    print(f"\n{changed}/{total} skills changed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Ruby plugin skills deterministically")
    parser.add_argument("skill_path", nargs="?", help="Path to a SKILL.md file")
    parser.add_argument("--all", action="store_true", help="Score all skills")
    parser.add_argument("--core", action="store_true", help="Score the core skill subset")
    parser.add_argument("--eval", help="Override eval definition JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--behavioral", action="store_true", help="Include behavioral routing dimension (requires cached results)")
    parser.add_argument("--compare", action="store_true", help="Show base vs behavioral composite score diff table")
    parser.add_argument("--fail-under", type=float, help="Exit non-zero if composite score is below threshold")
    args = parser.parse_args()

    if args.compare:
        _compare_scores()
        return

    if args.behavioral:
        matchers.MATCHERS["behavioral_routing"] = _behavioral_check

    if args.all:
        results = score_all(behavioral=args.behavioral)
        print(json.dumps(results, indent=2 if args.pretty else None))
        return

    if args.core:
        results = score_core(behavioral=args.behavioral)
        print(json.dumps(results, indent=2 if args.pretty else None))
        return

    if not args.skill_path:
        parser.print_help()
        sys.exit(1)

    eval_def = EvalDefinition.from_file(args.eval) if args.eval else None
    if eval_def is None:
        skill_name = Path(args.skill_path).resolve().parent.name
        eval_path = find_eval(skill_name)
        if eval_path:
            eval_def = EvalDefinition.from_file(eval_path)

    if eval_def and args.behavioral:
        eval_def = _inject_behavioral(eval_def)
    elif eval_def is None and args.behavioral:
        eval_def = _inject_behavioral(default_eval(args.skill_path))

    result = score_skill(args.skill_path, eval_def)
    if args.fail_under is not None and result.composite < args.fail_under:
        print(json.dumps(result.to_dict(), indent=2 if args.pretty else None))
        sys.exit(1)

    print(json.dumps(result.to_dict(), indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
