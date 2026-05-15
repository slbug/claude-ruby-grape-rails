"""Validate and analyze deterministic trigger corpora."""


import argparse
import json
import sys
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


def load_hidden_skills() -> set[str]:
    """Skills with `disable-model-invocation: true` are excluded from NL routing.

    Trigger fixtures measure whether NL routing picks the right skill;
    fixtures for hidden skills score routing the runtime cannot perform.
    """
    hidden: set[str] = set()
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        fm = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
        if isinstance(fm, dict) and fm.get("disable-model-invocation") is True:
            hidden.add(skill_dir.name)
    return hidden


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
    """Load the single ``description`` routing field per agentskills.io canon.

    Returns a dict-of-dicts shape (one key per skill, holding a single
    ``description`` entry) for downstream callers that consume the structured
    routing-field map rather than the flat string returned by
    :func:`load_descriptions`.
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
        }
    return descriptions


def routing_description_text(value: RoutingDescription) -> str:
    """Return the routing description text from a string or routing-field dict."""
    if isinstance(value, Mapping):
        return str(value.get("description", "")).strip()
    return str(value).strip()


def routing_text_sources(value: RoutingDescription) -> list[tuple[str, str]]:
    """Return the routing description as a (field_name, text) pair.

    Used by hygiene + corpus-quality gates to check the routing field
    independently (e.g., description echo detection).
    """
    if isinstance(value, Mapping):
        desc = str(value.get("description", "")).strip()
        return [("description", desc)] if desc else []
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


_SEMANTIC_CACHE_PATH = TRIGGERS_DIR / "_semantic_pairs.json"

_SEMANTIC_SYSTEM_PROMPT = (
    "You identify semantically confusable skill pairs. Reply with ONLY "
    "pipe-separated lines in this exact format: skill-a | skill-b | 7 | "
    "brief reason. Include a numeric confusability score (1-10) and a short "
    "reason on every line. NEVER add headers, numbering, or explanations."
)


def _fetch_semantic_pairs(
    descriptions: RoutingDescriptions,
    token_pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Call Ollama once to identify additional semantically-confusable pairs.

    Token-overlap pairs from `build_confusable_pairs` catch lexical
    similarity; this asks the model to surface pairs that overlap by
    meaning even when they share few tokens. Returns a list of pair
    dicts with keys: left, right, score, reason, source.
    """
    from .behavioral_scorer import ollama_chat

    desc_lines = "\n".join(
        f"- {name}: {routing_description_text(desc)[:150]}"
        for name, desc in sorted(descriptions.items())
    )
    token_lines = "\n".join(
        f"- {p['left']} | {p['right']} (overlap={p.get('overlap')})"
        for p in token_pairs[:15]
    )
    user_prompt = (
        f"Skills:\n{desc_lines}\n\n"
        f"Already-found token-overlap pairs (deprioritize, do not repeat):\n{token_lines}\n\n"
        "Name 10-15 additional skill pairs that are SEMANTICALLY confusable "
        "(a user prompt could reasonably route to either skill) but were NOT "
        "in the list above. Rate each pair 1-10 for confusability.\n\n"
        "Reply ONLY in this format, one per line:\n"
        "skill-a | skill-b | 7 | both handle database queries"
    )

    try:
        text = ollama_chat(
            _SEMANTIC_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=512,
            reasoning_effort="none",
        )
    except Exception as exc:
        print(f"WARNING: semantic pairs call failed ({exc})", file=sys.stderr)
        return []

    pairs: list[dict[str, Any]] = []
    skill_names = set(descriptions.keys())
    for raw in text.split("\n"):
        line = raw.strip().lstrip("-*0123456789.) ").strip()
        if not line or "|" not in line:
            continue
        parts = [seg.strip() for seg in line.split("|")]
        if len(parts) < 2:
            continue
        left, right = parts[0], parts[1]
        if left not in skill_names or right not in skill_names or left == right:
            continue
        # Score on 1-10 from the prompt → normalize to 0-1 for parity with
        # token-overlap pairs. Default 0.5 on malformed score (incl. fractions
        # like "8/10" or words like "high").
        overlap = 0.5
        if len(parts) >= 3:
            raw_score = parts[2]
            if "/" in raw_score:
                raw_score = raw_score.split("/", 1)[0].strip()
            try:
                overlap = max(1.0, min(10.0, float(raw_score))) / 10.0
            except ValueError:
                overlap = 0.5
        reason = " | ".join(parts[3:]) if len(parts) > 3 else ""
        ordered = tuple(sorted((left, right)))
        pairs.append({
            "left": ordered[0],
            "right": ordered[1],
            "overlap": round(overlap, 4),
            "reason": reason,
            "source": "semantic",
        })
    return pairs


_MERGED_PAIR_LIMIT = 15


def _normalize_pair(p: dict[str, Any]) -> tuple[str, str]:
    """Return a canonical ordered key for a pair (alphabetical)."""
    return tuple(sorted((p["left"], p["right"])))


def _merge_pairs(
    token_pairs: list[dict[str, Any]],
    semantic_pairs: list[dict[str, Any]],
    desc_hash: str,
) -> list[dict[str, Any]]:
    """Merge token-overlap and semantic pairs. Cache semantic pairs.

    - Canonical ordering: (left, right) is sorted alphabetically before
      dedup so the same pair surfacing in either order collapses.
    - Token pairs win on duplicates so their `overlap` is preserved.
    - Result is sorted by `overlap` descending and capped at
      ``_MERGED_PAIR_LIMIT`` (15) — the cap the trigger-reviewer UI
      depends on.
    - Cache is written only when fresh_semantic is non-empty so transient
      Ollama failures don't clobber previously-good cached pairs.
    """
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    for p in token_pairs:
        key = _normalize_pair(p)
        if key in seen:
            continue
        seen.add(key)
        merged.append({**p, "left": key[0], "right": key[1]})
    fresh_semantic: list[dict[str, Any]] = []
    for p in semantic_pairs:
        key = _normalize_pair(p)
        if key in seen:
            continue
        seen.add(key)
        merged.append({**p, "left": key[0], "right": key[1]})
        fresh_semantic.append(p)

    merged.sort(key=lambda r: -(r.get("overlap") or 0.0))
    merged = merged[:_MERGED_PAIR_LIMIT]

    # Skip cache write when fresh_semantic is empty — preserves
    # previously-cached pairs on a transient Ollama failure rather than
    # clobbering them with an empty list.
    if fresh_semantic:
        try:
            _SEMANTIC_CACHE_PATH.write_text(
                json.dumps(
                    {"desc_hash": desc_hash, "pairs": fresh_semantic},
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"WARNING: failed to write semantic pair cache ({exc})", file=sys.stderr)

    return merged


def build_semantic_confusable_pairs(
    descriptions: RoutingDescriptions,
    token_pairs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build merged token + semantic confusable pairs via a single Ollama call.

    Caches semantic pairs in `_semantic_pairs.json` keyed by description
    content hash; cached pairs are reused until any description changes.
    Ollama is currently the only wired provider — future providers plug
    in through `behavioral_scorer.ollama_chat`'s sibling helpers.
    """
    desc_hash = _descriptions_hash(descriptions)
    if token_pairs is None:
        token_pairs = build_confusable_pairs(descriptions)
    cached: list[dict[str, Any]] = []
    cache_hit = False
    if _SEMANTIC_CACHE_PATH.is_file():
        try:
            data = json.loads(_SEMANTIC_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("desc_hash") == desc_hash:
                cached = data.get("pairs") or []
                cache_hit = True
        except (json.JSONDecodeError, OSError):
            cached = []
    semantic = cached if cache_hit else _fetch_semantic_pairs(descriptions, token_pairs)
    return _merge_pairs(token_pairs, semantic, desc_hash)


def score_all(semantic: bool = False) -> dict[str, Any]:
    hidden = load_hidden_skills()
    descriptions = {
        name: desc
        for name, desc in load_all_routing_descriptions().items()
        if name not in hidden
    }
    scores = {}
    for path in sorted(TRIGGERS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        if path.stem in hidden:
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
        "hidden_skills_excluded": sorted(hidden),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Ruby plugin trigger corpora")
    parser.add_argument("--all", action="store_true", help="Score all trigger files")
    parser.add_argument("--skill", help="Score a single skill trigger file")
    parser.add_argument("--overlap", action="store_true", help="Print confusable pairs only")
    parser.add_argument("--semantic", action="store_true", help="Include Ollama-rated semantic pairs (one local call)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    if args.overlap:
        hidden = load_hidden_skills()
        descriptions = {
            name: desc
            for name, desc in load_all_routing_descriptions().items()
            if name not in hidden
        }
        pairs = (
            build_semantic_confusable_pairs(descriptions)
            if args.semantic
            else build_confusable_pairs(descriptions)
        )
        print(json.dumps(pairs, indent=2 if args.pretty else None))
        return

    if args.skill:
        if args.skill in load_hidden_skills():
            raise SystemExit(f"skill {args.skill} is hidden (disable-model-invocation: true); trigger scoring not applicable")
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
