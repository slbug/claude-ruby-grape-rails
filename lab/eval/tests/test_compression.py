"""Contributor tests for verify-compression library + contributor CLI.

Plugin runtime is Ruby (lib/verify_compression.rb). The hook calls the
library directly. lab/eval/bin/compress-verify is a contributor-only
CLI wrapper used here for subprocess testing — lab/eval/ stays Python
by convention.

Uses unittest.TestCase to match the rest of lab/eval/tests/; CI runs
`python3 -m unittest discover` via scripts/run-eval-tests.sh, so pytest-only
conventions (tmp_path, bare assert) would be skipped.
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI = REPO / "lab" / "eval" / "bin" / "compress-verify"
LIB = REPO / "plugins" / "ruby-grape-rails" / "lib"


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


class CompressEmitTests(unittest.TestCase):
    def test_compress_preserves_migration_name(self) -> None:
        raw = "== 20260423120000_add_email_index.rb: migrating ====\nrunning...\ndone\n"
        text = _emit(raw)
        self.assertIn("20260423120000_add_email_index.rb", text)

    def test_compress_collapses_deep_stack(self) -> None:
        frames = [f"  from /gems/ar/{i}.rb:10" for i in range(30)]
        raw = "RuntimeError: boom\n" + "\n".join(frames)
        text = _emit(raw)
        self.assertIn("/gems/ar/0.rb:10", text)
        self.assertIn("/gems/ar/4.rb:10", text)
        self.assertIn("elided", text)
        self.assertNotIn("/gems/ar/29.rb:10", text)

    def test_compress_collapses_rspec_outside_of_examples_stack(self) -> None:
        # RSpec's "outside of examples" formatter (boot failures) emits
        # frames prefixed with `# /path:line:in '...'` rather than the bare
        # `from ...` form. STACK_FRAME_RE must match this prefix so the
        # >5-frame collapse fires for boot-failure stacks too.
        frames = [
            f"# /gems/sequel-5.103.0/lib/sequel/{i}.rb:{100 + i}:in 'method_{i}'"
            for i in range(20)
        ]
        raw = "Sequel::DatabaseConnectionError:\n" + "\n".join(frames)
        text = _emit(raw)
        # First 5 frames preserved.
        self.assertIn("sequel/0.rb:100:in 'method_0'", text)
        self.assertIn("sequel/4.rb:104:in 'method_4'", text)
        # Frames beyond the top 5 are elided.
        self.assertIn("elided", text)
        self.assertNotIn("sequel/19.rb:119", text)


class CompressBracketWarningCollapseTests(unittest.TestCase):
    def test_compress_collapses_consecutive_identical_bracket_warnings(self) -> None:
        # Bracket-prefixed warnings (`[dry-types] ...`, `[bundler] ...`) commonly
        # repeat verbatim once per Bundler require pass. Consecutive identical
        # lines collapse into the first occurrence + a `[+N repeated]` summary.
        warn = "[dry-types] [] is mutable. Be careful: types will return same instance."
        raw = "\n".join(["Loading...", warn, warn, warn, warn, "Continuing."]) + "\n"
        text = _emit(raw)
        # First occurrence preserved.
        self.assertEqual(text.count(warn), 1)
        # Three additional dupes collapsed.
        self.assertIn("[+3 repeated]", text)
        # Surrounding non-warning lines untouched.
        self.assertIn("Loading...", text)
        self.assertIn("Continuing.", text)

    def test_compress_resets_bracket_warning_run_across_non_warning_lines(self) -> None:
        # An interleaved non-warning line breaks the run; subsequent identical
        # warning does NOT count toward the previous run.
        warn = "[dry-types] [] is mutable"
        raw = "\n".join([warn, warn, "Finished in 1.2s, 5 examples", warn]) + "\n"
        text = _emit(raw)
        # First run: 2 dupes (1 emitted + 1 collapsed via "+1 repeated").
        self.assertIn("[+1 repeated]", text)
        # Two distinct emissions of `warn` (one before "Finished", one after).
        self.assertEqual(text.count(warn), 2)

    def test_compress_does_not_collapse_distinct_bracket_warnings(self) -> None:
        # Different bracket-prefixed lines must NOT collapse together.
        a = "[dry-types] [] is mutable"
        b = "[bundler] dependency outdated"
        raw = "\n".join([a, b, a]) + "\n"
        text = _emit(raw)
        self.assertEqual(text.count(a), 2)
        self.assertEqual(text.count(b), 1)
        self.assertNotIn("repeated", text)

    def test_compress_records_no_violation_when_sqlstate_kept(self) -> None:
        raw = "PG::UniqueViolation: ERROR: duplicate key"
        text = _emit(raw)
        self.assertIn("PG::UniqueViolation", text)
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(raw, Path(tmp) / "compression.jsonl")
            self.assertEqual(log["violations"], [])
            self.assertEqual(log["raw_bytes"], len(raw.encode("utf-8")))


class CompressDeprecationCollapseTests(unittest.TestCase):
    def test_compress_collapses_only_consecutive_identical_deprecations(self) -> None:
        # Three different deprecation messages must NOT collapse into one
        # `[+N similar deprecations]` summary; they are distinct facts. Only
        # consecutive identical lines collapse.
        a = "DEPRECATION WARNING: `attr_accessible` is deprecated"
        b = "DEPRECATION WARNING: `update_attributes` is deprecated"
        c = "DEPRECATION WARNING: `find_by_email` dynamic finders are removed"
        raw = "\n".join([a, a, a, b, c]) + "\n"
        text = _emit(raw)
        # All three distinct messages survive.
        self.assertIn(a, text)
        self.assertIn(b, text)
        self.assertIn(c, text)
        # The three identical `a` collapse to one + `[+2 similar]`.
        self.assertIn("[+2 similar deprecations]", text)
        # First-occurrence `b` and `c` must NOT be tagged as similar to `a`.
        self.assertEqual(text.count(a), 1)
        self.assertEqual(text.count(b), 1)
        self.assertEqual(text.count(c), 1)

    def test_compress_resets_dupe_run_across_non_deprecation_lines(self) -> None:
        # An interleaved non-deprecation line breaks the run; subsequent
        # identical deprecation does NOT count toward the previous run.
        dep = "DEPRECATION WARNING: `attr_accessible` is deprecated"
        raw = "\n".join([dep, dep, "Finished in 1.2s, 5 examples", dep]) + "\n"
        text = _emit(raw)
        # First run: 2 dupes (1 emitted + 1 collapsed via "+1 similar").
        self.assertIn("[+1 similar deprecations]", text)
        # Two distinct emissions of `dep` (one before "Finished", one after).
        self.assertEqual(text.count(dep), 2)


class JsonlLogSafetyTests(unittest.TestCase):
    """`compress-verify --log` must not follow symlinks or write to non-files."""

    def test_log_refuses_symlink_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            target = tmp_p / "innocent.txt"
            target.write_text("pre-existing content\n")
            log = tmp_p / "compression.jsonl"
            log.symlink_to(target)

            proc = subprocess.run(
                [str(CLI), "--log", str(log), "--cmd", "rspec"],
                input="rspec output",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(target.read_text(), "pre-existing content\n")
            self.assertTrue(log.is_symlink())

    def test_log_refuses_directory_at_jsonl_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            log.mkdir()  # not a regular file
            proc = subprocess.run(
                [str(CLI), "--log", str(log), "--cmd", "rspec"],
                input="rspec output",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertTrue(log.is_dir())  # still a directory; nothing written


class PreserveCheckTests(unittest.TestCase):
    def test_preserve_check_flags_dropped_duplicates(self) -> None:
        # The preserve contract says EACH occurrence of a match survives.
        # If the compressor drops 4 of 5 identical migration-name lines but
        # keeps 1, `compressed.include?(match)` would (wrongly) pass. The
        # multiplicity-aware check must surface the lost duplicates as a
        # preservation violation. The compressor itself never drops
        # migration_names, so this is a baseline correctness test:
        # 5 raw -> 5 compressed -> zero violations.
        name = "20260423120000_add_email_index.rb"
        raw = "\n".join([f"== {name}: migrating ====" for _ in range(5)]) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            log = _log(raw, Path(tmp) / "compression.jsonl")
            self.assertEqual(log["violations"], [], log["violations"])
        text = _emit(raw)
        self.assertEqual(text.count(name), 5)

    def test_preserve_check_handles_non_hash_preserve(self) -> None:
        # If `preserve:` in rules.yml is a scalar / list / anything that is
        # not a Hash, `check_preservation` must surface a violation rather
        # than crash on `.each`. We exercise this by writing a custom
        # rules file with a string `preserve:` and pointing the compressor
        # at it via VerifyCompression.compress(rules_path:).
        with tempfile.TemporaryDirectory() as tmp:
            rules = Path(tmp) / "rules.yml"
            rules.write_text("preserve: just-a-string\n")
            proc = subprocess.run(
                [
                    "ruby", "-I", str(LIB),
                    "-rverify_compression", "-rjson", "-e",
                    (
                        "result = VerifyCompression.compress("
                        "'rspec output', rules_path: ARGV[0]); "
                        "puts JSON.generate("
                        "violations: result.preservation_violations)"
                    ),
                    str(rules),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertTrue(
                any("Hash" in v for v in payload["violations"]),
                payload,
            )


if __name__ == "__main__":
    unittest.main()
