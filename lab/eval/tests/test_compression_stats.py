"""Subprocess-driven tests for the compression-stats Ruby CLI reader.

Uses unittest.TestCase to match the rest of lab/eval/tests/; CI runs
`python3 -m unittest discover` via scripts/run-eval-tests.sh, so pytest-only
conventions (tmp_path, bare assert) would be skipped.
"""

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI = REPO / "plugins" / "ruby-grape-rails" / "bin" / "compression-stats"


def _run(jsonl_path: Path) -> dict:
    proc = subprocess.run(
        [str(CLI), "--log", str(jsonl_path), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _run_redact(jsonl_path: Path) -> dict:
    proc = subprocess.run(
        [str(CLI), "--log", str(jsonl_path), "--redact"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")


class CompressionStatsAggregateTests(unittest.TestCase):
    def test_no_log_file_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [str(CLI), "--log", str(Path(tmp) / "nope.jsonl"), "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 1)

    def test_classifies_and_aggregates(self) -> None:
        entries = [
            {"ts": 1.0, "cmd": "rspec spec/foo", "raw_bytes": 1000, "compressed_bytes": 300, "ratio": 0.7, "violations": [], "raw_log": None},
            {"ts": 2.0, "cmd": "rspec spec/bar", "raw_bytes": 2000, "compressed_bytes": 600, "ratio": 0.7, "violations": [], "raw_log": None},
            {"ts": 3.0, "cmd": "bundle exec rubocop", "raw_bytes": 500, "compressed_bytes": 400, "ratio": 0.2, "violations": [], "raw_log": None},
            {"ts": 4.0, "cmd": "RAILS_ENV=test bundle exec rails db:migrate", "raw_bytes": 800, "compressed_bytes": 200, "ratio": 0.75, "violations": [], "raw_log": None},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, entries)
            payload = _run(log)
        self.assertEqual(payload["samples"], 4)
        self.assertEqual(payload["preservation_violations"], 0)
        self.assertEqual(set(payload["by_class"].keys()), {"rspec", "rubocop", "migration"})
        self.assertEqual(payload["by_class"]["rspec"]["count"], 2)
        self.assertAlmostEqual(payload["by_class"]["rspec"]["mean"], 0.7, places=6)
        self.assertTrue(payload["recommendation"].startswith("keep-collecting"))

    def test_flags_preservation_violations(self) -> None:
        entries = [
            {"ts": 1.0, "cmd": "rspec", "raw_bytes": 100, "compressed_bytes": 50, "ratio": 0.5, "violations": ["dropped foo"], "raw_log": None},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, entries)
            payload = _run(log)
        self.assertEqual(payload["preservation_violations"], 1)
        self.assertIn("preservation-violations", payload["recommendation"])

    def test_top_weak_samples(self) -> None:
        entries = [
            {"ts": float(i), "cmd": f"rspec spec/x{i}", "raw_bytes": 100, "compressed_bytes": 95, "ratio": 0.05, "violations": [], "raw_log": None}
            for i in range(5)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, entries)
            payload = _run(log)
        self.assertEqual(len(payload["weak_samples"]), 5)
        for sample in payload["weak_samples"]:
            self.assertLess(sample["ratio"], 0.20)

    def test_corrupt_jsonl_lines_skipped(self) -> None:
        good = json.dumps({"ts": 1.0, "cmd": "rspec", "raw_bytes": 10, "compressed_bytes": 5, "ratio": 0.5, "violations": [], "raw_log": None})
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            log.write_text("\n".join([good, "{not-json", "", good]) + "\n")
            payload = _run(log)
        self.assertEqual(payload["samples"], 2)


class CompressionStatsRedactTests(unittest.TestCase):
    def test_redact_strips_env_values_and_paths(self) -> None:
        entry = {
            "ts": 1.0,
            "cmd": "RAILS_ENV=production SECRET_KEY=abcdef rspec spec/models/user_spec.rb",
            "raw_bytes": 1000,
            "compressed_bytes": 100,
            "ratio": 0.05,
            "violations": [],
            "raw_log": "/data/cache/plugins/verify-raw/uuid-1.log",
        }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, [entry])
            payload = _run_redact(log)
        self.assertTrue(payload["redaction_applied"])
        weak = payload["weak_samples"][0]
        self.assertNotIn("production", weak["cmd"])
        self.assertNotIn("abcdef", weak["cmd"])
        self.assertNotIn("user_spec.rb", weak["cmd"])
        self.assertIn("rspec", weak["cmd"])
        self.assertIn("RAILS_ENV=<v>", weak["cmd"])
        self.assertEqual(weak["raw_log_id"], "uuid-1")
        self.assertNotIn("/data/cache", json.dumps(payload))

    def test_redact_drops_violation_message_strings(self) -> None:
        entry = {
            "ts": 1.0,
            "cmd": "bundle exec rubocop",
            "raw_bytes": 500,
            "compressed_bytes": 400,
            "ratio": 0.2,
            "violations": ["dropped /data/private/file.rb:42"],
            "raw_log": "/data/cache/plugins/verify-raw/uuid-2.log",
        }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, [entry])
            payload = _run_redact(log)
        self.assertEqual(payload["preservation_violations"], 1)
        sample = payload["violation_samples"][0]
        self.assertEqual(sample["violation_count"], 1)
        blob = json.dumps(payload)
        self.assertNotIn("private/file.rb", blob)
        self.assertNotIn("/data/private", blob)
        self.assertEqual(sample["raw_log_id"], "uuid-2")

    def test_redact_strips_lowercase_env_values(self) -> None:
        # Lowercase env keys (http_proxy, https_proxy, no_proxy, lang)
        # are POSIX-valid and carry credentials in real usage, e.g.
        # `http_proxy=https://user:pass@host`. The redactor must mask the
        # value the same way it masks uppercase keys.
        entry = {
            "ts": 1.0,
            "cmd": "http_proxy=https://user:pass@proxy.internal lang=en_US.UTF-8 rspec",
            "raw_bytes": 100,
            "compressed_bytes": 10,
            "ratio": 0.05,
            "violations": [],
            "raw_log": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, [entry])
            payload = _run_redact(log)
        blob = json.dumps(payload)
        self.assertNotIn("user:pass", blob)
        self.assertNotIn("proxy.internal", blob)
        self.assertNotIn("en_US.UTF-8", blob)
        weak = payload["weak_samples"][0]
        self.assertIn("http_proxy=<v>", weak["cmd"])
        self.assertIn("lang=<v>", weak["cmd"])
        self.assertIn("rspec", weak["cmd"])

    def test_redact_strips_cli_flag_values(self) -> None:
        # `--flag=value` style CLI options can carry tokens, API keys,
        # JIRA-shaped ticket ids, seed values, and other inline secrets
        # users routinely pass directly. The redactor keeps the flag name
        # for classification but replaces the value with `<v>`.
        entry = {
            "ts": 1.0,
            "cmd": "rspec --token=ghs_secretXYZ --tag=feature:auth --seed=12345",
            "raw_bytes": 100,
            "compressed_bytes": 10,
            "ratio": 0.05,
            "violations": [],
            "raw_log": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, [entry])
            payload = _run_redact(log)
        weak = payload["weak_samples"][0]
        self.assertNotIn("ghs_secretXYZ", weak["cmd"])
        self.assertNotIn("12345", weak["cmd"])
        self.assertNotIn("feature:auth", weak["cmd"])
        self.assertIn("--token=<v>", weak["cmd"])
        self.assertIn("--tag=<v>", weak["cmd"])
        self.assertIn("--seed=<v>", weak["cmd"])

    def test_redact_drops_trailing_freeform_args(self) -> None:
        entry = {
            "ts": 1.0,
            "cmd": "bundle exec rubocop -- /repo/myapp/lib/foo.rb /repo/myapp/lib/bar.rb",
            "raw_bytes": 200,
            "compressed_bytes": 190,
            "ratio": 0.05,
            "violations": [],
            "raw_log": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, [entry])
            payload = _run_redact(log)
        blob = json.dumps(payload)
        self.assertNotIn("/repo/myapp", blob)
        self.assertNotIn("myapp", blob)

    def test_redact_omits_absolute_paths(self) -> None:
        # The raw-log directory under ${CLAUDE_PLUGIN_DATA} contains the
        # user's home dir on real installs; --redact JSON must not leak
        # it. Consumers reconstruct the path locally from inline-
        # substituted ${CLAUDE_PLUGIN_DATA}, never from --redact output.
        entry = {
            "ts": 1.0,
            "cmd": "rspec",
            "raw_bytes": 100,
            "compressed_bytes": 30,
            "ratio": 0.7,
            "violations": [],
            "raw_log": "/data/cache/plugins/verify-raw/uuid-1.log",
        }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, [entry])
            payload = _run_redact(log)
        self.assertNotIn("raw_log_dir", payload)
        blob = json.dumps(payload)
        self.assertNotIn("/data/cache", blob)
        # Generic absolute-path guard.
        self.assertIsNone(
            re.search(r'"/(?:Users|home|var|opt|data|repo)/', blob),
            f"redacted JSON contains an absolute path-shaped value: {blob}",
        )

    def test_redact_keeps_aggregate_stats(self) -> None:
        entries = [
            {"ts": float(i), "cmd": "rspec", "raw_bytes": 100, "compressed_bytes": 30, "ratio": 0.7, "violations": [], "raw_log": None}
            for i in range(5)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "compression.jsonl"
            _write_jsonl(log, entries)
            payload = _run_redact(log)
        self.assertEqual(payload["samples"], 5)
        self.assertEqual(payload["by_class"]["rspec"]["count"], 5)
        self.assertAlmostEqual(payload["by_class"]["rspec"]["mean"], 0.7, places=6)


if __name__ == "__main__":
    unittest.main()
