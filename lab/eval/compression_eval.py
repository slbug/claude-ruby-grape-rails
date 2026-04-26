"""Fixture-based evaluation. Contributor-only.

Plugin runtime is Ruby; this harness shells out to bin/compress-verify and
asserts ratio + diff thresholds + zero preservation violations.
"""

import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "plugins" / "ruby-grape-rails" / "bin" / "compress-verify"
FIXTURES = Path(__file__).parent / "fixtures" / "compression"
SUCCESS_MEAN_RATIO = 0.40
SUCCESS_DIFF_SCORE = 0.15


def _diff_ratio(a: str, b: str) -> float:
    return 1.0 - difflib.SequenceMatcher(None, a, b).ratio()


def _compress(raw: str, log_path: Path) -> tuple[str, dict]:
    # Single CLI invocation: --emit writes compressed text to stdout AND
    # --log appends the JSONL stats entry. The CLI composes the two flags
    # so the harness gets both effects without double-running compression.
    proc = subprocess.run(
        [str(CLI), "--emit", "--log", str(log_path)],
        input=raw,
        capture_output=True,
        text=True,
        check=True,
    )
    last = log_path.read_text().splitlines()[-1]
    return proc.stdout, json.loads(last)


def main() -> int:
    if not CLI.is_file():
        print(f"compression_eval: missing CLI at {CLI}", file=sys.stderr)
        return 1
    if not FIXTURES.is_dir():
        print(f"compression_eval: no fixtures at {FIXTURES}", file=sys.stderr)
        return 1
    ratios: list[float] = []
    diffs: list[float] = []
    any_violation = False
    any_diff_fail = False
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "compression.jsonl"
        for fixture in sorted(FIXTURES.iterdir()):
            if not fixture.is_dir():
                continue
            raw = (fixture / "raw.txt").read_text(encoding="utf-8")
            expected = (fixture / "expected.txt").read_text(encoding="utf-8")
            text, entry = _compress(raw, log_path)
            ratio = entry["ratio"]
            diff = _diff_ratio(text, expected)
            ratios.append(ratio)
            diffs.append(diff)
            print(
                f"{fixture.name}: ratio={ratio:.2%} diff={diff:.2%} "
                f"violations={len(entry['violations'])}"
            )
            if entry["violations"]:
                any_violation = True
            if diff > SUCCESS_DIFF_SCORE:
                any_diff_fail = True
    mean_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    print(f"\nmean ratio: {mean_ratio:.2%} (target >= {SUCCESS_MEAN_RATIO:.0%})")
    if any_violation:
        return 1
    if any_diff_fail:
        return 1
    if mean_ratio < SUCCESS_MEAN_RATIO:
        return 1
    print("compression_eval: pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
