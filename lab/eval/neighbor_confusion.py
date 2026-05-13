"""Neighbor-confusion + forbidden-load eval runner.

Standalone module — invoked by contributors to validate description-boundary
routing accuracy. NOT part of `make eval-ci-deterministic` (LLM-cost gated).

Fixture: lab/eval/fixtures/neighbor_confusion.json
  - pairs: confusable skill pairs with queries that SHOULD route to each side
  - forbidden: per-skill negative queries that should NOT route to that skill
  - threshold_routing (default 0.80): min fraction of samples routing to expected skill
  - threshold_forbidden (default 0.20): max fraction of samples routing to forbidden skill
  - runs_per_query (default 3): provider call repetitions per query

Provider selection follows the rest of the eval suite via
`RUBY_PLUGIN_EVAL_PROVIDER` env var or `--provider`. Ollama is currently
the only wired provider; the dispatch in `behavioral_scorer._run_provider`
is pluggable for future additions (e.g., Microsoft Waza).

The underlying `run_ollama` → `_get_ollama_client` → `_ensure_ollama_server`
chain autostarts `ollama serve` with the eval-tuned env
(`OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`,
`OLLAMA_NUM_PARALLEL=4`, `OLLAMA_MAX_LOADED_MODELS=1`) when no external
server is already running. No manual `ollama serve` needed.

Cached results are NOT consulted — fixture queries are free-form NL and
do not fit the skill-keyed cache schema of the rest of the eval suite.
Each call hits the live provider.

Usage:
  python3 -m lab.eval.neighbor_confusion \
      --provider ollama --workers 4 --summary --pretty

Exit codes:
  0 — all pairs hit routing threshold AND all forbidden queries under FP threshold
  1 — at least one threshold breach
  2 — fixture / provider configuration error
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from . import results_dir as rd
from .behavioral_scorer import (
    CallResult,
    _run_provider,
    build_routing_prompt,
)
from .results_dir import SUPPORTED_PROVIDERS
from .trigger_scorer import load_all_routing_descriptions, load_hidden_skills

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "neighbor_confusion.json"


@dataclass
class CallProbe:
    skill: str
    query: str
    role: str  # "pair" | "forbidden"
    target_for: str  # skill the query targets (pair) or skill the query must NOT route to (forbidden)


@dataclass
class CallOutcome:
    probe: CallProbe
    routed_skills: list[str] | None
    error_type: str | None


def _load_fixture(path: Path) -> dict:
    if not path.is_file():
        print(f"neighbor_confusion: fixture not found at {path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"neighbor_confusion: invalid JSON in {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)


def _build_probes(fixture: dict) -> list[CallProbe]:
    probes: list[CallProbe] = []
    for pair in fixture.get("pairs", []):
        a = pair["a"]
        b = pair["b"]
        for query in pair.get("queries_for_a", []):
            probes.append(CallProbe(a, query, "pair", a))
        for query in pair.get("queries_for_b", []):
            probes.append(CallProbe(b, query, "pair", b))
    for skill, queries in fixture.get("forbidden", {}).items():
        for query in queries:
            probes.append(CallProbe(skill, query, "forbidden", skill))
    return probes


def _call(
    descriptions: dict[str, dict[str, str]],
    probe: CallProbe,
) -> CallOutcome:
    prompt = build_routing_prompt(descriptions, probe.query)
    result: CallResult = _run_provider(prompt)
    return CallOutcome(
        probe=probe,
        routed_skills=result.skills,
        error_type=result.error_type,
    )


def _aggregate(
    outcomes: list[CallOutcome],
    runs_per_query: int,
    threshold_routing: float,
    threshold_forbidden: float,
) -> dict:
    pair_buckets: dict[str, dict[str, dict]] = {}
    forbidden_buckets: dict[str, dict[str, dict]] = {}

    for outcome in outcomes:
        target = outcome.probe.target_for
        query = outcome.probe.query
        if outcome.probe.role == "pair":
            bucket = pair_buckets.setdefault(target, {}).setdefault(
                query, {"hits": 0, "calls": 0, "errors": 0}
            )
        else:
            bucket = forbidden_buckets.setdefault(target, {}).setdefault(
                query, {"hits": 0, "calls": 0, "errors": 0}
            )
        bucket["calls"] += 1
        if outcome.routed_skills is None:
            bucket["errors"] += 1
            continue
        if target in outcome.routed_skills:
            bucket["hits"] += 1

    pair_report: dict[str, dict] = {}
    pair_failures: list[str] = []
    for skill, queries in pair_buckets.items():
        per_query = []
        skill_hits = 0
        skill_calls = 0
        for query, stats in queries.items():
            rate = (stats["hits"] / stats["calls"]) if stats["calls"] else 0.0
            per_query.append(
                {
                    "query": query,
                    "hits": stats["hits"],
                    "calls": stats["calls"],
                    "errors": stats["errors"],
                    "rate": round(rate, 4),
                }
            )
            skill_hits += stats["hits"]
            skill_calls += stats["calls"]
        skill_rate = (skill_hits / skill_calls) if skill_calls else 0.0
        passed = skill_rate >= threshold_routing
        pair_report[skill] = {
            "rate": round(skill_rate, 4),
            "passed": passed,
            "threshold": threshold_routing,
            "per_query": per_query,
        }
        if not passed:
            pair_failures.append(f"{skill}: rate={skill_rate:.2f} < {threshold_routing}")

    forbidden_report: dict[str, dict] = {}
    forbidden_failures: list[str] = []
    for skill, queries in forbidden_buckets.items():
        per_query = []
        skill_hits = 0
        skill_calls = 0
        for query, stats in queries.items():
            rate = (stats["hits"] / stats["calls"]) if stats["calls"] else 0.0
            per_query.append(
                {
                    "query": query,
                    "hits": stats["hits"],
                    "calls": stats["calls"],
                    "errors": stats["errors"],
                    "fp_rate": round(rate, 4),
                }
            )
            skill_hits += stats["hits"]
            skill_calls += stats["calls"]
        skill_rate = (skill_hits / skill_calls) if skill_calls else 0.0
        passed = skill_rate <= threshold_forbidden
        forbidden_report[skill] = {
            "fp_rate": round(skill_rate, 4),
            "passed": passed,
            "threshold": threshold_forbidden,
            "per_query": per_query,
        }
        if not passed:
            forbidden_failures.append(f"{skill}: fp_rate={skill_rate:.2f} > {threshold_forbidden}")

    return {
        "runs_per_query": runs_per_query,
        "threshold_routing": threshold_routing,
        "threshold_forbidden": threshold_forbidden,
        "pair_routing": pair_report,
        "forbidden_load": forbidden_report,
        "failures": {
            "pair_routing": pair_failures,
            "forbidden_load": forbidden_failures,
        },
        "passed": not (pair_failures or forbidden_failures),
    }


def _print_summary(report: dict) -> None:
    print(f"runs_per_query: {report['runs_per_query']}")
    print(f"thresholds: routing >= {report['threshold_routing']}, forbidden FP <= {report['threshold_forbidden']}")
    print()
    print("Pair routing accuracy:")
    for skill, info in sorted(report["pair_routing"].items()):
        status = "PASS" if info["passed"] else "FAIL"
        print(f"  {status}  {skill}: rate={info['rate']:.2f}")
    print()
    print("Forbidden-load FP rate:")
    for skill, info in sorted(report["forbidden_load"].items()):
        status = "PASS" if info["passed"] else "FAIL"
        print(f"  {status}  {skill}: fp_rate={info['fp_rate']:.2f}")
    print()
    if report["passed"]:
        print("OK — all thresholds satisfied")
    else:
        print("FAIL — threshold breaches:")
        for failure in report["failures"]["pair_routing"]:
            print(f"  pair_routing: {failure}")
        for failure in report["failures"]["forbidden_load"]:
            print(f"  forbidden_load: {failure}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Neighbor-confusion + forbidden-load eval")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=FIXTURE_PATH,
        help=f"Path to neighbor_confusion.json (default: {FIXTURE_PATH})",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(SUPPORTED_PROVIDERS),
        default=None,
        help="Override RUBY_PLUGIN_EVAL_PROVIDER",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=None,
        help="Override runs_per_query from fixture",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel provider calls (default 1; raise for ollama with OLLAMA_NUM_PARALLEL>1)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print human-readable summary",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write full JSON report to PATH",
    )
    args = parser.parse_args()

    if args.provider:
        rd.set_active_provider(args.provider)

    provider = rd.get_active_provider()
    if provider not in SUPPORTED_PROVIDERS:
        print(f"neighbor_confusion: unsupported provider {provider!r}", file=sys.stderr)
        return 2

    fixture = _load_fixture(args.fixture)
    runs_per_query = args.runs or int(fixture.get("runs_per_query", 3))
    threshold_routing = float(fixture.get("threshold_routing", 0.80))
    threshold_forbidden = float(fixture.get("threshold_forbidden", 0.20))

    hidden = load_hidden_skills()
    descriptions = {
        name: desc
        for name, desc in load_all_routing_descriptions().items()
        if name not in hidden
    }
    if not descriptions:
        print("neighbor_confusion: no skill descriptions loaded", file=sys.stderr)
        return 2

    probes = _build_probes(fixture)
    if not probes:
        print("neighbor_confusion: no probes derived from fixture", file=sys.stderr)
        return 2

    expanded: list[CallProbe] = []
    for probe in probes:
        expanded.extend([probe] * runs_per_query)

    outcomes: list[CallOutcome] = []
    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for outcome in pool.map(lambda p: _call(descriptions, p), expanded):
                outcomes.append(outcome)
    else:
        for probe in expanded:
            outcomes.append(_call(descriptions, probe))

    report = _aggregate(outcomes, runs_per_query, threshold_routing, threshold_forbidden)
    report["provider"] = provider
    report["fixture_path"] = str(args.fixture)
    report["total_calls"] = len(outcomes)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, indent=2 if args.pretty else None, sort_keys=True),
            encoding="utf-8",
        )

    if args.summary:
        _print_summary(report)
    else:
        print(json.dumps(report, indent=2 if args.pretty else None, sort_keys=True))

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
