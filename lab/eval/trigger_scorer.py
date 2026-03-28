#!/usr/bin/env python3
"""Validate and analyze deterministic trigger corpora."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .matchers import PLUGIN_ROOT, parse_frontmatter, tokenize


TRIGGERS_DIR = Path(__file__).resolve().parent / "triggers"
SKILLS_DIR = PLUGIN_ROOT / "skills"
PROMPT_BUCKETS = (
    "should_trigger",
    "should_not_trigger",
    "hard_should_trigger",
    "hard_should_not_trigger",
)


def _extract_prompt(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("prompt", "")).strip()
    return ""


def normalize_prompt(prompt: str) -> str:
    return " ".join(sorted(tokenize(prompt)))


def load_all_descriptions() -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        fm = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        descriptions[skill_dir.name] = str(fm.get("description", ""))
    return descriptions


def load_trigger_file(skill_name: str) -> dict[str, Any] | None:
    path = TRIGGERS_DIR / f"{skill_name}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def score_trigger_file(skill_name: str, data: dict[str, Any]) -> dict[str, Any]:
    assertions: list[dict[str, Any]] = []
    positive = data.get("should_trigger", [])
    negative = data.get("should_not_trigger", [])
    hard_positive = data.get("hard_should_trigger", [])
    hard_negative = data.get("hard_should_not_trigger", [])

    all_prompts = []
    for bucket in PROMPT_BUCKETS:
        for item in data.get(bucket, []):
            prompt = _extract_prompt(item)
            if prompt:
                all_prompts.append((bucket, prompt))

    duplicate_count = len(all_prompts) - len({normalize_prompt(prompt) for _, prompt in all_prompts})
    hard_axes = sorted({item.get("axis", "") for item in hard_positive if isinstance(item, dict) and item.get("axis")})

    checks = [
        ("has_positive_prompts", len(positive) >= 4, f"{len(positive)} standard positives"),
        ("has_negative_prompts", len(negative) >= 4, f"{len(negative)} standard negatives"),
        ("has_hard_prompts", len(hard_positive) >= 2 and len(hard_negative) >= 2, f"{len(hard_positive)} hard positives / {len(hard_negative)} hard negatives"),
        ("no_duplicates", duplicate_count == 0, f"{duplicate_count} duplicate normalized prompts"),
        ("axis_diversity", len(hard_axes) >= 2, f"hard axes={hard_axes}"),
    ]

    for check_type, passed, evidence in checks:
        assertions.append({"type": check_type, "passed": passed, "evidence": evidence})

    score = sum(1 for item in assertions if item["passed"]) / len(assertions) if assertions else 0.0
    return {
        "skill": skill_name,
        "score": round(score, 4),
        "assertions": assertions,
        "prompt_counts": {bucket: len(data.get(bucket, [])) for bucket in PROMPT_BUCKETS},
    }


def build_confusable_pairs(descriptions: dict[str, str], limit: int = 10) -> list[dict[str, Any]]:
    bundle: dict[str, set[str]] = {}
    for skill, desc in descriptions.items():
        if load_trigger_file(skill) is None:
            continue
        tokens = set(tokenize(desc))
        data = load_trigger_file(skill) or {}
        for bucket in ("should_trigger", "hard_should_trigger"):
            for item in data.get(bucket, []):
                tokens.update(tokenize(_extract_prompt(item)))
        bundle[skill] = tokens

    pairs: list[dict[str, Any]] = []
    skills = sorted(bundle)
    for index, left in enumerate(skills):
        for right in skills[index + 1:]:
            shared = bundle[left] & bundle[right]
            union = bundle[left] | bundle[right]
            score = (len(shared) / len(union)) if union else 0.0
            if score <= 0:
                continue
            pairs.append(
                {
                    "left": left,
                    "right": right,
                    "overlap": round(score, 4),
                    "shared_tokens": sorted(shared)[:12],
                }
            )
    pairs.sort(key=lambda item: (-item["overlap"], item["left"], item["right"]))
    return pairs[:limit]


def score_all() -> dict[str, Any]:
    descriptions = load_all_descriptions()
    scores = {}
    for path in sorted(TRIGGERS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        scores[path.stem] = score_trigger_file(path.stem, json.loads(path.read_text(encoding="utf-8")))
    return {
        "skills": scores,
        "confusable_pairs": build_confusable_pairs(descriptions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Ruby plugin trigger corpora")
    parser.add_argument("--all", action="store_true", help="Score all trigger files")
    parser.add_argument("--skill", help="Score a single skill trigger file")
    parser.add_argument("--overlap", action="store_true", help="Print confusable pairs only")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    if args.overlap:
        print(json.dumps(build_confusable_pairs(load_all_descriptions()), indent=2 if args.pretty else None))
        return

    if args.skill:
        data = load_trigger_file(args.skill)
        if data is None:
            raise SystemExit(f"missing trigger file for {args.skill}")
        print(json.dumps(score_trigger_file(args.skill, data), indent=2 if args.pretty else None))
        return

    if args.all:
        print(json.dumps(score_all(), indent=2 if args.pretty else None))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
