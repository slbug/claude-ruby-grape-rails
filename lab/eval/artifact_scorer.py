#!/usr/bin/env python3
"""Score research/review output fixtures with deterministic checks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Callable

from . import output_checks


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "output"


CheckFn = Callable[[str], tuple[bool, str]]


@dataclass(frozen=True)
class CheckSpec:
    name: str
    description: str
    kind: str
    fn: CheckFn


@dataclass(frozen=True)
class FixtureSpec:
    name: str
    suite: str
    artifact_path: Path
    provenance_path: Path
    expected_failures: tuple[str, ...] = ()


COMMON_PROVENANCE_CHECKS: tuple[CheckSpec, ...] = (
    CheckSpec("provenance_header", "Has provenance heading", "provenance", output_checks.has_provenance_header),
    CheckSpec(
        "provenance_artifact_pointer",
        "Points back to the verified artifact",
        "provenance",
        output_checks.has_provenance_artifact_pointer,
    ),
    CheckSpec(
        "provenance_summary_counts",
        "Has summary counts",
        "provenance",
        output_checks.has_provenance_summary_counts,
    ),
    CheckSpec(
        "provenance_tier_summary",
        "Has source tier summary",
        "provenance",
        output_checks.has_provenance_tier_summary,
    ),
    CheckSpec(
        "provenance_claim_log",
        "Has claim log section",
        "provenance",
        output_checks.has_provenance_claim_log,
    ),
    CheckSpec(
        "provenance_claim_entries",
        "Has claim status entries",
        "provenance",
        output_checks.has_provenance_claim_entries,
    ),
    CheckSpec(
        "provenance_required_fixes",
        "Has required fixes section",
        "provenance",
        output_checks.has_provenance_required_fixes,
    ),
)

RESEARCH_CHECKS: tuple[CheckSpec, ...] = (
    CheckSpec("artifact_h1", "Has top-level heading", "artifact", output_checks.has_h1),
    CheckSpec(
        "research_metadata",
        "Has Last Updated/Date metadata",
        "artifact",
        output_checks.has_research_metadata,
    ),
    CheckSpec(
        "research_sources_section",
        "Has Sources section",
        "artifact",
        output_checks.has_sources_section,
    ),
    CheckSpec(
        "research_tiered_sources",
        "Uses tier markers in Sources",
        "artifact",
        output_checks.has_tiered_sources,
    ),
    CheckSpec(
        "research_inline_tiers",
        "Uses inline tier markers in the body",
        "artifact",
        output_checks.has_inline_tier_markers,
    ),
    CheckSpec(
        "research_decision_section",
        "Has summary/recommendation section",
        "artifact",
        output_checks.has_research_decision_section,
    ),
    CheckSpec(
        "research_provenance_external_evidence",
        "Provenance records external evidence",
        "provenance",
        output_checks.has_provenance_external_evidence,
    ),
) + COMMON_PROVENANCE_CHECKS

REVIEW_CHECKS: tuple[CheckSpec, ...] = (
    CheckSpec("review_title", "Has review heading", "artifact", output_checks.has_review_title),
    CheckSpec("review_verdict", "Has verdict line", "artifact", output_checks.has_review_verdict),
    CheckSpec(
        "review_summary_table",
        "Has severity summary table",
        "artifact",
        output_checks.has_review_summary_table,
    ),
    CheckSpec(
        "review_file_refs",
        "Findings cite file:line refs",
        "artifact",
        output_checks.has_review_file_refs,
    ),
    CheckSpec(
        "review_mandatory_table",
        "Has mandatory finding table",
        "artifact",
        output_checks.has_review_mandatory_table,
    ),
    CheckSpec(
        "review_no_task_lists",
        "Review stays findings-only",
        "artifact",
        output_checks.review_has_no_task_lists,
    ),
    CheckSpec(
        "review_provenance_local_evidence",
        "Provenance records local code evidence",
        "provenance",
        output_checks.has_provenance_local_evidence,
    ),
) + COMMON_PROVENANCE_CHECKS


FIXTURES: dict[str, tuple[FixtureSpec, ...]] = {
    "research": (
        FixtureSpec(
            name="research-good",
            suite="research",
            artifact_path=FIXTURES_DIR / "research-good.md",
            provenance_path=FIXTURES_DIR / "research-good.provenance.md",
        ),
        FixtureSpec(
            name="research-bad",
            suite="research",
            artifact_path=FIXTURES_DIR / "research-bad.md",
            provenance_path=FIXTURES_DIR / "research-bad.provenance.md",
            expected_failures=(
                "research_metadata",
                "research_tiered_sources",
                "research_inline_tiers",
                "research_decision_section",
                "research_provenance_external_evidence",
                "provenance_tier_summary",
                "provenance_claim_entries",
                "provenance_required_fixes",
            ),
        ),
    ),
    "review": (
        FixtureSpec(
            name="review-good",
            suite="review",
            artifact_path=FIXTURES_DIR / "review-good.md",
            provenance_path=FIXTURES_DIR / "review-good.provenance.md",
        ),
        FixtureSpec(
            name="review-bad",
            suite="review",
            artifact_path=FIXTURES_DIR / "review-bad.md",
            provenance_path=FIXTURES_DIR / "review-bad.provenance.md",
            expected_failures=(
                "review_verdict",
                "review_file_refs",
                "review_mandatory_table",
                "review_no_task_lists",
                "review_provenance_local_evidence",
                "provenance_claim_entries",
                "provenance_required_fixes",
            ),
        ),
    ),
}


def _suite_checks(suite: str) -> tuple[CheckSpec, ...]:
    if suite == "research":
        return RESEARCH_CHECKS
    if suite == "review":
        return REVIEW_CHECKS
    raise ValueError(f"Unknown suite: {suite}")


def score_fixture(spec: FixtureSpec) -> dict:
    artifact = spec.artifact_path.read_text()
    provenance = spec.provenance_path.read_text()
    checks = _suite_checks(spec.suite)

    assertions = []
    actual_failures: list[str] = []
    expected_failures = set(spec.expected_failures)
    matched = 0

    for check in checks:
        content = artifact if check.kind == "artifact" else provenance
        passed, evidence = check.fn(content)
        expected = check.name not in expected_failures
        if not passed:
            actual_failures.append(check.name)
        if passed == expected:
            matched += 1
        assertions.append(
            {
                "name": check.name,
                "desc": check.description,
                "kind": check.kind,
                "passed": passed,
                "expected": expected,
                "evidence": evidence,
            }
        )

    actual_failure_set = set(actual_failures)
    fixture_passed = actual_failure_set == expected_failures
    score = matched / len(checks) if checks else 0.0

    return {
        "suite": spec.suite,
        "artifact": str(spec.artifact_path.relative_to(PROJECT_ROOT)),
        "provenance": str(spec.provenance_path.relative_to(PROJECT_ROOT)),
        "expected_failures": sorted(expected_failures),
        "actual_failures": sorted(actual_failure_set),
        "matched_expectation": fixture_passed,
        "score": round(score, 4),
        "assertions": assertions,
    }


def score_suite(suite: str) -> dict:
    fixture_results = {spec.name: score_fixture(spec) for spec in FIXTURES[suite]}
    passed = sum(1 for result in fixture_results.values() if result["matched_expectation"])
    total = len(fixture_results)
    composite = passed / total if total else 0.0
    return {
        "suite": suite,
        "fixtures": fixture_results,
        "summary": {
            "matched": passed,
            "total": total,
            "composite": round(composite, 4),
        },
    }


def score_all() -> dict[str, dict]:
    return {suite: score_suite(suite) for suite in ("research", "review")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Score research/review output fixtures")
    parser.add_argument("--suite", choices=("research", "review"), help="Score one artifact suite")
    parser.add_argument("--all", action="store_true", help="Score all artifact suites")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=1.0,
        help="Exit non-zero if suite composite is below this threshold (default: 1.0)",
    )
    args = parser.parse_args()

    if not args.all and not args.suite:
        parser.print_help()
        sys.exit(1)

    if args.all:
        results = score_all()
        print(json.dumps(results, indent=2 if args.pretty else None))
        failing = [suite for suite, result in results.items() if result["summary"]["composite"] < args.fail_under]
        if failing:
            sys.exit(1)
        return

    result = score_suite(args.suite)
    print(json.dumps(result, indent=2 if args.pretty else None))
    if result["summary"]["composite"] < args.fail_under:
        sys.exit(1)


if __name__ == "__main__":
    main()
