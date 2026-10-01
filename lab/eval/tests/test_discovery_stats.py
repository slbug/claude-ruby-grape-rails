"""Subprocess-driven tests for the discovery-stats Ruby CLI reader.

Uses unittest.TestCase to match the rest of lab/eval/tests/; CI runs
`python3 -m unittest discover` via scripts/run-eval-tests.sh, so pytest-only
conventions (tmp_path, bare assert) would be skipped.
"""

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLUGIN_ROOT = REPO / "plugins" / "ruby-grape-rails"
CLI = PLUGIN_ROOT / "bin" / "discovery-stats"
TRIGGERS = PLUGIN_ROOT / "references" / "discovery" / "triggers.yml"


def _configured_rule_ids() -> list[str]:
    text = TRIGGERS.read_text(encoding="utf-8")
    return re.findall(r"^\s*- id:\s*(\S+)\s*$", text, flags=re.MULTILINE)


def _write_log(path: Path, rules: list[str]) -> None:
    rows = [
        {
            "ts": "2026-09-29T12:00:00Z",
            "session_id": "s1",
            "hook_event": "PostToolUse",
            "matched_rule": rule,
            "suggest": "sidekiq",
            "would_throttle": False,
            "would_inject_chars": 100,
        }
        for rule in rules
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _run(log: Path, env: dict[str, str]) -> dict:
    proc = subprocess.run(
        [str(CLI), "--log", str(log), "--json"],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return json.loads(proc.stdout)


class DiscoveryStatsSilentRulesTests(unittest.TestCase):
    def test_silent_rules_resolve_without_plugin_root_env(self) -> None:
        # The Bash tool does not export CLAUDE_PLUGIN_ROOT, so the CLI must
        # find triggers.yml from its own location.
        rule_ids = _configured_rule_ids()
        self.assertGreater(len(rule_ids), 1)
        matched = rule_ids[:1]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "discovery.jsonl"
            _write_log(log, matched)
            report = _run(log, env)

        self.assertEqual(report["silent_rules"], sorted(set(rule_ids) - set(matched)))

    def test_plugin_root_env_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "plugin"
            (root / "references" / "discovery").mkdir(parents=True)
            (root / "references" / "discovery" / "triggers.yml").write_text(
                "triggers:\n  - id: only-rule\n", encoding="utf-8"
            )
            log = Path(tmp) / "discovery.jsonl"
            _write_log(log, ["some-other-rule"])
            report = _run(log, {**os.environ, "CLAUDE_PLUGIN_ROOT": str(root)})

        self.assertEqual(report["silent_rules"], ["only-rule"])


if __name__ == "__main__":
    unittest.main()
