"""Validate and analyze deterministic trigger corpora."""


import argparse
import json
from collections.abc import Mapping
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

RoutingDescription = str | Mapping[str, Any]
RoutingDescriptions = Mapping[str, RoutingDescription]


def extract_prompt(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("prompt", "")).strip()
    return ""


def normalize_prompt(prompt: str) -> str:
    return " ".join(sorted(tokenize(prompt)))


def load_all_descriptions() -> dict[str, str]:
    """Load top-level skill descriptions only."""
    descriptions: dict[str, str] = {}
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        fm = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        descriptions[skill_dir.name] = str(fm.get("description", ""))
    return descriptions


def load_all_routing_descriptions() -> dict[str, dict[str, str]]:
    """Load routing text fields used by LLM-based skill routing.

    ``description`` explains broad intent; ``when_to_use`` carries trigger
    phrases and negative routing notes. Behavioral and confusable-pair evals
    need both to match the real routing surface.
    """
    descriptions: dict[str, dict[str, str]] = {}
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        fm = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        descriptions[skill_dir.name] = {
            "description": str(fm.get("description", "")).strip(),
            "when_to_use": str(fm.get("when_to_use", "")).strip(),
        }
    return descriptions


def routing_description_text(value: RoutingDescription) -> str:
    """Return full routing text from a description string or routing-field dict."""
    if isinstance(value, Mapping):
        desc = str(value.get("description", "")).strip()
        when = str(value.get("when_to_use", "")).strip()
        if desc and when:
            return f"{desc} When to use: {when}"
        return desc or when
    return str(value).strip()


def routing_text_sources(value: RoutingDescription) -> list[tuple[str, str]]:
    """Return individual routing text fields as (field_name, text) pairs.

    Used by hygiene and trigger_expand quality gates to check each routing
    field independently (e.g., description echo detection).
    """
    if isinstance(value, Mapping):
        sources: list[tuple[str, str]] = []
        desc = str(value.get("description", "")).strip()
        when = str(value.get("when_to_use", "")).strip()
        if desc:
            sources.append(("description", desc))
        if when:
            sources.append(("when_to_use", when))
        return sources
    text = str(value).strip()
    return [("description", text)] if text else []


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
            prompt = extract_prompt(item)
            if prompt:
                all_prompts.append((bucket, prompt))

    duplicate_count = len(all_prompts) - len({normalize_prompt(prompt) for _, prompt in all_prompts})
    hard_axes = sorted({item.get("axis", "") for item in hard_positive if isinstance(item, dict) and item.get("axis")})

    # Fork/lock routing validation — only for hard positives (routing is
    # meaningful only for prompts expected to trigger a skill)
    hard_positive_dicts = [item for item in hard_positive if isinstance(item, dict)]
    fork_count = sum(1 for item in hard_positive_dicts if item.get("routing") == "fork")
    lock_count = sum(1 for item in hard_positive_dicts if item.get("routing") == "lock")
    has_routing = fork_count > 0 or lock_count > 0

    # Validate fork prompts have valid_skills (hard positives only)
    fork_missing_valid = [
        extract_prompt(item) for item in hard_positive_dicts
        if item.get("routing") == "fork" and not item.get("valid_skills")
    ]

    checks = [
        ("has_positive_prompts", len(positive) >= 4, f"{len(positive)} standard positives"),
        ("has_negative_prompts", len(negative) >= 4, f"{len(negative)} standard negatives"),
        ("has_hard_prompts", len(hard_positive) >= 2 and len(hard_negative) >= 2, f"{len(hard_positive)} hard positives / {len(hard_negative)} hard negatives"),
        ("no_duplicates", duplicate_count == 0, f"{duplicate_count} duplicate normalized prompts"),
        ("axis_diversity", len(hard_axes) >= 2, f"hard axes={hard_axes}"),
        ("fork_valid_skills", len(fork_missing_valid) == 0,
         f"fork prompts without valid_skills: {len(fork_missing_valid)}" if fork_missing_valid
         else "all fork prompts have valid_skills (or no fork prompts)"),
    ]

    # has_fork_lock_mix is advisory — reported but not scored
    advisory_checks = []
    if has_routing:
        advisory_checks.append(
            ("has_fork_lock_mix", fork_count > 0 and lock_count > 0,
             f"fork={fork_count}, lock={lock_count} (advisory, not scored)")
        )

    for check_type, passed, evidence in checks:
        assertions.append({"type": check_type, "passed": passed, "evidence": evidence})
    for check_type, passed, evidence in advisory_checks:
        assertions.append({"type": check_type, "passed": passed, "evidence": evidence, "advisory": True})

    scored = [item for item in assertions if not item.get("advisory")]
    score = sum(1 for item in scored if item["passed"]) / len(scored) if scored else 0.0
    return {
        "skill": skill_name,
        "score": round(score, 4),
        "assertions": assertions,
        "prompt_counts": {bucket: len(data.get(bucket, [])) for bucket in PROMPT_BUCKETS},
    }


def build_confusable_pairs(
    descriptions: RoutingDescriptions,
    limit: int = 10,
) -> list[dict[str, Any]]:
    bundle: dict[str, set[str]] = {}
    for skill, desc in descriptions.items():
        data = load_trigger_file(skill)
        if data is None:
            continue
        tokens = set(tokenize(routing_description_text(desc)))
        for bucket in ("should_trigger", "hard_should_trigger"):
            for item in data.get(bucket, []):
                tokens.update(tokenize(extract_prompt(item)))
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


_SEMANTIC_CACHE_PATH = TRIGGERS_DIR / "_semantic_pairs.json"

_SEMANTIC_SYSTEM_PROMPT = (
    "You identify semantically confusable skill pairs. Reply with ONLY "
    "pipe-separated lines in this exact format: skill-a | skill-b | 7 | "
    "brief reason. Include a numeric confusability score (1-10) and a short "
    "reason on every line. NEVER add headers, numbering, or explanations."
)


def routing_descriptions_blob(descriptions: RoutingDescriptions) -> str:
    """Serialize routing descriptions to a stable JSON string.

    Used for cache-key hashing by behavioral_scorer and neighbor_regression.
    """
    return json.dumps(
        {name: routing_description_text(desc) for name, desc in descriptions.items()},
        sort_keys=True,
    )


def _descriptions_hash(descriptions: RoutingDescriptions) -> str:
    """Content hash of all descriptions for semantic pair cache invalidation."""
    import hashlib
    return hashlib.sha256(routing_descriptions_blob(descriptions).encode()).hexdigest()[:16]


def build_semantic_confusable_pairs(
    descriptions: RoutingDescriptions,
    token_pairs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build semantic confusable pairs via a single Haiku call.

    Asks Haiku to identify pairs that are semantically confusable but
    not caught by token overlap. Merges with token_pairs, deduplicates,
    returns top 15.

    Returns cached results if descriptions haven't changed.
    Requires 'claude' CLI — returns empty list if unavailable.
    """
    desc_hash = _descriptions_hash(descriptions)

    if token_pairs is None:
        token_pairs = build_confusable_pairs(descriptions, limit=10)

    # Check cache — stores only semantic additions, not merged token pairs.
    # Token pairs are always recomputed fresh (they depend on trigger corpora).
    cached_semantic: list[dict[str, Any]] = []
    cache_hit = False
    if _SEMANTIC_CACHE_PATH.is_file():
        try:
            cached = json.loads(_SEMANTIC_CACHE_PATH.read_text(encoding="utf-8"))
            if cached.get("descriptions_hash") == desc_hash:
                cached_semantic = cached.get("semantic_pairs", [])
                cache_hit = True
        except (json.JSONDecodeError, OSError):
            pass

    if cache_hit:
        semantic_pairs = cached_semantic
    else:
        semantic_pairs = _fetch_semantic_pairs(descriptions, token_pairs)

    return _merge_pairs(token_pairs, semantic_pairs, desc_hash)


def _fetch_semantic_pairs(
    descriptions: RoutingDescriptions,
    token_pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Call Haiku once to identify semantic confusable pairs."""
    import subprocess, sys

    # Build the prompt
    desc_lines = "\n".join(
        f"- {name}: {routing_description_text(desc)[:150]}"
        for name, desc in sorted(descriptions.items())
    )
    known_lines = "\n".join(
        f"{p['left']} | {p['right']} | {p['overlap']:.2f}"
        for p in token_pairs[:10]
    )
    user_prompt = (
        f"Here are {len(descriptions)} skill descriptions:\n{desc_lines}\n\n"
        f"These pairs were already found by token overlap:\n{known_lines}\n\n"
        "Name 10-15 additional skill pairs that are SEMANTICALLY confusable "
        "(a user prompt could reasonably route to either skill) but were NOT "
        "in the list above. Rate each pair 1-10 for confusability.\n\n"
        "Reply ONLY in this format, one per line:\n"
        "skill-a | skill-b | 7 | both handle database queries"
    )

    from .behavioral_scorer import _resolved_settings_path
    settings_path = _resolved_settings_path

    try:
        result = subprocess.run(
            [
                "claude", "--bare",
                "--settings", settings_path,
                "-p", "-",
                "--model", "haiku",
                "--system-prompt", _SEMANTIC_SYSTEM_PROMPT,
                "--tools", "",
                "--max-turns", "1",
                "--output-format", "json",
                "--max-budget-usd", "0.10",
                "--no-session-persistence",
            ],
            input=user_prompt,
            capture_output=True, text=True, timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"WARNING: semantic pairs call failed ({exc})", file=sys.stderr)
        return []

    if result.returncode != 0:
        print(f"WARNING: semantic pairs call returned rc={result.returncode}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
        text = data.get("result", "")
    except json.JSONDecodeError:
        text = result.stdout

    valid_skills = set(descriptions.keys())
    pairs: list[dict[str, Any]] = []
    for line in text.strip().split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 2:
            continue
        left, right = parts[0], parts[1]
        if left not in valid_skills or right not in valid_skills:
            continue
        if left == right:
            continue
        score = 0.5
        if len(parts) >= 3:
            raw = parts[2].strip()
            if "/" in raw:
                raw = raw.split("/", 1)[0].strip()
            try:
                score = max(1.0, min(10.0, float(raw))) / 10.0
            except ValueError:
                score = 0.5
        reason = " | ".join(parts[3:]) if len(parts) > 3 else ""
        if left > right:
            left, right = right, left
        pairs.append({
            "left": left,
            "right": right,
            "overlap": round(score, 4),
            "source": "semantic",
            "reason": reason,
        })
    return pairs


def _merge_pairs(
    token_pairs: list[dict[str, Any]],
    semantic_pairs: list[dict[str, Any]],
    desc_hash: str,
) -> list[dict[str, Any]]:
    """Merge token-overlap and semantic pairs, deduplicate, cache semantic additions."""
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    for p in (token_pairs or []):
        key = (min(p["left"], p["right"]), max(p["left"], p["right"]))
        if key not in seen:
            seen.add(key)
            merged.append(p)
    for p in semantic_pairs:
        key = (min(p["left"], p["right"]), max(p["left"], p["right"]))
        if key not in seen:
            seen.add(key)
            merged.append(p)

    merged.sort(key=lambda x: (-x["overlap"], x["left"], x["right"]))
    merged = merged[:15]

    # Cache only semantic additions (token pairs change with triggers).
    # Don't clobber existing cache with empty result from a failed fetch.
    if semantic_pairs:
        _SEMANTIC_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _SEMANTIC_CACHE_PATH.write_text(json.dumps({
            "descriptions_hash": desc_hash,
            "semantic_pairs": semantic_pairs,
        }, indent=2) + "\n", encoding="utf-8")

    return merged


def score_all(semantic: bool = False) -> dict[str, Any]:
    descriptions = load_all_routing_descriptions()
    scores = {}
    for path in sorted(TRIGGERS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        scores[path.stem] = score_trigger_file(path.stem, json.loads(path.read_text(encoding="utf-8")))
    token_pairs = build_confusable_pairs(descriptions)
    pairs = (
        build_semantic_confusable_pairs(descriptions, token_pairs)
        if semantic else token_pairs
    )
    return {
        "skills": scores,
        "confusable_pairs": pairs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Ruby plugin trigger corpora")
    parser.add_argument("--all", action="store_true", help="Score all trigger files")
    parser.add_argument("--skill", help="Score a single skill trigger file")
    parser.add_argument("--overlap", action="store_true", help="Print confusable pairs only")
    parser.add_argument("--semantic", action="store_true", help="Include Haiku-rated semantic pairs (one API call)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    if args.overlap:
        descriptions = load_all_routing_descriptions()
        if args.semantic:
            pairs = build_semantic_confusable_pairs(descriptions)
        else:
            pairs = build_confusable_pairs(descriptions)
        print(json.dumps(pairs, indent=2 if args.pretty else None))
        return

    if args.skill:
        data = load_trigger_file(args.skill)
        if data is None:
            raise SystemExit(f"missing trigger file for {args.skill}")
        print(json.dumps(score_trigger_file(args.skill, data), indent=2 if args.pretty else None))
        return

    if args.all:
        print(json.dumps(score_all(semantic=args.semantic), indent=2 if args.pretty else None))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
