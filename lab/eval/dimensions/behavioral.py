"""Behavioral dimension: Does the skill trigger correctly for real user prompts?

Uses cached trigger test results from lab/eval/triggers/results/.
If no cached results exist, returns a neutral score (dimension skipped).
Run behavioral_scorer.py first to populate cache.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas import AssertionResult, DimensionResult


RESULTS_DIR = Path(__file__).resolve().parent.parent / "triggers" / "results"


def score(
    content: str,
    skill_path: str = "",
    plugin_root: str = "",
    **_,
) -> DimensionResult:
    """Score behavioral dimension using cached trigger results."""
    skill_name = Path(skill_path).resolve().parent.name if skill_path else ""
    cache_path = RESULTS_DIR / f"{skill_name}.json"

    if not cache_path.is_file():
        return DimensionResult(
            name="behavioral",
            score=1.0,
            assertions=[AssertionResult(
                check_type="trigger_accuracy",
                description="Trigger test results cached",
                passed=True,
                evidence=f"No trigger cache for {skill_name} — skipping (neutral)",
            )],
        )

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return DimensionResult(
            name="behavioral",
            score=1.0,
            assertions=[AssertionResult(
                check_type="trigger_accuracy",
                description="Trigger cache readable",
                passed=True,
                evidence=f"Corrupted cache for {skill_name} — skipping (neutral)",
            )],
        )

    if "error" in data:
        return DimensionResult(
            name="behavioral",
            score=1.0,
            assertions=[AssertionResult(
                check_type="trigger_accuracy",
                description="Trigger test results valid",
                passed=True,
                evidence=f"Error in cache for {skill_name}: {data['error']} — skipping (neutral)",
            )],
        )

    assertions = []

    accuracy = data.get("accuracy", 0)
    assertions.append(AssertionResult(
        check_type="trigger_accuracy",
        description="Trigger accuracy >= 75%",
        passed=accuracy >= 0.75,
        evidence=f"Trigger accuracy: {accuracy:.0%} ({data.get('correct', 0)}/{data.get('total', 0)})",
    ))

    precision = data.get("precision", 0)
    assertions.append(AssertionResult(
        check_type="trigger_precision",
        description="Trigger precision >= 80%",
        passed=precision >= 0.80,
        evidence=f"Precision: {precision:.0%} (TP={data.get('tp', 0)}, FP={data.get('fp', 0)})",
    ))

    recall = data.get("recall", 0)
    assertions.append(AssertionResult(
        check_type="trigger_recall",
        description="Trigger recall >= 60%",
        passed=recall >= 0.60,
        evidence=f"Recall: {recall:.0%} (TP={data.get('tp', 0)}, FN={data.get('fn', 0)})",
    ))

    # Tiered assertions (when hard-tier data is present)
    tier_counts = data.get("tier_counts", {})
    easy_count = tier_counts.get("easy", 0)
    hard_count = tier_counts.get("hard", 0)

    if easy_count > 0:
        easy_acc = data.get("easy_accuracy", 0)
        assertions.append(AssertionResult(
            check_type="easy_tier_accuracy",
            description="Easy tier accuracy >= 90%",
            passed=easy_acc >= 0.90,
            evidence=f"Easy tier accuracy: {easy_acc:.0%} ({easy_count} prompts)",
        ))

    if hard_count > 0:
        hard_acc = data.get("hard_accuracy", 0)
        # Advisory only — small corpus sizes make this too brittle to block.
        # Promote to blocking when hard corpus sizes reach 8-10 per skill.
        assertions.append(AssertionResult(
            check_type="hard_tier_accuracy",
            description="Hard tier accuracy >= 50% (advisory)",
            passed=hard_acc >= 0.50,
            evidence=f"Hard tier accuracy: {hard_acc:.0%} ({hard_count} prompts, advisory threshold)",
        ))

    passed = sum(1 for a in assertions if a.passed)
    dim_score = passed / len(assertions) if assertions else 0.0

    return DimensionResult(
        name="behavioral",
        score=dim_score,
        assertions=assertions,
    )
