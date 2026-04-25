"""Guard: `eval-ci-deterministic` and `run_eval.sh --ci` must stay LLM-free.

Audits the Make target and run_eval.sh by source-scanning for LLM transports.
Fails the build if any banned reference appears, or if a banned module is
imported by code on the deterministic path. The Makefile audit comment is
self-checking through this test.

End-to-end smoke is intentionally NOT run here — the CI workflow already
invokes `make eval-ci-deterministic` as its own step, and a subprocess run
from inside `npm run eval:test` would double-execute the gate.
"""

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

BANNED_PATTERNS = (
    r"\bclaude\s+--bare\b",
    r"\bclaude\s+-p\b",
    r"\bollama\s+(run|generate|serve)\b",
    r"\bapi\.anthropic\.com\b",
    r"\bapi\.openai\.com\b",
    r"\bimport\s+anthropic\b",
    r"\bfrom\s+anthropic\b",
    r"\bimport\s+openai\b",
    r"\bfrom\s+openai\b",
)

BANNED_IMPORTS = (
    "behavioral_scorer",
    "epistemic_suite",
)

# Hardcoded allowlist of files transitively executed by
# `make eval-ci-deterministic`. NOT a wildcard scan: LLM-bearing modules
# (e.g. lab/eval/dimensions/behavioral.py, lab/eval/behavioral_scorer.py,
# lab/eval/epistemic_suite.py) live in the same tree but are NOT reached
# by `run_eval.sh --ci`, so they are intentionally excluded.
#
# When you add a new module to the deterministic path:
#   1. Add the path here.
#   2. Confirm the module imports and shell-outs are LLM-free.
#   3. Re-run this test.
# When you add a module that uses an LLM, do NOT add it here — keep it off
# the deterministic path entirely (see `make eval-behavioral` /
# `make eval-epistemic` for LLM-bearing entrypoints).
DETERMINISTIC_PATH_FILES = (
    "lab/eval/run_eval.sh",
    "lab/eval/scorer.py",
    "lab/eval/agent_scorer.py",
    "lab/eval/agent_matchers.py",
    "lab/eval/matchers.py",
    "lab/eval/matcher_ablation.py",
    "lab/eval/trigger_scorer.py",
    "lab/eval/triggers/hygiene.py",
    "lab/eval/context_budget.py",
    "lab/eval/artifact_scorer.py",
    "lab/eval/output_checks.py",
    "lab/eval/check_refs.py",
    "lab/eval/frontmatter.py",
    "lab/eval/results_dir.py",
    "lab/eval/schemas.py",
    "scripts/check-dynamic-injection.sh",
)


def _read(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="replace")


class EvalCiDeterminismTests(unittest.TestCase):
    def test_makefile_target_exists(self) -> None:
        body = _read("Makefile")
        self.assertRegex(
            body,
            r"(?m)^eval-ci-deterministic:",
            "eval-ci-deterministic target missing from Makefile",
        )
        audit_marker = re.search(
            r"Must NOT transitively\s+(?:#\s*)?invoke any\s+(?:#\s*)?LLM provider",
            body,
        )
        self.assertIsNotNone(
            audit_marker,
            "Makefile audit comment removed — restore it before merging",
        )

    def test_no_banned_patterns_on_deterministic_path(self) -> None:
        for rel in DETERMINISTIC_PATH_FILES:
            text = _read(rel)
            for pattern in BANNED_PATTERNS:
                for m in re.finditer(pattern, text):
                    # `trigger_scorer.py` legitimately gates a `--semantic`
                    # LLM call inside `_fetch_semantic_pairs`; the
                    # deterministic `--all` invocation never reaches it.
                    if (
                        rel == "lab/eval/trigger_scorer.py"
                        and pattern == r"\bclaude\s+--bare\b"
                    ):
                        line_start = text.rfind("\n", 0, m.start()) + 1
                        snippet = text[max(0, line_start - 4000) : m.start()]
                        if "--semantic" in snippet:
                            continue
                    self.fail(
                        f"{rel}: banned LLM pattern matched: {pattern!r}"
                    )

    def test_no_banned_imports_on_deterministic_path(self) -> None:
        for rel in DETERMINISTIC_PATH_FILES:
            if not rel.endswith(".py"):
                continue
            text = _read(rel)
            for module in BANNED_IMPORTS:
                if not re.search(
                    rf"^(import|from)\s.*\b{module}\b", text, re.MULTILINE
                ):
                    continue
                if (
                    rel == "lab/eval/trigger_scorer.py"
                    and module == "behavioral_scorer"
                ):
                    # confirm only inside `_fetch_semantic_pairs`, never
                    # at module top level.
                    top_level = text.split("def ")[0]
                    self.assertNotRegex(
                        top_level,
                        rf"(?m)^(import|from)\s.*\b{module}\b",
                        f"{rel}: top-level import of {module}",
                    )
                    continue
                self.fail(
                    f"{rel}: banned import on deterministic path: {module}"
                )

if __name__ == "__main__":
    unittest.main()
