"""Contributor tests for verify-compression CLI.

Plugin runtime is Ruby (verify_compression.rb + bin/compress-verify); end-users
already have Ruby ≥3.4. lab/eval/ stays Python by convention, so these tests
shell out to the Ruby CLI via subprocess and assert on its --emit output and
the JSONL log entry shape.
"""

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI = REPO / "plugins" / "ruby-grape-rails" / "bin" / "compress-verify"


def _emit(raw: str) -> str:
    proc = subprocess.run(
        [str(CLI), "--emit"],
        input=raw,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _log(raw: str, log_path: Path, cmd: str = "rspec") -> dict:
    subprocess.run(
        [str(CLI), "--log", str(log_path), "--cmd", cmd],
        input=raw,
        capture_output=True,
        text=True,
        check=True,
    )
    line = log_path.read_text().splitlines()[-1]
    return json.loads(line)


def test_compress_preserves_migration_name() -> None:
    raw = "== 20260423120000_add_email_index.rb: migrating ====\nrunning...\ndone\n"
    text = _emit(raw)
    assert "20260423120000_add_email_index.rb" in text


def test_compress_collapses_deep_stack() -> None:
    frames = [f"  from /gems/ar/{i}.rb:10" for i in range(30)]
    raw = "RuntimeError: boom\n" + "\n".join(frames)
    text = _emit(raw)
    assert "/gems/ar/0.rb:10" in text
    assert "/gems/ar/4.rb:10" in text
    assert "elided" in text
    assert "/gems/ar/29.rb:10" not in text


def test_compress_records_no_violation_when_sqlstate_kept(tmp_path: Path) -> None:
    raw = "PG::UniqueViolation: ERROR: duplicate key"
    text = _emit(raw)
    assert "PG::UniqueViolation" in text
    log = _log(raw, tmp_path / "compression.jsonl")
    assert log["violations"] == []
    assert log["raw_bytes"] == len(raw.encode("utf-8"))


def test_compress_collapses_only_consecutive_identical_deprecations() -> None:
    # Three different deprecation messages must NOT collapse into one
    # `[+N similar deprecations]` summary; they are distinct facts. Only
    # consecutive identical lines collapse.
    a = "DEPRECATION WARNING: `attr_accessible` is deprecated"
    b = "DEPRECATION WARNING: `update_attributes` is deprecated"
    c = "DEPRECATION WARNING: `find_by_email` dynamic finders are removed"
    raw = "\n".join([a, a, a, b, c]) + "\n"
    text = _emit(raw)
    # All three distinct messages survive.
    assert a in text
    assert b in text
    assert c in text
    # The three identical `a` collapse to one + `[+2 similar]`.
    assert "[+2 similar deprecations]" in text
    # First-occurrence `b` and `c` must NOT be tagged as similar to `a`.
    assert text.count(a) == 1
    assert text.count(b) == 1
    assert text.count(c) == 1


def test_compress_resets_dupe_run_across_non_deprecation_lines() -> None:
    # An interleaved non-deprecation line breaks the run; subsequent
    # identical deprecation does NOT count toward the previous run.
    dep = "DEPRECATION WARNING: `attr_accessible` is deprecated"
    raw = "\n".join([dep, dep, "Finished in 1.2s, 5 examples", dep]) + "\n"
    text = _emit(raw)
    # First run: 2 dupes (1 emitted + 1 collapsed via "+1 similar").
    assert "[+1 similar deprecations]" in text
    # Two distinct emissions of `dep` (one before "Finished", one after).
    assert text.count(dep) == 2
