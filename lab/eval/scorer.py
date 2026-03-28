#!/usr/bin/env python3
"""Score Ruby plugin skills with deterministic structural checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import matchers
from .schemas import AssertionResult, DimensionResult, EvalCheck, EvalDefinition, SubjectScore


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
                        {"type": "section_exists", "section": "Iron Laws", "desc": "Has Iron Laws"},
                        {"type": "has_iron_laws", "min_count": 1, "desc": "Has at least one law"},
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
                        {"type": "description_length", "min": 60, "max": 320, "desc": "Description length"},
                        {"type": "description_keywords", "min": 4, "desc": "Domain keywords"},
                        {"type": "description_structure", "desc": "Description has use/intent framing"},
                    ],
                },
                "safety": {
                    "weight": 0.12,
                    "checks": [
                        {"type": "has_iron_laws", "min_count": 1, "desc": "Iron laws present"},
                        {"type": "no_dangerous_patterns", "desc": "No catastrophic patterns"},
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
    fn = matchers.MATCHERS[check.check_type]
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
    content = path.read_text()
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


def score_all() -> dict[str, dict]:
    results: dict[str, dict] = {}
    for path in find_all_skills():
        skill_name = Path(path).parent.name
        eval_path = find_eval(skill_name)
        eval_def = EvalDefinition.from_file(eval_path) if eval_path else None
        results[skill_name] = score_skill(path, eval_def).to_dict()
    return results


def score_core() -> dict[str, dict]:
    results: dict[str, dict] = {}
    for skill_name in CORE_SKILLS:
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        eval_path = find_eval(skill_name)
        eval_def = EvalDefinition.from_file(eval_path) if eval_path else None
        results[skill_name] = score_skill(str(skill_path), eval_def).to_dict()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Ruby plugin skills deterministically")
    parser.add_argument("skill_path", nargs="?", help="Path to a SKILL.md file")
    parser.add_argument("--all", action="store_true", help="Score all skills")
    parser.add_argument("--core", action="store_true", help="Score the 1.6.0 core skill subset")
    parser.add_argument("--eval", help="Override eval definition JSON")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--fail-under", type=float, help="Exit non-zero if composite score is below threshold")
    args = parser.parse_args()

    if args.all:
        results = score_all()
        print(json.dumps(results, indent=2 if args.pretty else None))
        return

    if args.core:
        results = score_core()
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

    result = score_skill(args.skill_path, eval_def)
    if args.fail_under is not None and result.composite < args.fail_under:
        print(json.dumps(result.to_dict(), indent=2 if args.pretty else None))
        sys.exit(1)

    print(json.dumps(result.to_dict(), indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
