"""Behavioral trigger evaluation using haiku.

Tests whether Claude routes user prompts to the correct skill
by sending all skill descriptions + one test prompt to haiku.

Usage:
    python3 -m lab.eval.behavioral_scorer --skill plan       # Test one skill
    python3 -m lab.eval.behavioral_scorer --all               # Test all skills with triggers
    python3 -m lab.eval.behavioral_scorer --all --cache       # Cache-only, skip stale/missing (no API calls)
    python3 -m lab.eval.behavioral_scorer --all --summary     # Summary only

Cost: Uses --bare mode to minimize per-call overhead.
Observed: ~$10 for full 51-skill run without --bare, expected ~$1-2 with --bare.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from .trigger_scorer import load_all_descriptions, load_trigger_file, TRIGGERS_DIR


RESULTS_DIR = TRIGGERS_DIR / "results"

_ROUTING_SYSTEM_PROMPT = (
    "You are a skill router. Given a list of skills and a user message, "
    "reply with ONLY the skill name(s) that should be loaded, one per line. "
    "If none, reply with the single word 'none'. List at most 3, ordered by relevance. "
    "NEVER add explanations, code examples, or commentary. Output ONLY skill names or 'none'."
)


def content_hash(skill_name: str, descriptions: dict[str, str]) -> str:
    """Hash skill description + trigger corpus for cache invalidation."""
    desc = descriptions.get(skill_name, "")
    trigger_data = load_trigger_file(skill_name)
    corpus = json.dumps(trigger_data, sort_keys=True) if trigger_data else ""
    combined = f"{desc}\n---\n{corpus}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def build_routing_prompt(descriptions: dict[str, str], user_prompt: str) -> str:
    """Build the routing prompt for haiku.

    System-level instructions are in _ROUTING_SYSTEM_PROMPT (passed via --system-prompt).
    This function builds only the user-turn content: skill list + user message.
    """
    desc_list = "\n".join(
        f"- {name}: {desc[:150]}" for name, desc in sorted(descriptions.items())
    )
    return (
        f"Available skills:\n{desc_list}\n\n"
        f'The user says: "{user_prompt}"'
    )

# Cost tracking accumulators (reset per main() run)
_total_cost: float = 0.0
_max_call_cost: float = 0.0
_total_calls: int = 0


def run_haiku(prompt: str, verbose: bool = False) -> list[str] | None:
    """Ask haiku which skill(s) to route to. Returns skill names, or None on failure."""
    global _total_cost, _max_call_cost, _total_calls
    settings_path = str(TRIGGERS_DIR.parent / "bare_settings.json")
    try:
        result = subprocess.run(
            [
                "claude", "--bare",
                "--settings", settings_path,
                "-p", "-",
                "--model", "haiku",
                "--system-prompt", _ROUTING_SYSTEM_PROMPT,
                "--tools", "",
                "--max-turns", "1",
                "--output-format", "json",
                "--max-budget-usd", "0.10",
                "--no-session-persistence",
            ],
            input=prompt,
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            if verbose:
                print(f"--- RESPONSE (rc={result.returncode}) ---", file=sys.stderr)
                print(result.stdout.strip()[:200] or "(empty)", file=sys.stderr)
                if result.stderr.strip():
                    print(f"STDERR: {result.stderr.strip()[:200]}", file=sys.stderr)
                print("--- END RESPONSE ---", file=sys.stderr)
            return None

        # Parse JSON response
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            if verbose:
                print("ERROR: could not parse JSON response", file=sys.stderr)
            return None

        text = data.get("result", "")
        cost = data.get("total_cost_usd", 0)
        _total_calls += 1
        _total_cost += cost
        if cost > _max_call_cost:
            _max_call_cost = cost
        if verbose:
            usage = data.get("usage", {})
            in_tok = usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
            out_tok = usage.get("output_tokens", 0)
            print(f"--- RESPONSE (${cost:.4f}, {in_tok}in/{out_tok}out) ---", file=sys.stderr)
            print(text.strip() or "(empty)", file=sys.stderr)
            print("--- END RESPONSE ---", file=sys.stderr)

        skills = []
        for line in text.strip().split("\n"):
            line = line.strip().lstrip("-*0123456789.) ").strip()
            if " — " in line:
                line = line.split(" — ")[0].strip()
            if " (" in line:
                line = line.split(" (")[0].strip()
            if " -" in line:
                line = line.split(" -")[0].strip()
            line = line.strip("`").strip()
            if line and line.lower() != "none" and not line.startswith("No "):
                skills.append(line)
        return skills

    except subprocess.TimeoutExpired:
        if verbose:
            print("TIMEOUT after 60s", file=sys.stderr)
        return None
    except Exception as exc:
        if verbose:
            print(f"ERROR: {exc}", file=sys.stderr)
        return None


def extract_prompt(item) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("prompt", "")).strip()
    return ""


def _extract_prompt_meta(item) -> dict:
    """Extract prompt text and optional routing metadata from a trigger item."""
    if isinstance(item, str):
        return {"prompt": item.strip(), "routing": None, "valid_skills": []}
    if isinstance(item, dict):
        return {
            "prompt": str(item.get("prompt", "")).strip(),
            "routing": item.get("routing"),
            "valid_skills": item.get("valid_skills", []),
        }
    return {"prompt": "", "routing": None, "valid_skills": []}


def _check_correct(skill_name: str, chosen: list[str], expected: bool,
                   routing: str | None, valid_skills: list[str]) -> bool:
    """Single source of truth for per-prompt correctness."""
    if not expected:
        return skill_name not in chosen
    if routing == "fork" and valid_skills:
        return any(s in chosen for s in valid_skills)
    return skill_name in chosen


def _run_prompt_batch(
    skill_name: str,
    items: list,
    descriptions: dict[str, str],
    expected: bool,
    tier: str,
    verbose: bool = False,
) -> tuple[list[dict], int]:
    """Run a batch of prompt items and return (results, failure_count)."""
    results = []
    failures = 0
    label = "should_trigger" if expected else "should_not"
    for i, item in enumerate(items, 1):
        meta = _extract_prompt_meta(item)
        prompt = meta["prompt"]
        if not prompt:
            continue
        if verbose:
            routing = meta["routing"]
            routing_tag = f" [{routing}]" if routing and routing != "lock" else ""
            print(f"  [{skill_name} {label}({tier}){routing_tag} {i}/{len(items)}] {prompt}", file=sys.stderr)
        full_prompt = build_routing_prompt(descriptions, prompt)
        chosen = run_haiku(full_prompt, verbose=verbose)
        if chosen is None:
            failures += 1
            if verbose:
                print("  -> SKIPPED (haiku call failed)", file=sys.stderr)
            continue
        correct = _check_correct(
            skill_name, chosen, expected, meta["routing"], meta["valid_skills"]
        )
        if verbose:
            status = "OK" if correct else ("MISS" if expected else "FALSE_POS")
            print(f"  -> chosen={chosen} [{status}]", file=sys.stderr)
        results.append({
            "prompt": prompt,
            "expected": expected,
            "chosen": chosen,
            "correct": correct,
            "tier": tier,
            "routing": meta["routing"],
        })
    return results, failures


def _compute_metrics(results: list[dict]) -> dict:
    """Compute accuracy/precision/recall from a list of result dicts."""
    total = len(results)
    if total == 0:
        return {"accuracy": 0.0, "precision": 1.0, "recall": 1.0, "total": 0, "correct": 0}
    correct_count = sum(1 for r in results if r["correct"])
    tp = sum(1 for r in results if r["expected"] and r["correct"])
    fp = sum(1 for r in results if not r["expected"] and not r["correct"])
    fn = sum(1 for r in results if r["expected"] and not r["correct"])
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    accuracy = correct_count / total if total > 0 else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "total": total,
        "correct": correct_count,
        "tp": tp, "fp": fp, "fn": fn,
    }


def score_skill(
    skill_name: str,
    descriptions: dict[str, str],
    use_cache: bool = False,
    verbose: bool = False,
    limit: int = 0,
) -> dict:
    """Score trigger accuracy for one skill. Returns precision/recall/accuracy with tier split."""
    cache_path = RESULTS_DIR / f"{skill_name}.json"

    if use_cache:
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {"skill": skill_name, "error": "corrupted cache file"}
            expected_hash = content_hash(skill_name, descriptions)
            if cached.get("content_hash") == expected_hash:
                return cached
        # --cache is cache-only: skip skills without valid cache
        return {"skill": skill_name, "error": "no valid cache (stale or missing)"}

    triggers = load_trigger_file(skill_name)
    if not triggers:
        return {"skill": skill_name, "error": "no trigger file"}

    # Easy tier: should_trigger + should_not_trigger (raw items, may be str or dict)
    easy_trigger = triggers.get("should_trigger", [])
    easy_not = triggers.get("should_not_trigger", [])
    # Hard tier: hard_should_trigger + hard_should_not_trigger (may have routing/valid_skills)
    hard_trigger = triggers.get("hard_should_trigger", [])
    hard_not = triggers.get("hard_should_not_trigger", [])

    if limit > 0:
        easy_trigger = easy_trigger[:limit]
        easy_not = easy_not[:limit]
        hard_trigger = hard_trigger[:limit]
        hard_not = hard_not[:limit]

    all_results = []
    total_failures = 0

    for items, expected, tier in [
        (easy_trigger, True, "easy"),
        (easy_not, False, "easy"),
        (hard_trigger, True, "hard"),
        (hard_not, False, "hard"),
    ]:
        results, failures = _run_prompt_batch(
            skill_name, items, descriptions, expected, tier, verbose
        )
        all_results.extend(results)
        total_failures += failures

    if not all_results and total_failures > 0:
        return {"skill": skill_name, "error": f"all {total_failures} haiku calls failed"}

    # Overall metrics
    overall = _compute_metrics(all_results)

    # Tier-split metrics
    easy_results = [r for r in all_results if r.get("tier") == "easy"]
    hard_results = [r for r in all_results if r.get("tier") == "hard"]
    easy_metrics = _compute_metrics(easy_results)
    hard_metrics = _compute_metrics(hard_results)

    # Fork/lock metrics — only from explicitly annotated prompts (routing != None)
    fork_results = [r for r in all_results if r.get("routing") == "fork"]
    lock_results = [r for r in all_results if r.get("routing") == "lock"]
    fork_metrics = _compute_metrics(fork_results)
    lock_metrics = _compute_metrics(lock_results)

    score_data = {
        "skill": skill_name,
        **overall,
        "failures": total_failures,
        "easy_accuracy": easy_metrics["accuracy"],
        "easy_precision": easy_metrics["precision"],
        "easy_recall": easy_metrics["recall"],
        "hard_accuracy": hard_metrics["accuracy"],
        "hard_precision": hard_metrics["precision"],
        "hard_recall": hard_metrics["recall"],
        "fork_accuracy": fork_metrics["accuracy"],
        "lock_accuracy": lock_metrics["accuracy"],
        "tier_counts": {"easy": easy_metrics["total"], "hard": hard_metrics["total"]},
        "routing_counts": {"fork": fork_metrics["total"], "lock": lock_metrics["total"]},
        "content_hash": content_hash(skill_name, descriptions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": all_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(score_data, indent=2) + "\n", encoding="utf-8")

    return score_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Test skill trigger accuracy with haiku")
    parser.add_argument("--skill", help="Test one skill")
    parser.add_argument("--all", action="store_true", help="Test all skills with trigger files")
    parser.add_argument("--cache", action="store_true", help="Cache-only: use cached results, skip stale/missing (no API calls)")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--verbose", action="store_true", help="Show prompt/response for each API call")
    parser.add_argument("--limit", type=int, default=0, metavar="N",
                        help="Test only first N should_trigger + N should_not_trigger prompts per skill")
    args = parser.parse_args()

    descriptions = load_all_descriptions()

    global _total_cost, _max_call_cost, _total_calls
    _total_cost = 0.0
    _max_call_cost = 0.0
    _total_calls = 0

    if args.skill:
        result = score_skill(args.skill, descriptions, args.cache,
                             verbose=args.verbose, limit=args.limit)
        if args.summary:
            tier_str = ""
            tc = result.get("tier_counts", {})
            if tc.get("hard", 0) > 0:
                tier_str = (f" (easy: {result.get('easy_accuracy', 0):.0%}, "
                            f"hard: {result.get('hard_accuracy', 0):.0%})")
            print(f"{args.skill}: accuracy={result.get('accuracy', 0):.0%}{tier_str} "
                  f"precision={result.get('precision', 0):.0%} "
                  f"recall={result.get('recall', 0):.0%}")
        else:
            print(json.dumps(result, indent=2 if args.pretty else None))

    elif args.all:
        skills_tested = 0
        total_accuracy = 0.0
        all_results = {}

        for name in sorted(descriptions.keys()):
            triggers = load_trigger_file(name)
            if not triggers:
                continue
            print(f"  Testing {name}...", end="\n" if args.verbose else " ", flush=True, file=sys.stderr)
            result = score_skill(name, descriptions, args.cache,
                                 verbose=args.verbose, limit=args.limit)
            if "error" in result:
                print(f"SKIPPED ({result['error']})", file=sys.stderr)
                continue
            all_results[name] = result
            total_accuracy += result.get("accuracy", 0)
            skills_tested += 1
            print(
                f"accuracy={result.get('accuracy', 0):.0%} "
                f"(P={result.get('precision', 0):.0%} "
                f"R={result.get('recall', 0):.0%})",
                file=sys.stderr,
            )

        avg = total_accuracy / skills_tested if skills_tested else 0
        print(f"\n{skills_tested} skills tested, average accuracy: {avg:.0%}", file=sys.stderr)

        if args.summary:
            for name, result in sorted(all_results.items()):
                tier_str = ""
                tc = result.get("tier_counts", {})
                if tc.get("hard", 0) > 0:
                    tier_str = (f" (easy: {result.get('easy_accuracy', 0):.0%}, "
                                f"hard: {result.get('hard_accuracy', 0):.0%})")
                print(f"  {name}: accuracy={result.get('accuracy', 0):.0%}{tier_str} "
                      f"P={result.get('precision', 0):.0%} "
                      f"R={result.get('recall', 0):.0%}")
        else:
            aggregate = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "skills_tested": skills_tested,
                "average_accuracy": round(avg, 4),
                "per_skill": {
                    k: {
                        "accuracy": v.get("accuracy", 0),
                        "precision": v.get("precision", 0),
                        "recall": v.get("recall", 0),
                    }
                    for k, v in all_results.items()
                },
            }
            aggregate_path = RESULTS_DIR / "_aggregate.json"
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            aggregate_path.write_text(
                json.dumps(aggregate, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(aggregate, indent=2 if args.pretty else None))

    else:
        parser.print_help()
        return

    # Cost summary (always printed to stderr when API calls were made)
    if _total_calls > 0:
        avg_cost = _total_cost / _total_calls
        print(f"\n--- Cost Summary ---", file=sys.stderr)
        print(f"  Total API calls: {_total_calls}", file=sys.stderr)
        print(f"  Total cost:      ${_total_cost:.4f}", file=sys.stderr)
        print(f"  Max single call: ${_max_call_cost:.4f}", file=sys.stderr)
        print(f"  Avg per call:    ${avg_cost:.4f}", file=sys.stderr)
        print(f"--------------------", file=sys.stderr)


if __name__ == "__main__":
    main()
