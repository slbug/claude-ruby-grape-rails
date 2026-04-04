"""Contamination hygiene checker for trigger corpora.

Scans trigger files for prompts that leak routing answers into evaluation
metrics — skill name leaks, description echo, and hard corpus quality issues.

Pure deterministic — no LLM calls.

Usage:
    python3 -m lab.eval.triggers.hygiene --all              # Scan all skills
    python3 -m lab.eval.triggers.hygiene --skill plan       # Scan one skill
    python3 -m lab.eval.triggers.hygiene --all --summary    # Summary only
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from ..trigger_scorer import (
    TRIGGERS_DIR,
    load_all_descriptions,
    load_trigger_file,
    _extract_prompt,
    PROMPT_BUCKETS,
)


STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "for", "to", "in", "of", "and", "or",
    "with", "this", "that", "my", "your", "me", "i", "it", "do", "not",
    "be", "has", "have", "was", "were", "will", "can", "should", "would",
    "but", "if", "on", "at", "by", "from", "as", "no", "so", "up",
})


def _tokenize_for_overlap(text: str) -> set[str]:
    """Lowercase, split on whitespace/punctuation, remove stopwords and short tokens."""
    tokens = set(re.split(r"[\s/:\-_.,;!?()\"'`]+", text.lower()))
    return {t for t in tokens if len(t) > 2 and t not in STOPWORDS}


def check_skill_name_leaks(
    skill_name: str,
    triggers: dict[str, Any],
) -> list[dict[str, str]]:
    """Find prompts that contain /rb: prefixes or the target skill name literally."""
    flags: list[dict[str, str]] = []

    for bucket in PROMPT_BUCKETS:
        for item in triggers.get(bucket, []):
            prompt = _extract_prompt(item)
            if not prompt:
                continue

            # Check for /rb: prefix anywhere in prompt
            if "/rb:" in prompt.lower():
                flags.append({
                    "type": "skill_name_leak",
                    "prompt": prompt,
                    "category": bucket,
                    "reason": "contains /rb: prefix",
                })
                continue

            # Check for explicit skill name references in should_trigger.
            # Only flag multi-word skill names (e.g., "active-record-patterns")
            # or command-style references (e.g., "rb:plan"). Single common words
            # like "plan", "review", "work" appear naturally and are not contamination.
            if bucket in ("should_trigger", "hard_should_trigger"):
                prompt_lower = prompt.lower()
                # Flag rb:skillname references (without leading /)
                if f"rb:{skill_name}" in prompt_lower:
                    flags.append({
                        "type": "skill_name_leak",
                        "prompt": prompt,
                        "category": bucket,
                        "reason": f"contains command reference 'rb:{skill_name}'",
                    })
                # Flag multi-word skill names (contain hyphen) as whole-word matches
                elif "-" in skill_name:
                    pattern = r"\b" + re.escape(skill_name.lower()) + r"\b"
                    if re.search(pattern, prompt_lower):
                        flags.append({
                            "type": "skill_name_leak",
                            "prompt": prompt,
                            "category": bucket,
                            "reason": f"contains multi-word skill name '{skill_name}'",
                        })

    return flags


def check_description_echo(
    _skill_name: str,
    description: str,
    triggers: dict[str, Any],
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Find should_not_trigger prompts that share too many keywords with the description."""
    flags: list[dict[str, Any]] = []
    desc_tokens = _tokenize_for_overlap(description)
    if not desc_tokens:
        return flags

    for bucket in ("should_not_trigger", "hard_should_not_trigger"):
        for idx, item in enumerate(triggers.get(bucket, [])):
            prompt = _extract_prompt(item)
            if not prompt:
                continue
            prompt_tokens = _tokenize_for_overlap(prompt)
            shared = desc_tokens & prompt_tokens
            ratio = len(shared) / len(desc_tokens) if desc_tokens else 0.0
            if ratio > threshold:
                flags.append({
                    "type": "description_echo",
                    "prompt": prompt,
                    "category": bucket,
                    "index": idx,
                    "overlap_ratio": round(ratio, 3),
                    "shared_tokens": sorted(shared),
                    "reason": f"{ratio:.1%} overlap with skill description",
                })

    return flags


def check_hard_corpus_quality(triggers: dict[str, Any]) -> list[dict[str, str]]:
    """Verify hard tier entries exist and have basic quality markers."""
    flags: list[dict[str, str]] = []

    hard_pos = triggers.get("hard_should_trigger", [])
    hard_neg = triggers.get("hard_should_not_trigger", [])

    if len(hard_pos) < 2:
        flags.append({
            "type": "hard_corpus_missing",
            "reason": f"only {len(hard_pos)} hard_should_trigger entries (need >= 2)",
        })

    if len(hard_neg) < 2:
        flags.append({
            "type": "hard_corpus_missing",
            "reason": f"only {len(hard_neg)} hard_should_not_trigger entries (need >= 2)",
        })

    # Check that hard entries have axis annotations
    for bucket_name, items in [("hard_should_trigger", hard_pos), ("hard_should_not_trigger", hard_neg)]:
        for idx, item in enumerate(items):
            if isinstance(item, dict) and not item.get("axis"):
                flags.append({
                    "type": "hard_corpus_quality",
                    "reason": f"{bucket_name}[{idx}] missing axis annotation",
                })

    return flags


def score_skill(
    skill_name: str,
    all_descriptions: dict[str, str],
) -> dict[str, Any]:
    """Score one skill for contamination. Returns dict with contamination_score and flags."""
    triggers = load_trigger_file(skill_name)
    if not triggers:
        return {
            "skill": skill_name,
            "contamination_score": 0.0,
            "flags": [],
            "error": "no trigger file",
        }

    description = all_descriptions.get(skill_name, "")

    flags: list[dict[str, Any]] = []
    flags.extend(check_skill_name_leaks(skill_name, triggers))
    flags.extend(check_description_echo(skill_name, description, triggers))
    flags.extend(check_hard_corpus_quality(triggers))

    # Compute contamination score: 0 = clean, 1 = fully contaminated
    # Weight: name leaks are severe, description echo moderate, hard corpus minor
    total_prompts = sum(len(triggers.get(b, [])) for b in PROMPT_BUCKETS)
    if total_prompts == 0:
        contamination = 0.0
    else:
        leak_count = sum(1 for f in flags if f["type"] == "skill_name_leak")
        echo_count = sum(1 for f in flags if f["type"] == "description_echo")
        quality_count = sum(1 for f in flags if f["type"] in ("hard_corpus_missing", "hard_corpus_quality"))

        # Leaks and echoes are prompt-level, quality is structural
        prompt_issues = leak_count * 1.0 + echo_count * 0.5
        structural_issues = min(quality_count * 0.1, 0.3)
        contamination = min(prompt_issues / total_prompts + structural_issues, 1.0)

    return {
        "skill": skill_name,
        "contamination_score": round(contamination, 4),
        "flags": flags,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan trigger corpora for contamination")
    parser.add_argument("--all", action="store_true", help="Scan all skills")
    parser.add_argument("--skill", help="Scan a single skill")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    descriptions = load_all_descriptions()

    if args.skill:
        result = score_skill(args.skill, descriptions)
        if args.summary:
            if result.get("flags"):
                flag_summary = ", ".join(
                    f'{f["type"]}' for f in result["flags"][:3]
                )
                print(f"  {args.skill}: {flag_summary}")
            else:
                print(f"  {args.skill}: clean")
        else:
            print(json.dumps(result, indent=2 if args.pretty else None))
        return

    if args.all:
        clean = []
        flagged = []

        for path in sorted(TRIGGERS_DIR.glob("*.json")):
            if path.name.startswith("_"):
                continue
            name = path.stem
            result = score_skill(name, descriptions)
            if result.get("flags"):
                flagged.append(result)
            else:
                clean.append(name)

        total = len(clean) + len(flagged)

        if args.summary:
            print(f"Hygiene scan: {total} skills")
            print(f"  Clean: {len(clean)} skills")
            print(f"  Flagged: {len(flagged)} skills")
            for result in flagged:
                # Group flags by type for concise display
                type_counts: dict[str, list[str]] = {}
                for flag in result["flags"]:
                    ftype = flag["type"]
                    reason = flag.get("reason", "")
                    if ftype not in type_counts:
                        type_counts[ftype] = []
                    type_counts[ftype].append(reason)
                parts = []
                for ftype, reasons in type_counts.items():
                    parts.append(f"{ftype} ({reasons[0]})")
                print(f"    {result['skill']}: {', '.join(parts)}")
        else:
            all_results = {r["skill"]: r for r in flagged}
            for name in clean:
                all_results[name] = {"skill": name, "contamination_score": 0.0, "flags": []}
            output = {
                "total": total,
                "clean": len(clean),
                "flagged": len(flagged),
                "skills": {k: all_results[k] for k in sorted(all_results)},
            }
            print(json.dumps(output, indent=2 if args.pretty else None))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
