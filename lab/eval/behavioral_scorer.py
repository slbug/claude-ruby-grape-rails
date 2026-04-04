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


def score_skill(
    skill_name: str,
    descriptions: dict[str, str],
    use_cache: bool = False,
    verbose: bool = False,
    limit: int = 0,
) -> dict:
    """Score trigger accuracy for one skill. Returns precision/recall/accuracy."""
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

    should_trigger = [extract_prompt(p) for p in triggers.get("should_trigger", [])]
    should_not = [extract_prompt(p) for p in triggers.get("should_not_trigger", [])]

    if limit > 0:
        should_trigger = should_trigger[:limit]
        should_not = should_not[:limit]

    results = []

    failures = 0

    for i, prompt in enumerate(should_trigger, 1):
        if not prompt:
            continue
        if verbose:
            print(f"  [{skill_name} should_trigger {i}/{len(should_trigger)}] {prompt}", file=sys.stderr)
        full_prompt = build_routing_prompt(descriptions, prompt)
        chosen = run_haiku(full_prompt, verbose=verbose)
        if chosen is None:
            failures += 1
            if verbose:
                print("  -> SKIPPED (haiku call failed)", file=sys.stderr)
            continue
        correct = skill_name in chosen
        if verbose:
            status = "OK" if correct else "MISS"
            print(f"  -> chosen={chosen} [{status}]", file=sys.stderr)
        results.append({
            "prompt": prompt,
            "expected": True,
            "chosen": chosen,
            "correct": correct,
        })

    for i, prompt in enumerate(should_not, 1):
        if not prompt:
            continue
        if verbose:
            print(f"  [{skill_name} should_not {i}/{len(should_not)}] {prompt}", file=sys.stderr)
        full_prompt = build_routing_prompt(descriptions, prompt)
        chosen = run_haiku(full_prompt, verbose=verbose)
        if chosen is None:
            failures += 1
            if verbose:
                print("  -> SKIPPED (haiku call failed)", file=sys.stderr)
            continue
        correct = skill_name not in chosen
        if verbose:
            status = "OK" if correct else "FALSE_POS"
            print(f"  -> chosen={chosen} [{status}]", file=sys.stderr)
        results.append({
            "prompt": prompt,
            "expected": False,
            "chosen": chosen,
            "correct": correct,
        })

    if not results and failures > 0:
        return {"skill": skill_name, "error": f"all {failures} haiku calls failed"}

    total = len(results)
    correct_count = sum(1 for r in results if r["correct"])

    tp = sum(1 for r in results if r["expected"] and r["correct"])
    fp = sum(1 for r in results if not r["expected"] and not r["correct"])
    fn = sum(1 for r in results if r["expected"] and not r["correct"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    accuracy = correct_count / total if total > 0 else 0.0

    score_data = {
        "skill": skill_name,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "total": total,
        "correct": correct_count,
        "tp": tp, "fp": fp, "fn": fn,
        "failures": failures,
        "content_hash": content_hash(skill_name, descriptions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
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
            print(f"{args.skill}: accuracy={result.get('accuracy', 0):.0%} "
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
                print(f"  {name}: accuracy={result.get('accuracy', 0):.0%} "
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
