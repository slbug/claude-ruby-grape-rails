"""Self-sampled trigger corpus expansion via Haiku.

Generates candidate trigger prompts with style diversity constraints,
applies quality gates, and writes to candidates/ for manual review.

Never auto-merges into trigger corpora — manual review is a hard gate.

Usage:
    python3 -m lab.eval.trigger_expand --skill plan        # Expand one skill
    python3 -m lab.eval.trigger_expand --fragile            # Expand fragile skills (from eval sensitivity)
    python3 -m lab.eval.trigger_expand --all                # Expand all skills

Cost: ~$0.005/skill (one bare-mode Haiku call per skill).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from .trigger_scorer import (
    TRIGGERS_DIR,
    extract_prompt,
    load_all_descriptions,
    load_trigger_file,
    tokenize,
)


CANDIDATES_DIR = TRIGGERS_DIR / "candidates"

_EXPAND_SYSTEM_PROMPT = (
    "You generate realistic user prompts for testing a skill router. "
    "Reply with ONLY JSON — no markdown fences, no commentary."
)

_STYLE_CONSTRAINTS = """Vary the phrasing style across prompts:
- One as a frustrated developer would type it
- One using only 5-8 words
- One with a typo or abbreviation
- One as a non-native English speaker
- One that's technically precise"""


def _token_overlap(a: str, b: str) -> float:
    """Jaccard token overlap between two strings."""
    ta, tb = set(tokenize(a)), set(tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _quality_gate(
    candidate: str,
    skill_name: str,
    existing_prompts: list[str],
    skill_description: str,
) -> str | None:
    """Returns rejection reason, or None if candidate passes all gates."""
    import re
    if len(candidate) < 10:
        return "too_short"
    if len(candidate) > 500:
        return "too_long"
    # Skill name leak detection — aligned with hygiene.py rules:
    # - /rb: prefixes are always leaks
    # - rb:skillname command references are leaks
    # - Multi-word (hyphenated) skill names as whole-word matches are leaks
    # - Single common words (plan, review, work) appear naturally and are NOT leaks
    prompt_lower = candidate.lower()
    if "/rb:" in prompt_lower:
        return "skill_name_leak"
    if f"rb:{skill_name}" in prompt_lower:
        return "skill_name_leak"
    if "-" in skill_name:
        pattern = r"\b" + re.escape(skill_name.lower()) + r"\b"
        if re.search(pattern, prompt_lower):
            return "skill_name_leak"
    # Description echo: >50% token overlap with description
    if _token_overlap(candidate, skill_description) > 0.50:
        return "description_echo"
    # Near-duplicate: >80% token overlap with any existing prompt
    for existing in existing_prompts:
        if _token_overlap(candidate, existing) > 0.80:
            return "near_duplicate"
    return None


def expand_skill(
    skill_name: str,
    descriptions: dict[str, str],
) -> dict:
    """Generate candidate trigger prompts for one skill.

    Returns dict with candidates and quality gate stats.
    """
    description = descriptions.get(skill_name, "")
    if not description:
        return {"skill": skill_name, "error": "no description found"}

    triggers = load_trigger_file(skill_name)
    existing_prompts = []
    if triggers:
        for bucket in ("should_trigger", "should_not_trigger",
                        "hard_should_trigger", "hard_should_not_trigger"):
            for item in triggers.get(bucket, []):
                p = extract_prompt(item)
                if p:
                    existing_prompts.append(p)

    user_prompt = (
        f"Skill name: {skill_name}\n"
        f"Skill description: {description[:300]}\n\n"
        f"Existing prompts (do NOT duplicate these):\n"
        + "\n".join(f"- {p}" for p in existing_prompts[:20])
        + f"\n\n{_STYLE_CONSTRAINTS}\n\n"
        "Generate exactly 5 prompts that SHOULD trigger this skill and "
        "5 prompts that should NOT trigger it (but might seem related).\n\n"
        'Reply as JSON: {"should_trigger": ["..."], "should_not_trigger": ["..."]}'
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
                "--system-prompt", _EXPAND_SYSTEM_PROMPT,
                "--tools", "",
                "--max-turns", "1",
                "--output-format", "json",
                "--max-budget-usd", "0.10",
                "--no-session-persistence",
            ],
            input=user_prompt,
            capture_output=True, text=True, timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"skill": skill_name, "error": str(exc)}

    if result.returncode != 0:
        return {"skill": skill_name, "error": f"rc={result.returncode}"}

    # Parse response
    try:
        data = json.loads(result.stdout)
        text = data.get("result", "")
    except json.JSONDecodeError:
        text = result.stdout

    # Extract JSON from response text
    try:
        # Try direct parse first
        candidates = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                candidates = json.loads(text[start:end])
            except json.JSONDecodeError:
                return {"skill": skill_name, "error": "could not parse candidates JSON"}
        else:
            return {"skill": skill_name, "error": "no JSON in response"}

    # Apply quality gates
    accepted = {"should_trigger": [], "should_not_trigger": []}
    rejected = {"should_trigger": [], "should_not_trigger": []}
    for bucket in ("should_trigger", "should_not_trigger"):
        for candidate in candidates.get(bucket, []):
            if not isinstance(candidate, str):
                continue
            candidate = candidate.strip()
            reason = _quality_gate(candidate, skill_name, existing_prompts, description)
            if reason:
                rejected[bucket].append({"prompt": candidate, "reason": reason})
            else:
                accepted[bucket].append({"prompt": candidate})

    output = {
        "skill": skill_name,
        "accepted": accepted,
        "rejected": rejected,
        "stats": {
            "total_generated": sum(
                len(candidates.get(b, [])) for b in ("should_trigger", "should_not_trigger")
            ),
            "total_accepted": sum(len(v) for v in accepted.values()),
            "total_rejected": sum(len(v) for v in rejected.values()),
        },
    }

    # Write to candidates/
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CANDIDATES_DIR / f"{skill_name}.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate candidate trigger prompts via Haiku",
    )
    parser.add_argument("--skill", help="Expand one skill")
    parser.add_argument("--fragile", action="store_true",
                        help="Expand only skills with high fragility (from eval sensitivity)")
    parser.add_argument("--all", action="store_true", help="Expand all skills")
    parser.add_argument("--fragility-threshold", type=float, default=0.10,
                        help="Fragility max threshold for --fragile (default 0.10)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    # Resolve auth once — mirrors behavioral_scorer's cleanup pattern
    import atexit
    from .behavioral_scorer import _resolve_settings
    import lab.eval.behavioral_scorer as bs
    bs._resolved_settings_path = _resolve_settings()
    base_settings = str(TRIGGERS_DIR.parent / "bare_settings.json")
    is_temp = bs._resolved_settings_path != base_settings

    def _cleanup():
        if is_temp:
            import os
            try:
                os.unlink(bs._resolved_settings_path)
            except OSError:
                pass
            os.environ.pop(bs._RESOLVED_TOKEN_ENV, None)

    atexit.register(_cleanup)

    descriptions = load_all_descriptions()

    if args.skill:
        result = expand_skill(args.skill, descriptions)
        print(json.dumps(result, indent=2 if args.pretty else None))
        return

    if args.fragile:
        # Read eval sensitivity results to find fragile skills
        from .eval_sensitivity import analyze_skill as sensitivity_analyze
        fragile_skills = []
        for name in sorted(descriptions.keys()):
            if not load_trigger_file(name):
                continue
            try:
                analysis = sensitivity_analyze(name)
                if analysis and analysis.get("fragility_max", 0) > args.fragility_threshold:
                    fragile_skills.append(name)
            except Exception as exc:
                print(f"WARNING: sensitivity analysis failed for '{name}': {exc}",
                      file=sys.stderr)
                continue
        if not fragile_skills:
            print("No fragile skills found above threshold.", file=sys.stderr)
            return
        print(f"Expanding {len(fragile_skills)} fragile skills: {', '.join(fragile_skills)}",
              file=sys.stderr)
        for name in fragile_skills:
            result = expand_skill(name, descriptions)
            stats = result.get("stats", {})
            print(f"  {name}: {stats.get('total_accepted', 0)} accepted, "
                  f"{stats.get('total_rejected', 0)} rejected", file=sys.stderr)
        return

    if args.all:
        for name in sorted(descriptions.keys()):
            if not load_trigger_file(name):
                continue
            print(f"  Expanding {name}...", end=" ", flush=True, file=sys.stderr)
            result = expand_skill(name, descriptions)
            stats = result.get("stats", {})
            if "error" in result:
                print(f"ERROR: {result['error']}", file=sys.stderr)
            else:
                print(f"{stats.get('total_accepted', 0)} accepted, "
                      f"{stats.get('total_rejected', 0)} rejected", file=sys.stderr)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
