from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / ".claude"
    / "skills"
    / "session-scan"
    / "references"
    / "compute-metrics.py"
)

SPEC = importlib.util.spec_from_file_location("session_scan_metrics", MODULE_PATH)
session_scan_metrics = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(session_scan_metrics)


class SessionScanMetricTests(unittest.TestCase):
    def test_extract_plugin_commands_normalizes_aliases(self) -> None:
        user_msgs = [
            "Use /rb:verify next",
            "Then try /ruby-grape-rails:permissions",
        ]

        commands = session_scan_metrics.extract_plugin_commands(user_msgs)

        self.assertEqual(commands, ["/rb:verify", "/rb:permissions"])

    def test_extract_plugin_commands_ignores_placeholders(self) -> None:
        user_msgs = [
            "Template: /rb:{command}",
            "Placeholder: /ruby-grape-rails:<skill>",
            "Real: /rb:plan",
        ]

        commands = session_scan_metrics.extract_plugin_commands(user_msgs)

        self.assertEqual(commands, ["/rb:plan"])

    def test_locate_skill_invocations_normalizes_aliases(self) -> None:
        messages = [
            {
                "role": "user",
                "content": (
                    "<command-message>ruby-grape-rails:permissions</command-message>\n"
                    "<command-name>/ruby-grape-rails:permissions</command-name>"
                ),
            }
        ]

        invocations = session_scan_metrics._locate_skill_invocations([], messages)

        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0]["skill"], "/rb:permissions")

    def test_compute_plugin_opportunity_accepts_prefixed_commands(self) -> None:
        tool_calls = [
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/a.rb"}},
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/b.rb"}},
            {"name": "Bash", "input": {"command": "bundle exec rspec spec/c.rb"}},
        ]

        score, could_use = session_scan_metrics.compute_plugin_opportunity(
            [],
            tool_calls,
            ["/ruby-grape-rails:verify", "/rb:plan"],
        )

        self.assertEqual(score, 0.2)
        self.assertEqual(could_use, ["investigate"])


if __name__ == "__main__":
    unittest.main()
