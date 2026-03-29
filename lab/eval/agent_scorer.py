"""Score Ruby plugin agents with deterministic structural checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import agent_matchers, matchers
from .schemas import AssertionResult, DimensionResult, EvalDefinition, SubjectScore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = PROJECT_ROOT / "plugins" / "ruby-grape-rails"
AGENTS_DIR = PLUGIN_ROOT / "agents"


def default_eval(agent_path: str) -> EvalDefinition:
    name = Path(agent_path).stem
    return EvalDefinition.from_dict(
        {
            "agent": name,
            "agent_path": agent_path,
            "dimensions": {
                "completeness": {
                    "weight": 0.24,
                    "checks": [
                        {"type": "frontmatter_field", "field": "name", "desc": "Has name"},
                        {"type": "frontmatter_field", "field": "description", "desc": "Has description"},
                        {"type": "tools_present", "min_count": 1, "desc": "Lists tools"},
                        {"type": "effort_present", "desc": "Declares effort"},
                    ],
                },
                "accuracy": {
                    "weight": 0.22,
                    "checks": [
                        {"type": "valid_skill_refs", "desc": "Valid skill refs"},
                        {"type": "valid_agent_refs", "desc": "Valid agent refs"},
                        {"type": "permission_mode_valid", "desc": "Valid permission mode"},
                    ],
                },
                "conciseness": {
                    "weight": 0.16,
                    "checks": [
                        {"type": "line_count", "target": 120, "tolerance": 180, "desc": "Reasonable length"},
                        {"type": "max_section_lines", "max": 55, "desc": "Sections controlled"},
                    ],
                },
                "safety": {
                    "weight": 0.18,
                    "checks": [
                        {"type": "disallowed_tools_present", "desc": "Has disallowed tools"},
                        {"type": "read_only_tools_coherent", "desc": "Tool restrictions coherent"},
                        {"type": "no_dangerous_patterns", "desc": "No catastrophic patterns"},
                    ],
                },
                "consistency": {
                    "weight": 0.20,
                    "checks": [
                        {"type": "description_length", "min": 60, "max": 320, "desc": "Description length"},
                        {"type": "description_keywords", "min": 3, "desc": "Description keywords"},
                        {"type": "action_density", "min_ratio": 0.10, "desc": "Action density"},
                    ],
                },
            },
        }
    )


def _run_check(content: str, check_type: str, description: str, agent_path: str, params: dict) -> AssertionResult:
    if check_type in agent_matchers.MATCHERS:
        fn = agent_matchers.MATCHERS[check_type]
    else:
        fn = matchers.MATCHERS.get(check_type)
        if fn is None:
            available = ", ".join(sorted(set(agent_matchers.MATCHERS) | set(matchers.MATCHERS)))
            raise ValueError(f"Unknown check type: {check_type!r}. Available: {available}")
    passed, evidence = fn(content, skill_path=agent_path, plugin_root=str(PLUGIN_ROOT), **params)
    return AssertionResult(check_type=check_type, description=description, passed=bool(passed), evidence=evidence)


def score_agent(agent_path: str, eval_def: EvalDefinition | None = None) -> SubjectScore:
    path = Path(agent_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Agent file not found: {path}. This file may have been moved or deleted."
        )
    content = path.read_text(encoding="utf-8")
    definition = eval_def or default_eval(str(path))
    dimensions: dict[str, DimensionResult] = {}
    total_weight = 0.0
    weighted = 0.0

    for name, dimension in definition.dimensions.items():
        assertions = [
            _run_check(content, check.check_type, check.description, str(path), check.params)
            for check in dimension.checks
        ]
        score = (sum(1 for item in assertions if item.passed) / len(assertions)) if assertions else 0.0
        dimensions[name] = DimensionResult(name=name, score=score, assertions=assertions)
        weighted += score * dimension.weight
        total_weight += dimension.weight

    return SubjectScore(
        subject_name=definition.subject or path.stem,
        subject_path=str(path),
        composite=(weighted / total_weight) if total_weight else 0.0,
        dimensions=dimensions,
    )


def find_all_agents() -> list[str]:
    return [str(path) for path in sorted(AGENTS_DIR.glob("*.md"))]


def score_all() -> dict[str, dict]:
    return {Path(path).stem: score_agent(path).to_dict() for path in find_all_agents()}


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Ruby plugin agents deterministically")
    parser.add_argument("agent_path", nargs="?", help="Path to an agent markdown file")
    parser.add_argument("--all", action="store_true", help="Score all agents")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    if args.all:
        print(json.dumps(score_all(), indent=2 if args.pretty else None))
        return

    if not args.agent_path:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(score_agent(args.agent_path).to_dict(), indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
